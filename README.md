# 🏢 Agence digitale autonome

Une **équipe d'agents IA orchestrée par un Manager** qui va de la **prospection**
jusqu'à la **livraison d'un site web déployé** — sans qu'aucune étape ne ressemble
à un site « fait par IA ».

> Détecter un prospect au site daté/cassé → rédiger un email humain (brouillon) →
> *(sur acceptation)* cadrer → designer → rédiger → coder → tester → déployer.

---

## ✨ Ce que ça fait

| Étape | Agent | Résultat |
|------|-------|----------|
| 1. Détecter | 🔍 **Scout** | Liste qualifiée de prospects + diagnostic technique |
| 2. Approcher | ✍️ **Closer** | Brouillon d'email personnalisé (**jamais envoyé**) |
| — | 🤝 *Porte d'acceptation* | La production ne démarre **que** si le prospect accepte |
| 3. Cadrer | 🎯 **Strategist** | Objectif, cible, arborescence, **type de site choisi dynamiquement** |
| 4. Designer | 🎨 **Designer** | **Direction artistique unique** (palette, typo, archétype, tokens) |
| 5. Rédiger | 🖊️ **Copywriter** | Contenu **sur-mesure** + SEO (zéro lorem ipsum) |
| 6. Coder | 💻 **Builder** | Site réel (HTML sémantique, CSS par tokens, SVG dessinés) |
| 7. Contrôler | 🔎 **Inspector** | QA + **droit de veto** sur tout rendu générique (boucle) |
| 8. Optimiser | 📈 **Optimizer** | Meta, JSON-LD, sitemap, robots, tracking RGPD |
| 9. Lancer | 🚀 **Launcher** | Build + **déploiement local vérifié** (HTTP 200 + contenu) |

Le tout est piloté par le 🧭 **Manager** : il découpe, assigne, applique des
**critères d'acceptation explicites**, **relance** en cas d'échec et orchestre la
**boucle qualité**.

---

## 🚀 Démarrage rapide

**Prérequis :** Python 3.8+ (aucune dépendance à installer).

### Option 1 — le site « L'agence » + Mission Control (recommandé)

```bash
python agency.py dashboard
# → http://127.0.0.1:7000/      (Ctrl+C pour arrêter)
```

- **`/`** : la page de vente **« L'agence »** — ludique, avec les **avatars 3D**
  de chaque agent, l'équipe par pôle, le process et les arguments.
- **`/app`** : la **salle de contrôle (Mission Control)** où tu **vois le Manager
  piloter l'équipe en direct** — agent actif mis en évidence, pipeline qui avance,
  flux d'activité, prospects, et aperçu du site produit.

Dans Mission Control : clique **« Lancer la démo »** (ou **« Lancer la mission »**
sur un prospect), règle la **cadence** pour bien voir chaque agent travailler.

> Les avatars sont dans `src/agency/web/avatars/` et le casting complet dans
> `data/roster.json` (8 pôles, 19 agents + catalogue étendu).

### Option 2 — en ligne de commande

```bash
# Démonstration complète : de la détection au site déployé en local
python agency.py demo

# Puis servir le site produit (Ctrl+C pour arrêter)
python agency.py serve atelier-moreau-ebenisterie-d-art
# → http://127.0.0.1:8800/
```

Sous Windows (PowerShell), des raccourcis existent dans `scripts/` :

```powershell
.\scripts\demo.ps1
.\scripts\serve.ps1 atelier-moreau-ebenisterie-d-art
```

---

## 🧰 Toutes les commandes

```bash
python agency.py demo                 # démo complète bout-en-bout (auto)
python agency.py scout                # prospection : liste qualifiée -> state/prospects.json
python agency.py outreach [n]         # brouillons d'emails pour les n meilleurs prospects
python agency.py accept <slug|index>  # le prospect accepte -> production + déploiement
python agency.py serve <slug>         # (re)servir le site livré en local (port 8800)
python agency.py status               # état détaillé de la dernière mission
python agency.py team                 # présenter l'équipe d'agents
```

`<index>` = numéro affiché par `scout` ; `<slug>` = nom de dossier dans `deliverables/`.

---

## 🗂️ Structure du projet

