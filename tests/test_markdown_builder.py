import pytest
from markdown_builder import fm, build_chapter_md
from writers.obsidian_writer import sanitize


# ---------------------------------------------------------------------------
# fm() — frontmatter YAML
# ---------------------------------------------------------------------------

def test_fm_tags_no_hash():
    result = fm(["type/chapitre", "theme/amour", "statut/importé"])
    for line in result.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") and not stripped.startswith('- "[['):
            tag = stripped[2:]
            assert not tag.startswith("#"), f"Tag commençant par # : {tag!r}"


def test_fm_wikilinks_quoted():
    result = fm([], auteur="[[Victor Hugo]]", titre="[[Les Misérables]]")
    assert '"[[Victor Hugo]]"' in result
    assert '"[[Les Misérables]]"' in result


def test_fm_dates_not_quoted():
    result = fm([], date_creation="2026-03-14", date_modification="2026-03-15")
    assert "date_creation: 2026-03-14" in result
    assert "date_modification: 2026-03-15" in result
    assert 'date_creation: "' not in result
    assert 'date_modification: "' not in result


def test_fm_aliases_always_present():
    result = fm(["type/chapitre"])
    assert "aliases:" in result


# ---------------------------------------------------------------------------
# build_chapter_md()
# ---------------------------------------------------------------------------

def test_build_chapter_md_structure():
    data = {
        "auteur": "Victor Hugo",
        "titre": "Les Misérables",
        "chapitre_ou_passage": "Tome I, Chapitre 1",
        "resume": "Jean Valjean sort de prison.",
        "personnages": ["Jean Valjean"],
        "themes": ["rédemption", "justice"],
        "mouvement_litteraire": {
            "nom": "Romantisme",
            "epoque": "XIXe siècle",
            "description": "",
            "contexte_historique": "",
        },
        "contexte_historique_oeuvre": "Restauration.",
        "fiche_auteur": {},
        "auteurs_lies": [],
        "avertissements": [],
    }
    result = build_chapter_md(data, 1)
    assert "## 📖 Résumé" in result
    assert "## 👤 Personnages présents" in result
    assert "## 🏷️ Thèmes" in result
    assert "type/chapitre" in result


# ---------------------------------------------------------------------------
# sanitize()
# ---------------------------------------------------------------------------

def test_sanitize_removes_forbidden_chars():
    assert sanitize('Hello/World:Test*?"<>|') == "HelloWorldTest"
    assert sanitize("Normal Title") == "Normal Title"
    assert sanitize("Le Père Goriot") == "Le Père Goriot"
    assert sanitize("") == ""
