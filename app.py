"""
Serveur Flask — interface web par-dessus les modules Python existants.
Lance avec : python app.py  (accessible sur http://0.0.0.0:5000)
"""

import traceback
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from config import (
    VAULT_PATH,
    LIVRES_DIR,
    AUTEURS_DIR,
    MOUVEMENTS_DIR,
    PERSONNAGES_DIR,
)
from claude_api import call_claude
from writers import get_writer, sanitize, next_chapter_number

writer = get_writer()

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _preview_files(data: dict, ch_num: int) -> list[dict]:
    """Construit la liste prévisionnelle des fichiers avant toute écriture."""
    titre_safe  = sanitize(data["titre"])
    auteur_safe = sanitize(data.get("fiche_auteur", {}).get("nom", data.get("auteur", "")))
    mvt_safe    = sanitize(data.get("mouvement_litteraire", {}).get("nom", ""))
    ch_label    = f"Ch_{ch_num:02d}"

    files = [
        {"path": f"Livres/{titre_safe}/Chapitres/{ch_label}.md", "status": "new"},
        {"path": f"Livres/{titre_safe}/00_Index.md",              "status": "update"},
        {"path": f"Livres/{titre_safe}/Personnages.md",           "status": "update"},
        {"path": f"Livres/{titre_safe}/Themes.md",                "status": "update"},
        {"path": f"Citations/{titre_safe}_citations.md",          "status": "update"},
        {"path": "00_Bibliotheque.md",                            "status": "update"},
        {
            "path":   f"Auteurs/{auteur_safe}.md",
            "status": "new" if not (AUTEURS_DIR / f"{auteur_safe}.md").exists() else "existing",
        },
    ]
    if mvt_safe:
        files.append({
            "path":   f"Mouvements/{mvt_safe}.md",
            "status": "new" if not (MOUVEMENTS_DIR / f"{mvt_safe}.md").exists() else "existing",
        })
    for p in data.get("personnages", []):
        p_safe = sanitize(p)
        files.append({
            "path":   f"Personnages/{p_safe}.md",
            "status": "new" if not (PERSONNAGES_DIR / f"{p_safe}.md").exists() else "existing",
        })
    return files


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    payload  = request.get_json(silent=True) or {}
    raw_note = payload.get("note", "").strip()
    if not raw_note:
        return jsonify({"error": "La note est vide."}), 400

    try:
        data    = call_claude(raw_note)
        ch_dir  = LIVRES_DIR / sanitize(data["titre"]) / "Chapitres"
        ch_num  = next_chapter_number(ch_dir)
        preview = _preview_files(data, ch_num)
        return jsonify({"data": data, "ch_num": ch_num, "preview_files": preview})
    except SystemExit as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": str(exc), "detail": traceback.format_exc()}), 500


@app.route("/import", methods=["POST"])
def import_vault():
    payload = request.get_json(silent=True) or {}
    data    = payload.get("data")
    ch_num  = payload.get("ch_num")
    if not data or ch_num is None:
        return jsonify({"error": "Données manquantes."}), 400

    try:
        ch_path                        = writer.write_chapter(data, ch_num)
        idx_path                       = writer.update_index(data, ch_num)
        perso_livre_path               = writer.update_personnages(data)
        themes_path                    = writer.update_themes(data)
        cit_path                       = writer.update_citations(data, ch_num)
        auteur_path, auteur_created    = writer.write_auteur(data)
        mvt_path,    mvt_created       = writer.write_mouvement(data)
        perso_ind                      = writer.write_personnages_individuels(data)
        bib_path                       = writer.update_bibliotheque(data)

        def rel(p: Path) -> str:
            return str(p.relative_to(VAULT_PATH))

        def st(created: bool) -> str:
            return "created" if created else "existing"

        files = [
            {"path": rel(ch_path),         "status": "created"},
            {"path": rel(idx_path),         "status": "updated"},
            {"path": rel(perso_livre_path), "status": "updated"},
            {"path": rel(themes_path),      "status": "updated"},
            {"path": rel(cit_path),         "status": "updated"},
            {"path": rel(bib_path),         "status": "updated"},
            {"path": rel(auteur_path),      "status": st(auteur_created)},
            {"path": rel(mvt_path),         "status": st(mvt_created)},
        ]
        for path, created in perso_ind:
            files.append({"path": rel(path), "status": st(created)})

        return jsonify({"files": files})
    except Exception as exc:
        return jsonify({"error": str(exc), "detail": traceback.format_exc()}), 500


@app.route("/status")
def vault_status():
    books = []
    if LIVRES_DIR.exists():
        for d in sorted(LIVRES_DIR.iterdir()):
            if d.is_dir():
                ch_dir = d / "Chapitres"
                count  = len(list(ch_dir.glob("Ch_*.md"))) if ch_dir.exists() else 0
                books.append({"titre": d.name, "chapitres": count})
    return jsonify({"books": books})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
