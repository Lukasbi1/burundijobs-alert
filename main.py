import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8684867209:AAGhop82JDrDaeteos1lWAhXdl1mwEjjOE8")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5004814618")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # À renseigner sur Render
SEEN_JOBS_FILE = "seen_jobs.json"

PROFILE = """
Candidat: Jean Luc VYIZIGIRO
- BAC+3 en Droit (droit commercial, droit public/privé, économie politique, comptabilité générale et analytique)
- 1 an d'expérience comme Juge au Tribunal de Résidence
- Maîtrise MS Excel et PowerPoint (certifié)
- Maîtrise Google Workspace, Microsoft 365, Teams, Zoom
- Langues: Français (courant), Anglais (courant), Kirundi (natif), Kiswahili (courant)
- Basé à Bujumbura, Burundi
- Compétences: rédaction juridique, gestion de dossiers, archivage, coordination administrative, comptabilité de base

POSTES COMPATIBLES (exemples): assistant administratif, chargé de projets, juriste, gestionnaire administratif, 
grant writer, chargé de communication, coordinateur, responsable conformité/contrats, 
assistant RH, assistant relèvement économique, agent administratif ONG/cabinet.

POSTES NON COMPATIBLES: ingénieur civil, médecin, agronome, technicien solaire, 
chauffeur, spécialiste IT, comptable senior (sans expérience), 
postes exigeant 5+ ans d'expérience spécialisée.
"""

# ─── FONCTIONS UTILITAIRES ────────────────────────────────────────────────────

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return json.load(f)
    return []

def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(seen, f)

def job_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()

# ─── SCRAPING ─────────────────────────────────────────────────────────────────

def scrape_jobs():
    jobs = []
    for page in [1, 2]:
        url = "https://www.burundijobs.bi/" if page == 1 else f"https://www.burundijobs.bi/page/{page}/"
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            
            for job_el in soup.select("h3 a"):
                title = job_el.get_text(strip=True)
                link = job_el.get("href", "")
                if link and "burundijobs.bi/job/" in link and title:
                    # Récupérer la deadline si dispo
                    parent = job_el.find_parent()
                    deadline = ""
                    if parent:
                        card = parent.find_parent()
                        if card:
                            dl = card.get_text()
                            if "Deadline" in dl or "avril" in dl or "mai" in dl:
                                import re
                                match = re.search(r'Deadline[:\s]*(\d+\s+\w+\s+\d+)', dl)
                                if match:
                                    deadline = match.group(1)
                    
                    jobs.append({
                        "title": title,
                        "url": link,
                        "deadline": deadline,
                        "id": job_id(title, link)
                    })
        except Exception as e:
            print(f"Erreur scraping page {page}: {e}")
    
    # Dédoublonner
    seen_ids = set()
    unique = []
    for j in jobs:
        if j["id"] not in seen_ids:
            seen_ids.add(j["id"])
            unique.append(j)
    return unique

# ─── ANALYSE IA ───────────────────────────────────────────────────────────────

def analyze_job_with_ai(job_title, job_url):
    """Utilise Claude pour analyser si le poste est compatible avec le profil."""
    try:
        # D'abord récupérer le contenu de l'offre
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(job_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Extraire le texte principal de l'offre
        content = ""
        for tag in soup.select("h1, h2, h3, p, li, td"):
            text = tag.get_text(strip=True)
            if text and len(text) > 20:
                content += text + "\n"
        content = content[:3000]  # Limiter
        
        prompt = f"""Tu es un conseiller emploi expert au Burundi. Analyse si cette offre d'emploi est compatible avec ce profil de candidat.

PROFIL DU CANDIDAT:
{PROFILE}

OFFRE D'EMPLOI: {job_title}
CONTENU:
{content}

Réponds UNIQUEMENT en JSON sans markdown, format exact:
{{"compatible": true/false, "score": 0-100, "raison": "explication courte en 1-2 phrases", "points_forts": "ce qui correspond", "points_faibles": "ce qui manque"}}

Compatible = true seulement si score >= 50 ET le candidat a une chance réelle d'être retenu."""

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        
        data = response.json()
        text = data["content"][0]["text"].strip()
        # Nettoyer les backticks si présents
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
        
    except Exception as e:
        print(f"Erreur analyse IA pour '{job_title}': {e}")
        return None

# ─── TELEGRAM ─────────────────────────────────────────────────────────────────

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Erreur Telegram: {e}")
        return False

def format_alert(job, analysis):
    score = analysis.get("score", 0)
    emoji = "🔥" if score >= 80 else "✅" if score >= 60 else "⚠️"
    
    msg = f"""{emoji} <b>NOUVELLE OFFRE COMPATIBLE</b>

📌 <b>{job['title']}</b>

📊 Score de compatibilité: <b>{score}/100</b>
✅ Points forts: {analysis.get('points_forts', 'N/A')}
⚠️ Points faibles: {analysis.get('points_faibles', 'N/A')}
💡 {analysis.get('raison', '')}"""

    if job.get("deadline"):
        msg += f"\n⏰ Deadline: {job['deadline']}"
    
    msg += f"\n\n🔗 <a href='{job['url']}'>Voir l'offre complète</a>"
    msg += f"\n\n🕐 Détecté le {datetime.now().strftime('%d/%m/%Y à %Hh%M')}"
    return msg

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Vérification des nouvelles offres...")
    
    seen_jobs = load_seen_jobs()
    all_jobs = scrape_jobs()
    
    new_jobs = [j for j in all_jobs if j["id"] not in seen_jobs]
    print(f"  → {len(all_jobs)} offres trouvées, {len(new_jobs)} nouvelles")
    
    compatible_count = 0
    
    for job in new_jobs:
        print(f"  Analyse: {job['title'][:60]}...")
        
        # Filtrage rapide — ignorer les appels d'offres de fournitures évidentes
        skip_keywords = [
            "fourniture", "travaux", "réhabilitation", "construction", 
            "véhicule", "électrogène", "carburant", "audit financier",
            "cotation", "appel d'offres", "pistes rurales", "assurance",
            "équipements", "matériel", "produits phytosanitaires"
        ]
        title_lower = job["title"].lower()
        if any(kw in title_lower for kw in skip_keywords):
            print(f"    → Ignoré (fourniture/travaux)")
            seen_jobs.append(job["id"])
            continue
        
        # Analyse IA
        analysis = analyze_job_with_ai(job["title"], job["url"])
        
        if analysis and analysis.get("compatible"):
            msg = format_alert(job, analysis)
            if send_telegram(msg):
                print(f"    → ✅ ALERTE ENVOYÉE (score: {analysis.get('score')})")
                compatible_count += 1
            else:
                print(f"    → ❌ Erreur envoi Telegram")
        else:
            score = analysis.get("score", 0) if analysis else "?"
            print(f"    → Non compatible (score: {score})")
        
        seen_jobs.append(job["id"])
    
    save_seen_jobs(seen_jobs)
    print(f"  → Terminé. {compatible_count} alerte(s) envoyée(s).\n")

if __name__ == "__main__":
    run()
