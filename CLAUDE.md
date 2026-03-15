# Carnet de lecture littéraire — Mémoire du projet

## Description

Script Python qui transforme des notes brutes de lecture (texte libre, futur : audio Whisper, image OCR) en fiches Markdown structurées et interconnectées dans un vault Obsidian.

Le pipeline : **note brute → API Claude (JSON structuré) → fichiers Markdown Obsidian**

---

## Stack technique

- **Python 3.11+**
- **SDK Anthropic** (`anthropic`) — modèle `claude-sonnet-4-20250514`
- **python-dotenv** — gestion des variables d'environnement
- **Flask 3.0+** — serveur web backend
- **Tailwind CSS + DaisyUI** via CDN — composants et styles
- **Alpine.js** via CDN — interactivité client
- **markdown-it** via CDN — rendu Markdown temps réel
- **Lucide Icons** via CDN — icônes
- **Google Fonts Inter** — typographie
- **Whisper** (OpenAI) — transcription audio *(à venir)*
- **Tesseract OCR** — extraction texte depuis image *(à venir)*

Configuration via `.env` (jamais commité) :
```
ANTHROPIC_API_KEY=sk-ant-...
VAULT_PATH=/chemin/vers/vault/Obsidian

# Backend de destination (obsidian ou notion)
WRITER_BACKEND=obsidian

# Notion (laisser vide si non utilisé)
NOTION_TOKEN=
NOTION_ROOT_PAGE_ID=
```

---

## Architecture du code

```
Brain/
├── app.py               ← serveur Flask (interface web, point d'entrée principal)
├── main.py              ← point d'entrée terminal, orchestration uniquement
├── config.py            ← constantes MODEL, VAULT_PATH, WRITER_BACKEND et chemins
├── claude_api.py        ← SYSTEM_PROMPT, call_claude(), gestion erreurs API
├── markdown_builder.py  ← toutes les fonctions build_*() et fm()
├── input_handler.py     ← show_help(), collect_raw_note() + validation args + stubs Whisper / Tesseract
├── cli.py               ← preview_and_confirm(), print_report()
├── writers/
│   ├── __init__.py          ← factory get_writer(), exports sanitize / next_chapter_number
│   ├── base_writer.py       ← classe abstraite BaseWriter (10 méthodes)
│   ├── obsidian_writer.py   ← ObsidianWriter : écriture fichiers .md dans le vault local
│   └── notion_writer.py     ← NotionWriter : stubs avec TODO détaillés (à implémenter)
├── templates/
│   ├── base.html                    ← layout commun (CDN, polices, Alpine.js)
│   ├── index.html                   ← page principale (layout deux colonnes)
│   └── components/
│       ├── preview_card.html        ← macro Jinja2 : carte de section avec animation
│       └── file_badge.html          ← macro Jinja2 : badge fichier +/~/=
└── static/
    ├── app.js                       ← logique Alpine.js (analyze, import, révélation progressive)
    └── style.css                    ← overrides Tailwind, animations, scrollbar
```

