# 🌐 Mettre « L'agence » en ligne

L'application est **prête à être hébergée**. Le serveur détecte automatiquement
l'hébergeur (variable `PORT`) et écoute alors sur `0.0.0.0:$PORT`. Le seul geste
que je ne peux pas faire à ta place : **créer / connecter ton compte d'hébergement**.

Tout fonctionne sans aucune clé API (la prospection réelle utilise l'API publique
gratuite OpenStreetMap, et les audits se font en HTTP direct).

---

## ✅ Option recommandée — Render (gratuit, le plus simple)

1. **Crée 2 comptes gratuits** : [github.com](https://github.com) et [render.com](https://render.com).
2. **Pousse le projet sur GitHub** (depuis ce dossier) :
   ```bash
   git init
   git add -A
   git commit -m "L'agence — équipe d'agents IA autonome"
   git branch -M main
   git remote add origin https://github.com/<ton-pseudo>/lagence.git
   git push -u origin main
   ```
3. Sur **Render** → **New +** → **Blueprint** → choisis ton dépôt `lagence`.
   Render lit `render.yaml`, installe et lance tout seul.
4. Au bout de ~2 min, tu obtiens une **URL publique** du type
   `https://lagence.onrender.com` → c'est ton site « L'agence », en ligne. 🎉
   - `/`     → la page de vente avec les avatars
   - `/app`  → la salle de contrôle (prospection réelle + production live)

> Offre gratuite Render : le service se met en veille après inactivité et se
> réveille en ~30 s à la 1ʳᵉ visite. Le stockage est éphémère (les sites produits
> sont régénérés à chaque mission) — parfait pour une démo commerciale.

---

## 🐳 Option Docker (Railway, Fly.io, VPS…)

Un `Dockerfile` est fourni :
```bash
docker build -t lagence .
docker run -p 7000:7000 lagence      # puis http://localhost:7000
```
Sur Railway/Fly : « Deploy from Dockerfile », rien d'autre à configurer.

---

## 🔗 Publier les SITES produits (livrables clients) en ligne

Les sites générés sont du **HTML statique** (`deliverables/<slug>/dist/`),
publiables gratuitement en une commande (npm est déjà installé) :

```bash
# Netlify (compte gratuit, un seul login navigateur la 1ʳᵉ fois)
npx netlify-cli deploy --dir "deliverables/<slug>/dist" --prod

# ou Surge
npx surge "deliverables/<slug>/dist" mon-client.surge.sh
```

---

## 🔒 Avant une vraie mise en prod commerciale
- Mettre le domaine cible réel dans `src/agency/agents/optimizer.py` (`SITE_URL`).
- Garder l'outreach en **brouillon** (déjà le cas) : l'envoi reste un geste humain (RGPD).
- Option : brancher un vrai modèle (clé API Claude) pour un contenu encore plus
  rédactionnel — le moteur est prêt à recevoir cette extension.
