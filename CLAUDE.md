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
│   └── notion_writer.py     ← NotionWriter : backend Notion complet (notion-client)
├── templates/
│   ├── base.html                    ← layout commun (CDN, polices, Alpine.js)
│   ├── index.html                   ← page principale (layout deux colonnes)
│   ├── settings.html                ← page paramètres (backend, credentials)
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
| `write_personnages_individuels(data, ch_num)` | Crée ou met à jour les fiches personnages (liens inter-œuvres) |
| `update_bibliotheque(data)` | Met à jour l'index global |
| `get_existing_context(titre)` | Retourne `{personnages, themes, nb_chapitres}` |

### Pipeline deux passes — enrichissement du contexte (`claude_api.py`)

Avant l'appel principal à Claude, le pipeline effectue un appel léger pour extraire le titre, puis injecte le contexte existant du vault dans le message utilisateur :

1. **Passe 1 — `extract_title(raw_note)`** : appel Claude minimal (`max_tokens=256`, prompt `TITLE_PROMPT`) qui retourne `{"titre": "...", "auteur": "..."}`. Retourne `{}` sans exception en cas d'échec.

2. **Récupération du contexte** : `writer.get_existing_context(titre)` → `{personnages, themes, nb_chapitres}`. Si cette étape échoue, le pipeline continue avec `context = {}`.

3. **Passe 2 — `call_claude(raw_note, context=context, ia_level=ia_level)`** : si `context.nb_chapitres > 0`, `_build_context_block(context)` est préfixé au message utilisateur avec personnages, thèmes et numéro de chapitre déjà connus. Sinon, comportement identique à l'ancien (pas d'injection inutile pour un premier chapitre).

**Règle d'injection conditionnelle** : le bloc contexte n'est injecté que si `nb_chapitres > 0`. Un premier import passe directement en passe 2.

### Niveau d'implication de l'IA (`ia_level`)

Paramètre entier 1–5 transmis par le frontend via `POST /analyze` (`ia_level`, défaut `3`). Injecté en tête du message utilisateur via `IA_LEVEL_INSTRUCTIONS[ia_level]` dans `call_claude`.

| Valeur | Label | Comportement Claude |
|--------|-------|---------------------|
| 1 | Transcription pure | Reste au plus proche de la note brute, minimise les inférences |
| 2 | Légèrement enrichi | Structure et reformule légèrement, champs manquants complétés avec discrétion |
| 3 | Équilibré (défaut) | Mix fidélité / enrichissement littéraire naturel |
| 4 | Analyse approfondie | Développe et contextualise, analyses narratives et psychologiques |
| 5 | Immersion totale | Mobilise tout le savoir littéraire, résumé riche, liens inter-œuvres |

L'instruction de niveau est toujours injectée en tête, avant le bloc contexte éventuel et la note brute.

**Fonctions `claude_api.py` :**

| Fonction | Description |
|----------|-------------|
| `extract_title(raw_note)` | Appel Claude léger — retourne `{titre, auteur}` ou `{}` |
| `_build_context_block(context)` | Formate le contexte existant en bloc texte pour injection |
| `_strip_code_fences(text)` | Retire les balises ` ```json ``` ` (mutualisé avec `call_claude`) |
| `call_claude(raw_note, context=None, ia_level=3)` | Appel complet — injecte niveau + contexte si `nb_chapitres > 0` |

### Routes Flask (`app.py`)

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Page principale (rendu `index.html`) |
| `/analyze` | POST | Reçoit `{note}`, appelle `call_claude()`, retourne `{data, ch_num, preview_files}` |
| `/import` | POST | Reçoit `{data, ch_num}`, appelle toutes les fonctions `write_*`, retourne `{files}` |
| `/status` | GET | Retourne la liste des livres existants dans le vault `{books}` |
| `/settings` | GET | Page paramètres — passe les valeurs `.env` actuelles au template via `current` |
| `/settings/save` | POST | Reçoit `{WRITER_BACKEND, VAULT_PATH, ANTHROPIC_API_KEY, NOTION_TOKEN, NOTION_ROOT_PAGE_ID}`, met à jour `.env` via `_update_env_file()`, recharge l'env via `load_dotenv(override=True)`, réinstancie le `writer` global |

### Helper `_update_env_file(updates: dict)` (`app.py`)

Met à jour les clés dans `.env` sans écraser les lignes non modifiées ni les commentaires. Parcourt les lignes existantes et remplace les valeurs connues ; ajoute les clés absentes à la fin du fichier.

**Note :** `VAULT_PATH` est un constant de `config.py` figé à l'import. La modification prend effet dans `.env` immédiatement, mais les chemins utilisés par `ObsidianWriter` ne sont mis à jour qu'au prochain redémarrage du serveur. `WRITER_BACKEND` et les credentials Notion/Anthropic, eux, sont relus dynamiquement lors de la réinstanciation du writer.

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
│   └── Nom du personnage.md        ← fiche personnage — mise à jour à chaque import (liens inter-œuvres)
└── Livres/
    └── Titre du livre/
        ├── 00_Index.md             ← vue d'ensemble + liens chapitres (append)
        ├── Personnages.md          ← liste agrégée des personnages (append)
        ├── Themes.md               ← liste agrégée des thèmes (append)
        ├── Citations.md            ← toutes les citations du livre (append)
        └── Chapitres/
            └── Ch_01.md            ← une note par chapitre/passage (nouveau fichier)
