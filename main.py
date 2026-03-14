"""
Point d'entrée — orchestre le pipeline sans aucune logique métier.

Pipeline :
  collect_raw_note()      ← input_handler
       ↓
  call_claude()           ← claude_api
       ↓
  preview_and_confirm()   ← cli
       ↓
  write_* / update_*      ← vault_writer
       ↓
  print_report()          ← cli
"""

from config import MODEL, VAULT_PATH
from input_handler import collect_raw_note
from claude_api import call_claude
from vault_writer import (
    sanitize,
    next_chapter_number,
    write_chapter,
    update_index,
    update_personnages_livre,
    update_themes,
    update_citations,
    write_auteur,
    write_mouvement,
    write_personnages_individuels,
    update_bibliotheque,
    LIVRES_DIR,
)
from cli import preview_and_confirm, print_report


def main() -> None:
    print("📚 Carnet de lecture littéraire — génération de fiches Obsidian")
    print(f"   Modèle : {MODEL}")
    print(f"   Vault  : {VAULT_PATH}\n")

    raw_note = collect_raw_note()

    print("\n⏳ Envoi à Claude en cours…")
    data = call_claude(raw_note)
    print(f"✔  Œuvre détectée : « {data.get('titre', '?')} » de {data.get('auteur', '?')}")

    ch_dir = LIVRES_DIR / sanitize(data["titre"]) / "Chapitres"
    ch_num = next_chapter_number(ch_dir)

    if not preview_and_confirm(data, ch_num):
        print("Annulé.")
        return

    aut_path, aut_created = write_auteur(data)
    mvt_path, mvt_created = write_mouvement(data)

    results = {
        "chapter":          write_chapter(data, ch_num),
        "index":            update_index(data, ch_num),
        "personnages_livre": update_personnages_livre(data),
        "themes":           update_themes(data),
        "citations":        update_citations(data, ch_num),
        "bibliotheque":     update_bibliotheque(data),
        "auteur":           aut_path,
        "auteur_created":   aut_created,
        "mouvement":        mvt_path,
        "mouvement_created": mvt_created,
        "personnages_ind":  write_personnages_individuels(data),
    }

    print_report(data, ch_num, results)


if __name__ == "__main__":
    main()
