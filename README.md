# 📚 Carnet de lecture littéraire

Transforme des notes brutes de lecture en fiches structurées et interconnectées vers **Obsidian** ou **Notion**, via l'API **Claude**. Dual-backend, interface web moderne, niveau d'implication IA ajustable.

```
note brute (texte / futur: audio, image)
        ↓
   API Claude (claude-sonnet-4)
  (JSON structuré — 2 passes)
        ↓
  Obsidian (.md) ou Notion (databases)
```

---

## Démo

```
┌──────────────────────────────┬──────────────────────────────────────┐
│  📁 Obsidian  ● Live  ⚙️      │                                      │
├──────────────────────────────┤                                      │
│  Note de lecture             │   Titre — Chapitre X                 │
│  [zone de texte libre...]    │   Auteur · Mouvement                 │
│                              │                                      │
│  Implication de l'IA        │   📖 Résumé                          │
│  Fidèle ←————●————→ Enrichi │   👤 Personnages                     │
│  [Équilibré]                 │   🏷️  Thèmes                         │
│                              │   💬 Citations                       │
│  [✨ Analyser]               │   ⚠️  Points à vérifier              │
│                              │   ☐ J'ai lu les anomalies...        │
│                              │   📁 Fichiers générés               │
│                              │   [🗂️  Importer dans Obsidian]       │
└──────────────────────────────┴──────────────────────────────────────┘
```

---

## Prérequis

