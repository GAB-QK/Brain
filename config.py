"""
Configuration globale — chargement .env, constantes MODEL et chemins du vault.
N'importe aucun autre module du projet (prévient les imports circulaires).
"""

import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Modèle Claude
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Vault Obsidian
# ---------------------------------------------------------------------------
def _env_required(name: str) -> str:
    """Retourne la valeur d'une variable d'environnement obligatoire."""
    value = os.getenv(name, "")
    if not value:
        print(f"❌ Erreur : {name} n'est pas défini dans le fichier .env ou l'environnement.")
        print()
        print("Utilise `python main.py --help` pour voir les options disponibles.")
        sys.exit(1)
    return value


_vault_env = _env_required("VAULT_PATH")
_          = _env_required("ANTHROPIC_API_KEY")   # vérifié ici ; utilisé par claude_api.py

VAULT_PATH      = Path(_vault_env)
LITTERATURE     = VAULT_PATH / "Littérature"
AUTEURS_DIR     = LITTERATURE / "Auteurs"
MOUVEMENTS_DIR  = LITTERATURE / "Mouvements"
PERSONNAGES_DIR = LITTERATURE / "Personnages"
LIVRES_DIR      = LITTERATURE / "Livres"
CITATIONS_DIR   = LITTERATURE / "Citations"
BIBLIOTHEQUE    = LITTERATURE / "00_Bibliotheque.md"

# ---------------------------------------------------------------------------
# Date du jour (utilisée dans les frontmatters)
# ---------------------------------------------------------------------------
TODAY = date.today().isoformat()
