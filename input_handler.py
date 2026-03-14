"""
Gestion des entrées — lit la note brute depuis différentes sources.
Stubs prêts pour les futures intégrations audio (Whisper) et image (Tesseract).
"""

import sys
from pathlib import Path


def collect_raw_note() -> str:
    """
    Retourne la note brute sous forme de chaîne.
    Sources supportées (par ordre de priorité) :
      1. Fichier texte passé en argument : python main.py note.txt
      2. Saisie stdin                    : python main.py  (puis Ctrl+D)
    """
    if len(sys.argv) > 1:
        return _from_file(Path(sys.argv[1]))
    return _from_stdin()


# ---------------------------------------------------------------------------
# Sources texte
# ---------------------------------------------------------------------------

def _from_file(path: Path) -> str:
    if not path.exists():
        sys.exit(f"Erreur : fichier introuvable → {path}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        sys.exit("Erreur : le fichier est vide. Abandon.")
    return content


def _from_stdin() -> str:
    print("Entrez votre note brute (terminez avec EOF : Ctrl+D / Ctrl+Z) :")
    content = sys.stdin.read()
    if not content.strip():
        sys.exit("Erreur : note vide. Abandon.")
    return content


# ---------------------------------------------------------------------------
# TODO: Whisper — transcription audio
# ---------------------------------------------------------------------------
# def _from_audio(path: Path) -> str:
#     """Transcrit un fichier audio en texte via OpenAI Whisper."""
#     import whisper
#     model  = whisper.load_model("base")
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