**Ordre des dépendances (pas d'import circulaire) :**
`config` ← `markdown_builder` ← `writers/obsidian_writer` ← `writers/__init__` ← `main` / `app`
`config` ← `claude_api` ← `main` / `app`
`config` + `writers` ← `cli` ← `main`
`input_handler` ← `main` (aucune dépendance projet)

**Interface abstraite `BaseWriter` (writers/base_writer.py) :**

| Méthode | Description |
|---------|-------------|
| `write_chapter(data, ch_num)` | Crée la fiche chapitre |
| `update_index(data, ch_num)` | Crée ou met à jour l'index du livre |
| `update_personnages(data)` | Agrège les personnages du livre |
| `update_themes(data)` | Agrège les thèmes du livre |
| `update_citations(data, ch_num)` | Agrège les citations du livre |
| `write_auteur(data)` | Crée la fiche auteur si absente |
| `write_mouvement(data)` | Crée la fiche mouvement si absente |
| `write_personnages_individuels(data)` | Crée les fiches personnages individuelles |
| `update_bibliotheque(data)` | Met à jour l'index global |
| `get_existing_context(titre)` | Retourne `{personnages, themes, nb_chapitres}` |

### Routes Flask (`app.py`)

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Page principale (rendu `index.html`) |
| `/analyze` | POST | Reçoit `{note}`, appelle `call_claude()`, retourne `{data, ch_num, preview_files}` |
| `/import` | POST | Reçoit `{data, ch_num}`, appelle toutes les fonctions `write_*`, retourne `{files}` |
| `/status` | GET | Retourne la liste des livres existants dans le vault `{books}` |

### Lancement

```bash
python app.py          # http://0.0.0.0:5000 (réseau local)
```

---

## Architecture du vault Obsidian

Tout est créé sous `VAULT_PATH/Littérature/` :

```
Littérature/
├── 00_Bibliotheque.md              ← index global de tous les livres (append)
├── Auteurs/
│   └── Prénom Nom.md               ← fiche auteur (créée une fois, jamais écrasée)
├── Mouvements/
│   └── Romantisme.md               ← fiche mouvement (créée une fois, jamais écrasée)
├── Personnages/
│   └── Nom du personnage.md        ← fiche personnage (créée une fois, jamais écrasée)
├── Livres/
│   └── Titre du livre/
│       ├── 00_Index.md             ← vue d'ensemble + liens chapitres (append)
│       ├── Personnages.md          ← liste agrégée des personnages (append)
│       ├── Themes.md               ← liste agrégée des thèmes (append)
│       └── Chapitres/
│           └── Ch_01.md            ← une note par chapitre/passage (nouveau fichier)
└── Citations/
    └── Titre_citations.md          ← toutes les citations du livre (append)
```

---

## Règles de comportement critiques

1. **Ne jamais écraser** `Auteurs/*.md`, `Mouvements/*.md`, `Personnages/*.md` — créés une seule fois
2. **Toujours valider en terminal** avant toute écriture dans le vault (aperçu + confirmation o/n)
3. **Liens internes** toujours en syntaxe Obsidian `[[Nom du fichier]]` sans extension `.md`
4. **Append uniquement** pour `Personnages.md`, `Themes.md`, `Citations/*.md`, `00_Index.md`, `00_Bibliotheque.md`
5. **Auto-numérotation** des chapitres : `Ch_01.md`, `Ch_02.md`… basée sur les fichiers existants
6. **Frontmatter YAML** en tête de chaque fichier généré — voir règles détaillées ci-dessous

---

## Règles frontmatter YAML (Obsidian Properties / Dataview)

### Tags hiérarchiques — sans `#`, format YAML block list

```yaml
tags:
  - type/chapitre      # type de note : chapitre, livre, auteur, mouvement, personnage,
  - type/lecture       #                citations, personnages-livre, themes-livre, bibliotheque
  - theme/rédemption   # un tag par thème littéraire détecté
  - mouvement/romantisme
  - statut/importé
```

Schéma par type de note :

| Fichier | Tags obligatoires |
|---------|------------------|
| `Ch_XX.md` | `type/chapitre`, `type/lecture`, `theme/<t>…`, `mouvement/<m>`, `statut/importé` |
| `00_Index.md` | `type/livre`, `mouvement/<m>`, `statut/importé` |
| `Auteurs/*.md` | `type/auteur`, `mouvement/<m>`, `statut/importé` |
| `Mouvements/*.md` | `type/mouvement`, `statut/importé` |
| `Personnages/*.md` | `type/personnage`, `statut/importé` |
| `Personnages.md` (livre) | `type/personnages-livre`, `statut/importé` |
| `Themes.md` (livre) | `type/themes-livre`, `statut/importé` |
| `Citations/*.md` | `type/citations`, `statut/importé` |
| `00_Bibliotheque.md` | `type/bibliotheque`, `statut/importé` |

### Wikilinks — toujours entre guillemets doubles

```yaml
auteur: "[[Victor Hugo]]"
titre: "[[Les Misérables]]"
auteurs_lies:
  - "[[Honoré de Balzac]]"
  - "[[Gustave Flaubert]]"
```

### Propriétés standards sur tous les fichiers

```yaml
aliases: []                    # toujours présent, même vide
date_creation: 2026-03-14      # format YYYY-MM-DD, non quoté
date_modification: 2026-03-14  # mis à jour automatiquement à chaque append
```

### Interdictions

- **Jamais de `#`** dans le frontmatter — les tags s'écrivent sans `#`
- **Pas de YAML imbriqué** — toutes les propriétés restent à plat

---

## État actuel du projet

- [x] Import de note brute (stdin ou fichier texte)
- [x] Appel API Claude avec prompt système JSON structuré
- [x] Génération des fiches chapitre, auteur, mouvement
- [x] Index par livre (`00_Index.md`)
- [x] Citations agrégées par livre
- [x] Personnages agrégés par livre + fiches individuelles
- [x] Index global de la bibliothèque (`00_Bibliotheque.md`)
- [x] Frontmatter YAML sur tous les fichiers générés
- [x] Configuration via `.env`
- [x] `--help` / `-h` avec message d'aide complet (affiché avant tout import projet)
- [x] Validation des arguments : trop d'args, fichier introuvable, extension inconnue, audio/image non supportés
- [x] Validation `.env` : `ANTHROPIC_API_KEY` et `VAULT_PATH` obligatoires avec message d'erreur clair
- [x] Frontmatter 100% compatible Obsidian Properties / Dataview : tags hiérarchiques, wikilinks quotés, dates non quotées, `aliases: []`, `date_modification` mis à jour à chaque append
- [x] Frontmatter sur `Personnages.md` et `Themes.md` (précédemment sans frontmatter)
- [x] Correction du bug de dédoublonnage des thèmes (vérification sur la forme stockée `#theme_slug`)
- [x] Champ `avertissements` dans le JSON Claude — anomalies détectées dans la note (personnage anachronique, confusion d'auteur, etc.), affiché dans le terminal avant confirmation
- [x] Verbosité proportionnelle : `resume` (5-10 phrases si riche), `contexte_historique_oeuvre`, `mouvement_litteraire.description/contexte_historique`, `fiche_auteur.biographie` guidés par des règles de profondeur
- [x] Interface web Flask — layout deux colonnes, dark mode par défaut, aperçu progressif, toast d'import
- [x] Routes Flask : `GET /`, `POST /analyze`, `POST /import`, `GET /status`
- [x] Révélation progressive des sections de l'aperçu (résumé → personnages → thèmes → citations → avertissements → fichiers → bouton)
- [x] Badges fichiers colorés : vert `+` nouveau, bleu `~` mis à jour, gris `=` existant
- [x] Accessible en réseau local (`0.0.0.0:5000`) depuis smartphone ou autre appareil

## Prochaines étapes

- [ ] **Entrée audio** : intégration Whisper pour transcrire une note vocale avant envoi à Claude
- [ ] **Entrée image/scan** : intégration Tesseract OCR pour extraire le texte d'une photo de page
- [ ] **Mode batch** : traiter plusieurs notes d'un dossier en une seule passe
- [ ] **Mise à jour des fiches auteur** : enrichissement progressif au fil des imports
- [ ] **Backend Notion** : implémenter `NotionWriter` (voir TODO dans `writers/notion_writer.py`)
