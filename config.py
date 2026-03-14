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
_vault_env = os.getenv("VAULT_PATH", "")
if not _vault_env:
    sys.exit("Erreur : VAULT_PATH non défini dans .env ou l'environnement.")

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
