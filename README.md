# README → PowerPoint

> Convertissez automatiquement n'importe quel fichier README.md en une présentation PowerPoint professionnelle grâce à l'intelligence artificielle.

---

## Aperçu

**README to PowerPoint** est une application web full-stack qui exploite un pipeline d'agents IA pour analyser le contenu d'un fichier README, l'adapter à un public cible, extraire les couleurs de la charte graphique d'un logo, puis générer un fichier `.pptx` prêt à télécharger — le tout en quelques secondes.

L'utilisateur peut ensuite affiner la présentation générée via un chatbot intégré, sans retoucher manuellement PowerPoint.

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| 📄 **Upload README** | Glisser-déposer ou sélection d'un fichier `.md` / `.txt` |
| 🎨 **Extraction de marque** | Analyse automatique du logo pour extraire les couleurs primaires et d'accent |
| 👥 **Audience adaptative** | Génération différenciée selon 3 profils : Développeur, Manager, Investisseur |
| 🌐 **Multilingue** | Même langue que le README (auto-détectée), ou FR + EN en simultané (téléchargement ZIP) |
| ✨ **Personnalisation IA** | Chatbot pour modifier couleurs, polices, ton et contenu en langage naturel |
| 👁 **Aperçu en temps réel** | Prévisualisation slide par slide avec le design exact du PPTX généré |
| 📊 **Score README** | Analyse IA de la qualité du README (clarté, complétude, structure) |
| 🕓 **Historique persistant** | Toutes les générations sont sauvegardées et restent disponibles après redémarrage |
| 🌙 **Mode sombre** | Interface entièrement adaptée light / dark |
| 🔗 **Import GitHub** | Import direct depuis une URL de dépôt GitHub |

---

## Architecture

L'application repose sur un pipeline **LangGraph** composé de trois agents séquentiels :

```
README.md
    │
    ▼
┌─────────────────┐
│  Parser Agent   │  ──► LLM (claude-haiku-4-5 via OpenRouter)
│                 │       Analyse le README, structure les slides
│  Fallback :     │       selon le squelette audience/langue
│  Markdown parse │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Branding Agent  │  ──► ColorThief (extraction de palette)
│                 │       Détecte primary + accent depuis le logo
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PPTX Agent     │  ──► python-pptx
│                 │       Génère le fichier .pptx avec le design
│                 │       et retourne effective_colors pour l'aperçu
└────────┬────────┘
         │
         ▼
   presentation.pptx
```

### Stack technique

| Couche | Technologies |
|---|---|
| **Backend** | Python 3.13, FastAPI, Uvicorn |
| **Pipeline IA** | LangGraph (StateGraph), OpenRouter API |
| **LLMs** | `claude-haiku-4-5` (parsing), `claude-sonnet-4-6` (chat) |
| **Génération PPTX** | python-pptx |
| **Extraction couleurs** | ColorThief, Pillow |
| **Frontend** | HTML / CSS / JavaScript vanilla (servi inline par FastAPI) |
| **Persistance** | JSON file (sessions.json) |

---

## Structure du projet

```
readme-to-pptx/
├── server.py               # Application FastAPI + interface web complète
├── graph/
│   └── pipeline.py         # Définition du StateGraph LangGraph
├── agents/
│   ├── parser_agent.py     # Agent d'analyse et structuration du README
│   ├── branding_agent.py   # Agent d'extraction des couleurs du logo
│   ├── pptx_agent.py       # Agent de génération de la présentation
│   └── utils.py            # Client OpenRouter, helpers
├── docs/
│   └── design-system.md    # Design system de référence
├── output/                 # Présentations générées (gitignored)
├── pyproject.toml
├── uv.lock
└── .env                    # Clé API (gitignored)
```

---

## Installation

### Prérequis

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets recommandé)
- Une clé API [OpenRouter](https://openrouter.ai/)

### Étapes

**1. Cloner le dépôt**

```bash
git clone https://github.com/Laabidi-Eya/README-vers-PowerPoint.git
cd README-vers-PowerPoint
```

**2. Créer l'environnement et installer les dépendances**

```bash
uv sync
```

Ou avec pip :

```bash
pip install -r requirements.txt
```

**3. Configurer les variables d'environnement**

Créez un fichier `.env` à la racine :

```env
OPENROUTER_API_KEY=votre_clé_openrouter
USE_LLM=true
```

> Si `USE_LLM=false`, l'application fonctionne en mode dégradé (parsing Markdown sans LLM).

**4. Lancer le serveur**

```bash
uv run python server.py
```

Ou :

```bash
python server.py
```

L'application est accessible sur **http://localhost:8000**

---

## Utilisation

1. **Déposez** votre fichier README.md dans la zone d'upload (ou importez depuis GitHub)
2. **Ajoutez** optionnellement le logo de votre entreprise — les couleurs seront extraites automatiquement
3. **Choisissez** le public cible : Développeurs, Managers ou Investisseurs
4. **Sélectionnez** la langue : FR, EN ou les deux
5. **Cliquez** sur "Générer PowerPoint"
6. **Prévisualisez** la présentation slide par slide dans l'aperçu intégré
7. **Téléchargez** le fichier `.pptx` ou affinez via le **chatbot IA** (onglet Personnaliser)

---

## Pipeline de génération

### Parser Agent

- Nettoie le README (supprime les blocs de code, commandes CLI)
- Filtre le contenu selon l'audience (ex : pas de Docker pour les Managers)
- Appelle le LLM avec un squelette de slides pré-défini par audience/langue
- Fallback automatique sur le parsing Markdown si le LLM échoue

### Branding Agent

- Extrait une palette de 6 couleurs depuis le logo via ColorThief
- Sélectionne la couleur primaire (sombre, peu saturée) et la couleur d'accent (vivid)
- Garantit un contraste lisible entre texte et fond

### PPTX Agent

- Génère une slide de garde + N slides de contenu
- Applique les couleurs de marque, polices et paramètres de design
- Place le logo sur chaque slide si fourni
- Retourne `effective_colors` pour que l'aperçu web soit identique au PPTX réel

---

## Personnalisation via le Chatbot

Après génération, l'onglet **Personnaliser** permet de modifier la présentation en langage naturel :

```
"Change les couleurs en bleu marine et or"
"Rends le ton plus formel"
"Ajoute une slide sur la sécurité"
"Utilise la police Arial"
```

Le chatbot utilise `claude-sonnet-4-6` pour interpréter la demande et regénérer la présentation avec les nouveaux paramètres.

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `OPENROUTER_API_KEY` | Clé API OpenRouter (obligatoire) | — |
| `USE_LLM` | Activer le LLM (`true` / `false`) | `true` |

---

## Dépendances principales

```
fastapi          >= 0.115.0    # Framework web
uvicorn          >= 0.34.0     # Serveur ASGI
langgraph        >= 1.2.6      # Orchestration des agents IA
python-pptx      >= 1.0.2      # Génération de fichiers PowerPoint
colorthief       >= 0.2.1      # Extraction de palette couleur
pillow           >= 11.0.0     # Traitement d'images
python-dotenv    >= 1.2.2      # Gestion des variables d'environnement
python-multipart >= 0.0.20     # Upload de fichiers
```

---


