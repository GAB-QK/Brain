"""
Gestion des entrées — --help, validation des arguments, lecture de la note brute.
Stubs prêts pour les futures intégrations audio (Whisper) et image (Tesseract).
"""

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Extensions supportées
# ---------------------------------------------------------------------------

_EXT_TEXT  = {".txt"}
_EXT_AUDIO = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
_EXT_IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".tiff"}


# ---------------------------------------------------------------------------
# Aide
# ---------------------------------------------------------------------------

def show_help() -> None:
    """Affiche le message d'aide complet (sans appeler sys.exit)."""
    print("""\
📚 Carnet de lecture littéraire — génération de fiches Obsidian

Usage :
  python main.py                  Saisie interactive (stdin)
  python main.py <fichier.txt>    Depuis un fichier texte

Arguments :
  <fichier.txt>   Chemin vers un fichier texte contenant la note brute

Options :
  -h, --help      Affiche ce message et quitte

Formats supportés :
  ✅  .txt         Fichier texte brut
  🔜  .mp3 .wav .m4a .ogg .flac   Audio (Whisper, à venir)
  🔜  .jpg .png .webp .tiff       Image/scan (Tesseract, à venir)

Exemples :
  python main.py
  python main.py notes/chapitre3.txt

Configuration (.env) :
  ANTHROPIC_API_KEY   Clé API Anthropic (obligatoire)
  VAULT_PATH          Chemin absolu vers le vault Obsidian (obligatoire)
  WHISPER_MODEL       Modèle Whisper à venir (défaut : base)

Vault Obsidian :
  Les fiches sont générées sous VAULT_PATH/Littérature/
  Voir README.md pour l'architecture complète.\
""")


# ---------------------------------------------------------------------------
# Utilitaire erreur
# ---------------------------------------------------------------------------

def _err(msg: str) -> None:
    """Affiche une erreur formatée et quitte avec le code 1."""
    print(f"❌ Erreur : {msg}")
    print()
    print("Utilise `python main.py --help` pour voir les options disponibles.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Validation + collecte
# ---------------------------------------------------------------------------

def collect_raw_note() -> str:
    """
    Valide les arguments, puis retourne la note brute sous forme de chaîne.
    Sources supportées (par ordre de priorité) :
      1. Fichier texte passé en argument : python main.py note.txt
      2. Saisie stdin                    : python main.py  (puis Ctrl+D)
    """
    args = sys.argv[1:]

    if len(args) > 1:
        _err(f"trop d'arguments ({len(args)} fournis, 1 attendu au maximum).")

    if len(args) == 1:
        path = Path(args[0])
        ext  = path.suffix.lower()

        if ext in _EXT_AUDIO:
            _err(
                f"le format audio ({ext}) n'est pas encore supporté.\n"
                "  L'intégration Whisper est prévue dans une prochaine version."
            )
        if ext in _EXT_IMAGE:
            _err(
                f"le format image ({ext}) n'est pas encore supporté.\n"
                "  L'intégration Tesseract OCR est prévue dans une prochaine version."
            )
        if ext not in _EXT_TEXT:
            _err(
                f"extension non reconnue : '{ext}'.\n"
                f"  Formats acceptés : {', '.join(sorted(_EXT_TEXT))} "
                f"(audio et image à venir)."
            )
        if not path.exists():
            _err(f"fichier introuvable : {path}")

        return _from_file(path)

    return _from_stdin()


# ---------------------------------------------------------------------------
# Sources texte
# ---------------------------------------------------------------------------

def _from_file(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        _err(f"le fichier est vide : {path}")
    return content


def _from_stdin() -> str:
    print("Entrez votre note brute (terminez avec EOF : Ctrl+D / Ctrl+Z) :")
    content = sys.stdin.read()
    if not content.strip():
        _err("note vide. Abandon.")
    return content


# ---------------------------------------------------------------------------
# TODO: Whisper — transcription audio
# ---------------------------------------------------------------------------
# def _from_audio(path: Path) -> str:
#     """Transcrit un fichier audio en texte via OpenAI Whisper."""
#     import os
#     import whisper
#     model  = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
#     result = model.transcribe(str(path))
#     return result["text"]


# ---------------------------------------------------------------------------
# TODO: Tesseract — extraction OCR depuis image
# ---------------------------------------------------------------------------
# def _from_image(path: Path) -> str:
#     """Extrait le texte d'une image ou d'un scan via Tesseract OCR."""
#     import pytesseract
#     from PIL import Image
#     return pytesseract.image_to_string(Image.open(path), lang="fra")