- Python 3.11+
- Clé API Anthropic → [console.anthropic.com](https://console.anthropic.com)
- Vault Obsidian existant **ou** compte Notion (pas les deux obligatoires)

---

## Installation et lancement

```bash
git clone <repo>
cd Brain
pip install -r requirements.txt
cp .env.example .env   # éditer les valeurs
python app.py          # http://localhost:5000
```

Accessible depuis n'importe quel appareil sur le même réseau Wi-Fi : `http://<IP-locale>:5000`

---

## Configuration `.env`

```env
# Obligatoire
ANTHROPIC_API_KEY=sk-ant-...

# Obligatoire si WRITER_BACKEND=obsidian
VAULT_PATH=/chemin/vers/ton/vault/Obsidian

# Backend de destination : obsidian (défaut) ou notion
WRITER_BACKEND=obsidian

# Obligatoire si WRITER_BACKEND=notion
NOTION_TOKEN=ntn_xxxxxxxxxxxxxxxxxxxx
NOTION_ROOT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> La clé API n'est jamais committée (`.gitignore`).

La page **⚙️ Paramètres** (`/settings`) permet de configurer le backend et les credentials directement depuis l'interface web — sans toucher au `.env`.

---

## Backend Obsidian

### Structure du vault

Tout est créé sous `VAULT_PATH/Littérature/` :

```
Littérature/
├── 00_Bibliotheque.md              ← index global de tous les livres (append)
├── Auteurs/
│   └── Gustave Flaubert.md         ← fiche auteur (créée une fois, jamais écrasée)
├── Mouvements/
│   └── Réalisme.md                 ← fiche mouvement (créée une fois, jamais écrasée)
├── Personnages/
│   └── Emma Bovary.md              ← fiche personnage — mise à jour à chaque import
└── Livres/
    └── Madame Bovary/
        ├── 00_Index.md             ← index du livre + liens chapitres (append)
        ├── Personnages.md          ← liste agrégée des personnages (append)
        ├── Themes.md               ← liste agrégée des thèmes (append)
        ├── Citations.md            ← toutes les citations du livre (append)
        └── Chapitres/
            ├── Ch_01.md
            └── Ch_02.md
```

### Règles clés

- **Jamais d'écrasement** — `Auteurs/*.md` et `Mouvements/*.md` créés une seule fois
- **Append uniquement** — `Personnages.md`, `Themes.md`, `Citations.md`, `00_Index.md`, `00_Bibliotheque.md`
- **Personnages inter-œuvres** — chaque fiche `Personnages/*.md` accumule les liens entre livres (`## Présent dans ces œuvres`, `## Apparitions par œuvre`)
- **Auto-numérotation** des chapitres : `Ch_01.md`, `Ch_02.md`… basée sur les fichiers existants

### Frontmatter YAML (compatible Obsidian Properties / Dataview)

```yaml
---
tags:
  - type/chapitre
  - type/lecture
  - theme/rédemption
  - mouvement/romantisme
  - statut/importé
auteur: "[[Victor Hugo]]"
titre: "[[Les Misérables]]"
aliases: []
date_creation: 2026-03-14
date_modification: 2026-03-14
---
```

Tags sans `#`, wikilinks entre guillemets doubles, dates au format `YYYY-MM-DD` non quotées.

---

## Backend Notion

### Configuration

**1. Créer une intégration**

1. Va sur [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Clique **New integration** → donne-lui un nom (ex. `Carnet de lecture`)
3. Sélectionne le workspace cible
4. Copie le **Internal Integration Token** (commence par `ntn_` ou `secret_`)

**2. Partager la page racine**

1. Dans Notion, crée une page vide (ex. `📚 Carnet de lecture`)
2. Ouvre la page → `···` (menu) → **Connections** → ajoute ton intégration
3. Copie l'ID depuis l'URL (32 caractères hexadécimaux après le dernier `/`)

**3. Configurer `.env`**

```env
WRITER_BACKEND=notion
NOTION_TOKEN=ntn_xxxxxxxxxxxxxxxxxxxx
NOTION_ROOT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # format brut ou URL complète acceptés
```

### Structure créée automatiquement

Au premier démarrage, `NotionWriter` crée les 5 databases dans l'ordre des dépendances :

```
📚 Page racine (NOTION_ROOT_PAGE_ID)
├── 🏛️  Mouvements  (database) — une page par mouvement (créée une fois)
├── 👤 Auteurs      (database) — une page par auteur (créée une fois)
├── 📗 Livres       (database) — une page par livre + sous-page Citations
├── 🎭 Personnages  (database) — une page par personnage (mise à jour à chaque import)
└── 📄 Chapitres    (database) — une page par chapitre/passage importé
```

Les **citations** sont des sous-pages de chaque livre (pas une database séparée).

### Propriétés des databases

| Database    | Propriétés                                                              |
|-------------|-------------------------------------------------------------------------|
| Mouvements  | Name (title), Period, Description, Context, Created                     |
| Auteurs     | Name (title), Dates, Movement, Biography, Works, Created                |
| Livres      | Name (title), Author, Movement, Chapters, Created                       |
| Personnages | Name (title), Books, Authors, Description, Appearances, Created, Modified |
| Chapitres   | Name (title), Book, Author, Movement, Chapter, Summary, Themes, Date, Warnings |

### Relations inter-databases

| Database    | Propriété  | Cible        |
|-------------|------------|--------------|
| Chapitres   | Book       | → Livres     |
| Chapitres   | Author     | → Auteurs    |
| Chapitres   | Movement   | → Mouvements |
| Livres      | Author     | → Auteurs    |
| Livres      | Movement   | → Mouvements |
| Auteurs     | Movement   | → Mouvements |
| Personnages | Books      | → Livres (multi) |
| Personnages | Authors    | → Auteurs (multi) |

> **Note technique :** les noms de propriétés sont en anglais pour éviter les conflits avec les noms internes Notion. Les queries de databases utilisent `httpx` directement (contournement d'une incompatibilité notion-client v3).

---

## Niveau d'implication de l'IA

Le slider (1–5) contrôle la profondeur d'analyse injectée dans le prompt Claude :

| Niveau | Nom | Comportement |
|--------|-----|--------------|
| 1 | Transcription pure | Retranscrit sans interpréter, minimise les inférences |
| 2 | Légèrement enrichi | Structure minimale, ta voix reste dominante |
| 3 | **Équilibré** (défaut) | Mix fidélité / connaissances littéraires |
| 4 | Analyse approfondie | Développe, contextualise, perspective critique |
| 5 | Immersion totale | Enrichissement maximum, liens inter-œuvres, savoir littéraire complet |

---

## Fonctionnalités

| Statut | Fonctionnalité |
|--------|---------------|
| ✅ | Import texte brut (stdin ou fichier `.txt`) |
| ✅ | Analyse littéraire via Claude (auteur, mouvement, thèmes, citations, contexte historique) |
| ✅ | Slider niveau d'implication IA — 5 niveaux de Fidèle à Enrichi |
| ✅ | Pipeline deux passes — cohérence inter-chapitres (contexte existant injecté) |
| ✅ | Fiches chapitre, auteur, mouvement, personnage |
| ✅ | Personnages inter-œuvres — liens entre livres automatiques |
| ✅ | Détection d'anomalies avec confirmation obligatoire avant import |
| ✅ | Jamais d'écrasement — append uniquement |
| ✅ | Backend Obsidian — fichiers `.md` locaux, frontmatter YAML, Dataview |
| ✅ | Backend Notion — 5 databases auto-créées, relations, citations en sous-pages |
| ✅ | Interface web Flask — dark/light mode, layout responsive, révélation progressive |
| ✅ | Page Paramètres `/settings` — switch backend sans toucher au `.env` |
| ✅ | Indicateur backend dans le header (cliquable → settings) |
| ✅ | Accessible en réseau local depuis smartphone |
| 🔜 | Import audio (transcription Whisper) |
| 🔜 | Import image/scan (OCR Tesseract) |
| 🔜 | Mode batch (dossier de notes) |
| 🔜 | Mode révision d'une fiche existante |
| 🔜 | Export fiche spaced repetition |
| 🔜 | Enrichissement progressif des fiches auteur |

---

## Architecture du code

```
Brain/
├── app.py               ← Flask + routes + switch backend dynamique
├── main.py              ← point d'entrée terminal (fallback)
├── config.py            ← variables d'env, chemins vault, WRITER_BACKEND
├── claude_api.py        ← pipeline deux passes, niveaux IA, JSON structuré
├── markdown_builder.py  ← constructeurs Markdown + frontmatter YAML
├── input_handler.py     ← validation args, stubs Whisper/Tesseract
├── cli.py               ← terminal UI (preview + confirmation)
└── writers/
    ├── __init__.py          ← factory get_writer(), exports sanitize / next_chapter_number
    ├── base_writer.py       ← interface abstraite BaseWriter (10 méthodes)
    ├── obsidian_writer.py   ← backend fichiers .md locaux
    └── notion_writer.py     ← backend API Notion (httpx direct)
templates/
├── base.html                    ← layout commun (CDN : Tailwind, DaisyUI, Alpine.js)
├── index.html                   ← page principale (layout deux colonnes)
├── settings.html                ← page paramètres
└── components/
    ├── preview_card.html        ← macro Jinja2 : carte de section animée
    └── file_badge.html          ← macro Jinja2 : badge fichier +/~/=
static/
├── app.js                       ← logique Alpine.js (analyze, import, révélation progressive)
└── style.css                    ← overrides Tailwind, animations, scrollbar
```

### Pipeline deux passes (`claude_api.py`)

1. **Passe 1 — `extract_title(raw_note)`** : appel Claude léger qui retourne `{titre, auteur}` (ou `{}` sans exception).
2. **Récupération du contexte** : `writer.get_existing_context(titre)` → `{personnages, themes, nb_chapitres}`.
3. **Passe 2 — `call_claude(raw_note, context, ia_level)`** : si `nb_chapitres > 0`, le contexte existant est injecté avant la note pour garantir la cohérence entre chapitres (orthographe des personnages, thèmes déjà présents, numérotation).

### Interface abstraite `BaseWriter` (`writers/base_writer.py`)

| Méthode | Description |
|---------|-------------|
| `write_chapter(data, ch_num)` | Crée la fiche chapitre |
| `update_index(data, ch_num)` | Crée ou met à jour l'index du livre |
| `update_personnages(data)` | Agrège les personnages du livre |
| `update_themes(data)` | Agrège les thèmes du livre |
| `update_citations(data, ch_num)` | Agrège les citations du livre |
| `write_auteur(data)` | Crée la fiche auteur si absente |
| `write_mouvement(data)` | Crée la fiche mouvement si absente |
| `write_personnages_individuels(data, ch_num)` | Crée ou met à jour les fiches personnages (liens inter-œuvres) |
| `update_bibliotheque(data)` | Met à jour l'index global |
| `get_existing_context(titre)` | Retourne `{personnages, themes, nb_chapitres}` |

### Routes Flask (`app.py`)

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Page principale |
| `/analyze` | POST | `{note, ia_level}` → `{data, ch_num, preview_files}` |
| `/import` | POST | `{data, ch_num}` → `{files}` |
| `/status` | GET | Liste des livres dans le vault `{books}` |
| `/config` | GET | Backend actif `{backend}` |
| `/settings` | GET | Page paramètres |
| `/settings/save` | POST | Met à jour `.env`, recharge l'env, réinstancie le writer |

---

## Usage terminal (fallback)

```bash
python main.py                    # saisie interactive (Ctrl+D pour terminer)
python main.py ma_note.txt        # depuis un fichier texte
python main.py --help             # affiche l'aide complète
```

| Cas | Message |
|-----|---------|
| Plus d'un argument | `❌ Erreur : trop d'arguments…` |
| Fichier introuvable | `❌ Erreur : fichier introuvable : …` |
| Extension inconnue | `❌ Erreur : extension non reconnue : '…'` |
| Fichier audio (`.mp3`, `.wav`…) | `❌ Erreur : le format audio n'est pas encore supporté` |
| Fichier image (`.jpg`, `.png`…) | `❌ Erreur : le format image n'est pas encore supporté` |
| `.env` incomplet | `❌ Erreur : ANTHROPIC_API_KEY / VAULT_PATH non défini…` |