```

---

## Règles de comportement critiques

1. **Ne jamais écraser** `Auteurs/*.md` et `Mouvements/*.md` — créés une seule fois, jamais regénérés
2. **Personnages** (`Personnages/*.md`) — jamais recréés, mais **mis à jour** à chaque import : nouvelles œuvres ajoutées dans `oeuvres_liees`, `## Présent dans ces œuvres` et `## Apparitions par œuvre` (append strict, rien n'est supprimé)
3. **Toujours valider en terminal** avant toute écriture dans le vault (aperçu + confirmation o/n)
4. **Liens internes** toujours en syntaxe Obsidian `[[Nom du fichier]]` sans extension `.md`
5. **Append uniquement** pour `Personnages.md`, `Themes.md`, `Citations.md`, `00_Index.md`, `00_Bibliotheque.md`
6. **Auto-numérotation** des chapitres : `Ch_01.md`, `Ch_02.md`… basée sur les fichiers existants
7. **Frontmatter YAML** en tête de chaque fichier généré — voir règles détaillées ci-dessous

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
| `Personnages/*.md` | `type/personnage`, `statut/importé` + `oeuvres_liees: ["[[Titre]]"…]` |
| `Personnages.md` (livre) | `type/personnages-livre`, `statut/importé` |
| `Themes.md` (livre) | `type/themes-livre`, `statut/importé` |
| `Citations.md` (livre) | `type/citations`, `statut/importé` |
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
- [x] Citations agrégées par livre dans `Livres/<Titre>/Citations.md` (plus de dossier global `Citations/`)
- [x] Personnages agrégés par livre + fiches individuelles avec liens inter-œuvres (`oeuvres_liees`, `## Présent dans ces œuvres`, `## Apparitions par œuvre`)
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
- [x] **Backend Notion** : `NotionWriter` complet (databases auto-créées, relations, citations en sous-pages, personnages inter-œuvres)
- [x] **Page Paramètres** (`/settings`) : configuration backend et credentials via l'interface web sans toucher au `.env`
- [x] **Pipeline deux passes** : `extract_title()` → `get_existing_context()` → `call_claude(context=…)` — cohérence inter-chapitres (personnages, thèmes, numérotation)

## Architecture Notion (WRITER_BACKEND=notion)

Structure créée automatiquement sous `NOTION_ROOT_PAGE_ID` :

```
📚 Page racine (NOTION_ROOT_PAGE_ID)
├── 📗 Livres      (database) — une page par livre + sous-page Citations
├── 📄 Chapitres   (database) — une page par chapitre importé
├── 👤 Auteurs     (database) — une page par auteur (créée une fois)
├── 🎭 Personnages (database) — une page par personnage (mise à jour à chaque import)
└── 🏛️ Mouvements (database) — une page par mouvement (créée une fois)
```

### Relations inter-databases

| Database    | Propriété   | → Cible     |
|-------------|-------------|-------------|
| Chapitres   | Livre       | → Livres    |
| Chapitres   | Auteur      | → Auteurs   |
| Chapitres   | Mouvement   | → Mouvements|
| Livres      | Auteur      | → Auteurs   |
| Livres      | Mouvement   | → Mouvements|
| Auteurs     | Mouvement   | → Mouvements|
| Personnages | Livres      | → Livres (multi) |
| Personnages | Auteurs     | → Auteurs (multi) |

### Citations en sous-pages

Les citations ne sont PAS une database séparée. Chaque page Livre contient une sous-page `Citations` (child page) alimentée en append à chaque import. Structure du corps de la sous-page :
```
# Citations — Titre du livre
---
## Chapitre X
> Citation 1
> Citation 2
```

### Comportements Notion vs Obsidian

| Méthode              | Obsidian         | Notion                                   |
|----------------------|------------------|------------------------------------------|
| `update_personnages` | Fichier append   | no-op (géré par `write_personnages_individuels`) |
| `update_themes`      | Fichier append   | no-op (champ `multi_select` sur Chapitres) |
| `update_bibliotheque`| Fichier append   | no-op (la database Livres est la bibliothèque) |
| `write_auteur`       | Path             | page_id (str)                            |
| `write_mouvement`    | Path             | page_id (str)                            |

**Note :** `app.py` et `cli.py` appellent `rel(path)` sur tous les retours, ce qui suppose des objets `Path`. Une mise à jour future sera nécessaire pour afficher les URLs Notion dans l'interface web.

### Initialisation au démarrage

`NotionWriter.__init__()` appelle `_ensure_databases()` qui :
1. Liste les child_database blocks sous la page racine
2. Crée les databases manquantes dans l'ordre : Mouvements → Auteurs → Livres → Personnages → Chapitres (ordre respectant les dépendances de relations)
3. Stocke les IDs dans `self._db_ids`

### Retry automatique (rate limit)

3 tentatives max avec backoff exponentiel (1s, 2s) sur erreur HTTP 429.

## Prochaines étapes

- [ ] **Entrée audio** : intégration Whisper pour transcrire une note vocale avant envoi à Claude
- [ ] **Entrée image/scan** : intégration Tesseract OCR pour extraire le texte d'une photo de page
- [ ] **Mode batch** : traiter plusieurs notes d'un dossier en une seule passe
- [ ] **Mise à jour des fiches auteur** : enrichissement progressif au fil des imports
- [ ] **Compatibilité app.py / cli.py pour Notion** : adapter `rel()` pour afficher les URLs Notion dans l'interface web