```
.
├── agency.py                  # CLI : point d'entrée de tous les workflows
├── README.md
├── requirements.txt           # (vide : 100 % bibliothèque standard)
├── .claude/agents/            # 1 sous-agent Claude par rôle (persona + prompt système)
│   ├── manager.md  scout.md  closer.md  strategist.md  designer.md
│   └── copywriter.md  builder.md  inspector.md  optimizer.md  launcher.md
├── src/agency/                # le moteur d'orchestration
│   ├── manager.py             # 🧭 orchestrateur (retries, critères, boucle QA)
│   ├── state.py               # état partagé sur fichiers (le « tableau blanc »)
│   ├── personas.py            # charge les personas depuis .claude/agents/*.md
│   ├── utils.py               # I/O, slug, graine, contraste WCAG
│   └── agents/                # 1 module par agent (même contrat AgentResult)
│       ├── scout.py  closer.py  strategist.py  designer.py  copywriter.py
│       └── builder.py  inspector.py  optimizer.py  launcher.py
├── data/prospect_pool.json    # vivier de prospects (= sortie simulée d'un crawl)
├── scripts/                   # raccourcis .ps1 (Windows) et .sh (Unix)
├── state/                     # généré : runs/<id>/state.json, prospects.json
├── outreach/drafts/           # généré : brouillons d'emails (jamais envoyés)
└── deliverables/<slug>/       # généré : src/ (site) + dist/ (build servi)
```

---

## 🔗 L'état partagé (comment les agents se parlent)

Chaque mission a un dossier `state/runs/<run_id>/state.json`. C'est le **canal
unique** de transmission : un agent lit le `blackboard`, y écrit sa section, le
suivant la relit.

```
blackboard:  audit → outreach → strategy → design → copy → build → qa → seo → deploy
```

Le Manager met à jour `stages[]` (statut, tentatives, score) et `log[]`
(qui a fait quoi, quand). Tout est lisible à la main pendant ou après la mission.

---

## 🛡️ Garanties « jamais un site fait par IA »

- **Direction artistique unique à chaque fois** : le Designer *compose* (archétype
  × palette engagée × typographie caractérielle × tokens) à partir d'une **graine
  déterministe** dérivée du client. Deux clients ⇒ deux mondes visuels.
- **Jamais le générique** : bleu Bootstrap, Arial/Inter/Roboto et layouts
  passe-partout sont **bannis** ; un **score de distinctivité** est exigé.
- **Contenu écrit pour le client réel** : métier, valeurs, histoire, ville —
  **zéro lorem ipsum**, accroches incarnées.
- **Veto de l'Inspector** : il **rejette** toute copie générique (« bienvenue sur
  notre site »…) et toute DA fade, et **renvoie en boucle** vers le bon agent.

## ⚖️ Conformité outreach

Les emails sont **courts**, **naturels**, avec **un seul appel à l'action**,
fondés sur le **vrai problème** détecté. Ils sont **générés en brouillon
uniquement** : aucun envoi automatique (RGPD / CAN-SPAM), avec mention
d'opposition et base légale.

---

## 🧩 Ajouter / modifier un agent (sans rien casser)

Le Manager ne connaît que le contrat `AgentResult`. Pour ajouter un agent :

1. créer `src/agency/agents/<nom>.py` avec une fonction
   `run(run, attempt, issues) -> AgentResult` ;
2. créer sa persona `.claude/agents/<nom>.md` ;
3. l'insérer dans `PIPELINE` (`src/agency/state.py`) et lui donner une politique
   dans `POLICY` (`src/agency/manager.py`).

Aucun autre fichier à toucher. Modifier la **personnalité** d'un agent = éditer
son `.md`, sans toucher au code.

---

## 🔌 Du simulé au réel

Le moteur tourne **hors-ligne et déterministe** pour être démontrable partout.
Pour le passer en production, on remplace des points d'entrée isolés :

| Simulé aujourd'hui | À brancher pour la prod |
|---|---|
| `scout.discover()` lit un vivier JSON | crawler web réel (`requests`/`playwright`) |
| Acceptation auto en démo | réponse réelle du prospect (boîte mail / CRM) |
| Déploiement local (`http.server`) | hébergeur statique / Netlify / serveur CMS |
| Envoi d'email | **volontairement absent** (brouillon + validation humaine) |

---

## 🧪 Tester l'anti-générique

La démo **montre la boucle QA en action** : le premier jet contient deux défauts
réalistes (accroche encore générique + illustration sans nom accessible).
L'Inspector pose son **veto**, renvoie vers le **Copywriter** et le **Builder**,
et ne valide qu'au second tour. C'est visible dans la sortie console et dans
`state/runs/<id>/qa-report.md`.
