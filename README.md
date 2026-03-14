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

**Saisie interactive** (Ctrl+D pour terminer) :
```bash
python carnet_lecture.py
```

**Depuis un fichier texte** :
```bash
python carnet_lecture.py ma_note.txt
```

Le script affiche un aperçu des fichiers qui seront créés ou mis à jour, puis demande une confirmation avant d'écrire quoi que ce soit dans le vault.

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
