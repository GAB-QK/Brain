import os

# MUST be set before any project import — config.py calls sys.exit if absent
os.environ.setdefault("VAULT_PATH", "/tmp/test_vault_placeholder")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-placeholder")

import pytest
from pathlib import Path


@pytest.fixture
def vault_tmp(tmp_path, monkeypatch):
    """Vault temporaire isolé pour chaque test."""
    import config
    import writers.obsidian_writer as ow

    litt = tmp_path / "Littérature"

    # Patch config module attributes
    monkeypatch.setattr(config, "VAULT_PATH", tmp_path)
    monkeypatch.setattr(config, "LITTERATURE", litt)
    monkeypatch.setattr(config, "AUTEURS_DIR", litt / "Auteurs")
    monkeypatch.setattr(config, "MOUVEMENTS_DIR", litt / "Mouvements")
    monkeypatch.setattr(config, "PERSONNAGES_DIR", litt / "Personnages")
    monkeypatch.setattr(config, "LIVRES_DIR", litt / "Livres")
    monkeypatch.setattr(config, "BIBLIOTHEQUE", litt / "00_Bibliotheque.md")

    # Patch obsidian_writer module-level names (imported from config at load time)
    monkeypatch.setattr(ow, "AUTEURS_DIR", litt / "Auteurs")
    monkeypatch.setattr(ow, "MOUVEMENTS_DIR", litt / "Mouvements")
    monkeypatch.setattr(ow, "PERSONNAGES_DIR", litt / "Personnages")
    monkeypatch.setattr(ow, "LIVRES_DIR", litt / "Livres")
    monkeypatch.setattr(ow, "LITTERATURE", litt)
    monkeypatch.setattr(ow, "BIBLIOTHEQUE", litt / "00_Bibliotheque.md")

    return tmp_path


@pytest.fixture
def data_ch1():
    """Données Claude simulées — chapitre 1."""
    return {
        "titre": "Le Père Goriot",
        "auteur": "Honoré de Balzac",
        "chapitre_ou_passage": "Chapitre 1 — Arrivée à la pension",
        "numero_chapitre": 1,
        "resume": "Rastignac arrive à la pension Vauquer.",
        "personnages": ["Rastignac", "Vautrin", "Père Goriot"],
        "personnages_details": [
            {"nom": "Rastignac", "description": "Jeune provincial ambitieux.", "apparition": "Arrive à Paris."},
            {"nom": "Vautrin", "description": "Mystérieux pensionnaire.", "apparition": "Observe Rastignac."},
            {"nom": "Père Goriot", "description": "Vieil homme pitoyable.", "apparition": "Ignore les autres."},
        ],
        "citations": ["Paris est un bourbier."],
        "themes": ["ambition", "argent", "société"],
        "mouvement_litteraire": {
            "nom": "Réalisme",
            "epoque": "XIXe siècle",
            "description": "Représentation fidèle du réel.",
            "contexte_historique": "Monarchie de Juillet.",
        },
        "contexte_historique_oeuvre": "Monarchie de Juillet.",
        "fiche_auteur": {
            "nom": "Honoré de Balzac",
            "dates": "1799-1850",
            "biographie": "Romancier français.",
            "oeuvres_majeures": ["Le Père Goriot", "Eugénie Grandet"],
            "influences": ["Walter Scott"],
            "courant": "Réalisme",
        },
        "auteurs_lies": ["Gustave Flaubert", "Stendhal"],
        "avertissements": [],
    }


@pytest.fixture
def data_ch4(data_ch1):
    """Données Claude simulées — chapitre 4, même auteur."""
    d = dict(data_ch1)
    d["chapitre_ou_passage"] = "Chapitre 4 — Le sacrifice de Goriot"
    d["numero_chapitre"] = 4
    d["resume"] = "Goriot révèle son sacrifice pour ses filles."
    d["personnages"] = ["Rastignac", "Père Goriot", "Anastasie", "Delphine"]
    d["personnages_details"] = [
        {"nom": "Rastignac", "description": "Jeune provincial.", "apparition": "Écoute Goriot."},
        {"nom": "Père Goriot", "description": "Père sacrifié.", "apparition": "Révèle ses secrets."},
        {"nom": "Anastasie", "description": "Fille aînée.", "apparition": "Absente mais évoquée."},
        {"nom": "Delphine", "description": "Fille cadette.", "apparition": "Absente mais évoquée."},
    ]
    d["citations"] = ["Mes filles, c'est ma vie."]
    d["themes"] = ["amour_paternel", "sacrifice", "argent"]
    d["fiche_auteur"] = dict(data_ch1["fiche_auteur"])
    d["fiche_auteur"]["oeuvres_majeures"] = ["Le Père Goriot", "Eugénie Grandet", "César Birotteau"]
    d["auteurs_lies"] = ["Gustave Flaubert", "Stendhal", "Émile Zola"]
    return d
