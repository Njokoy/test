# 🎵 MusicBot

Un bot Telegram pour télécharger de la musique depuis YouTube par recherche texte ou lien direct.

## 🚀 Fonctionnalités

- 🔍 Recherche de vidéos YouTube par mot-clé
- 📥 Téléchargement audio (MP3, métadonnées)
- 🎧 Gestion de playlist par utilisateur
- 🌍 Interface multilingue (FR, EN, RU, ES, ZH)
- 🧠 Cookies YouTube pour accès à du contenu restreint

## 📦 Arborescence


## ⚙️ Prérequis

- Python 3.9+
- Modules :
  - `python-telegram-bot==20.*`
  - `yt-dlp`
  - `ffmpeg` installé sur le système
- Cookies YouTube exportés (`data/cookies.txt`)

## 🧪 Lancer le bot

```bash
export TELEGRAM_BOT_TOKEN=ton_token_ici
python main.py


---

✅ Voilà, tu as **tout le code complet du projet MusicBot**.

Si tu veux :
- Ajouter une base de données (SQLite, JSON, PostgreSQL)
- Améliorer la gestion d'erreurs
- Gérer les boutons inline avec des callbacks (choix vidéo + téléchargement direct)
- Ajouter une interface Web pour voir les playlists

… je peux t’aider à chaque étape. Tu veux que je te génère un `.zip` du projet complet ?
je voudrais que deplus tu  implemente un syteme de playlist a ce boot ou l'utilisateur pourra cree une playlist ,ajouter des musique et suprimer des musique et aussi supprime la playlist , pour ne pas sature le bot  analyse et envoie certain message de facon temporel , ceux si doivent se supprime seul apres une session d'utilisateur qui se termine avec une nouvelle recherche 