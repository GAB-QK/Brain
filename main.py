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

import sys

# ── --help intercepté avant tout import projet ─────────────────────────────
# config.py appelle sys.exit si .env est incomplet ; on affiche le help avant.
if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    from input_handler import show_help
    show_help()
    sys.exit(0)

# ── Imports projet ──────────────────────────────────────────────────────────
from config import MODEL, VAULT_PATH, LIVRES_DIR
from input_handler import collect_raw_note
from claude_api import call_claude
from writers import get_writer, sanitize, next_chapter_number
from cli import preview_and_confirm, print_report

writer = get_writer()


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

    aut_path, aut_created = writer.write_auteur(data)
    mvt_path, mvt_created = writer.write_mouvement(data)

    results = {
        "chapter":           writer.write_chapter(data, ch_num),
        "index":             writer.update_index(data, ch_num),
        "personnages_livre": writer.update_personnages(data),
        "themes":            writer.update_themes(data),
        "citations":         writer.update_citations(data, ch_num),
        "bibliotheque":      writer.update_bibliotheque(data),
        "auteur":            aut_path,
        "auteur_created":    aut_created,
        "mouvement":         mvt_path,
        "mouvement_created": mvt_created,
        "personnages_ind":   writer.write_personnages_individuels(data),
    }

    print_report(data, ch_num, results)


if __name__ == "__main__":
    main()
