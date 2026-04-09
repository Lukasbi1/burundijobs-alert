# 🔔 BurundiJobs Alert Bot

Bot qui surveille burundijobs.bi toutes les 3h et t'envoie une alerte Telegram 
quand une nouvelle offre compatible avec ton profil apparaît.

## 🚀 Déploiement sur Render.com (gratuit)

### Étape 1 — Prépare ton bot Telegram
1. Ouvre Telegram → cherche @BotFather
2. Envoie `/newbot` → suis les instructions
3. Copie le **TOKEN** donné par BotFather
4. Cherche @userinfobot → envoie n'importe quel message → copie ton **Chat ID**

### Étape 2 — Mets le code sur GitHub
1. Crée un compte sur https://github.com
2. Crée un nouveau repository (ex: `burundijobs-alert`)
3. Upload les 3 fichiers: `main.py`, `requirements.txt`, `render.yaml`

### Étape 3 — Déploie sur Render.com
1. Crée un compte gratuit sur https://render.com
2. Clique "New +" → "Cron Job"
3. Connecte ton repo GitHub
4. Render détecte automatiquement le render.yaml
5. Dans "Environment Variables", ajoute:
   - `TELEGRAM_TOKEN` = ton token BotFather
   - `TELEGRAM_CHAT_ID` = ton chat ID
   - `ANTHROPIC_API_KEY` = ta clé API Anthropic

### Étape 4 — C'est parti !
Le bot vérifie le site toutes les 3 heures.
Tu recevras un message Telegram à chaque nouvelle offre compatible.

## 📱 Format des alertes Telegram

🔥 NOUVELLE OFFRE COMPATIBLE (score ≥ 80)
✅ NOUVELLE OFFRE COMPATIBLE (score 60-79)
⚠️  NOUVELLE OFFRE COMPATIBLE (score 50-59)

Chaque alerte contient:
- Titre du poste
- Score de compatibilité /100
- Points forts et points faibles
- Deadline
- Lien direct vers l'offre

## ⚙️ Modifier la fréquence de vérification

Dans render.yaml, modifie la ligne `schedule`:
- `"0 */3 * * *"` = toutes les 3 heures
- `"0 */6 * * *"` = toutes les 6 heures  
- `"0 8,12,18 * * *"` = à 8h, 12h et 18h chaque jour
