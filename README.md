# 📚 Carnet de lecture littéraire

Transforme des notes brutes de lecture en fiches Markdown structurées et interconnectées dans un vault **Obsidian**, via l'API **Claude**.

```
note brute (texte / futur: audio, image)
        ↓
   API Claude
  (JSON structuré)
        ↓
  Vault Obsidian
 (fiches .md liées)
```

---

## Prérequis

- Python 3.11+
- Un compte Anthropic avec une clé API → [console.anthropic.com](https://console.anthropic.com)
- Un vault Obsidian existant

---

## Installation

```bash
git clone <repo>
cd Brain
pip install -r requirements.txt
```

---

## Configuration

Édite le fichier `.env` à la racine :

```env
ANTHROPIC_API_KEY=sk-ant-...
VAULT_PATH=/chemin/vers/ton/vault/Obsidian
```

> La clé API n'est jamais committée (`.gitignore`).

---

## Usage

```bash
python main.py                    # saisie interactive (Ctrl+D pour terminer)
python main.py ma_note.txt        # depuis un fichier texte
python main.py --help             # affiche l'aide complète
```

Le script affiche un aperçu des fichiers qui seront créés ou mis à jour, puis demande une confirmation avant d'écrire quoi que ce soit dans le vault.

### Validation des arguments

| Cas | Message |
|-----|---------|
| Plus d'un argument | `❌ Erreur : trop d'arguments…` |
| Fichier introuvable | `❌ Erreur : fichier introuvable : …` |
| Extension inconnue | `❌ Erreur : extension non reconnue : '…'` |
| Fichier audio (`.mp3`, `.wav`…) | `❌ Erreur : le format audio n'est pas encore supporté` |
| Fichier image (`.jpg`, `.png`…) | `❌ Erreur : le format image n'est pas encore supporté` |
| `.env` incomplet | `❌ Erreur : ANTHROPIC_API_KEY / VAULT_PATH non défini…` |

---

## Architecture du vault généré

Tout est créé sous `VAULT_PATH/Littérature/` :

```
Littérature/
├── 00_Bibliotheque.md              ← index global de tous les livres
├── Auteurs/
│   └── Gustave Flaubert.md         ← fiche auteur (créée une fois)
├── Mouvements/
│   └── Réalisme.md                 ← fiche mouvement (créée une fois)
├── Personnages/
│   └── Emma Bovary.md              ← fiche personnage (créée une fois)
├── Livres/
│   └── Madame Bovary/
│       ├── 00_Index.md             ← index du livre + liens chapitres
│       ├── Personnages.md          ← tous les personnages du livre
│       ├── Themes.md               ← tous les thèmes (#tags)
│       └── Chapitres/
│           ├── Ch_01.md
│           └── Ch_02.md
└── Citations/
    └── Madame Bovary_citations.md  ← toutes les citations regroupées
```

Tous les fichiers contiennent un **frontmatter YAML** (tags, auteur, date d'import…) pour les requêtes Dataview dans Obsidian.

Tous les liens internes utilisent la syntaxe `[[Nom]]` sans extension.

---

## Structure du code

```
Brain/
├── main.py              ← point d'entrée : python main.py
├── config.py            ← constantes et chemins vault
├── claude_api.py        ← appel API + prompt système
├── markdown_builder.py  ← génération du Markdown
├── vault_writer.py      ← écriture dans Obsidian
├── input_handler.py     ← lecture note (texte, futur: audio, OCR)
└── cli.py               ← affichage terminal et confirmation
```

---

## Fonctionnalités

| Statut | Fonctionnalité |
|--------|---------------|
| ✅ | Import depuis texte brut (stdin ou fichier) |
| ✅ | Analyse littéraire via Claude (auteur, mouvement, thèmes, citations…) |
| ✅ | Génération de fiches chapitre, auteur, mouvement, personnage |
| ✅ | Index par livre et bibliothèque globale |
| ✅ | Logique append — jamais d'écrasement des fiches existantes |
| ✅ | Frontmatter YAML sur tous les fichiers |
| ✅ | Confirmation terminal avant écriture |
| 🔜 | Import audio (transcription Whisper) |
| 🔜 | Import image/scan (OCR Tesseract) |
| 🔜 | Mode batch (dossier de notes) |
