"""
Factory pour le backend d'écriture.
Sélectionne ObsidianWriter ou NotionWriter selon WRITER_BACKEND dans .env.
Exporte aussi les utilitaires sanitize() et next_chapter_number() pour
une utilisation directe dans app.py, main.py et cli.py.
"""

from config import WRITER_BACKEND
from writers.obsidian_writer import sanitize, next_chapter_number


def get_writer():
    """Retourne une instance du backend d'écriture configuré."""
    if WRITER_BACKEND == "notion":
        from writers.notion_writer import NotionWriter
        return NotionWriter()
    from writers.obsidian_writer import ObsidianWriter
    return ObsidianWriter()


__all__ = ["get_writer", "sanitize", "next_chapter_number"]
