"""
Serveur Flask — interface web par-dessus les modules Python existants.
Lance avec : python app.py  (accessible sur http://0.0.0.0:5000)
"""

import os
import re
import traceback
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

from config import (
    VAULT_PATH,
    LIVRES_DIR,
    AUTEURS_DIR,
    MOUVEMENTS_DIR,
    PERSONNAGES_DIR,
)
from claude_api import call_claude, extract_title
from writers import get_writer, sanitize, next_chapter_number

writer = get_writer()

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update_env_file(updates: dict) -> None:
    """Met à jour les clés dans .env sans écraser les lignes non modifiées."""
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated_keys = set()
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)
    # Ajouter les clés absentes du fichier
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _normalize_notion_id(value: str) -> str:
    """
    Extrait et normalise un UUID Notion depuis n'importe quel format :
    - UUID brut : 324d70bff8508013977fc45728a591e1
    - URL Notion : notion.so/Carnet-de-lecture-324d70bff8508013977fc45728a591e1
    - UUID avec tirets déjà présents : 324d70bf-f850-8013-977f-c45728a591e1
    """
    clean = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(clean) == 32:
        return f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"
    return value


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
        {"path": f"Livres/{titre_safe}/Citations.md",             "status": "update"},
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
        # Passe 1 — extraction du titre (silencieuse)
        title_data = extract_title(raw_note)
        titre      = title_data.get("titre", "")

        # Récupération du contexte existant
        context: dict = {}
        if titre:
            try:
                context = writer.get_existing_context(titre)
            except Exception:
                pass  # continuer sans contexte

        # Passe 2 — appel complet avec contexte
        data    = call_claude(raw_note, context=context)
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
        perso_ind                      = writer.write_personnages_individuels(data, ch_num)
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


@app.route("/settings")
def settings():
    current = {
        "WRITER_BACKEND":      os.getenv("WRITER_BACKEND", "obsidian"),
        "VAULT_PATH":          os.getenv("VAULT_PATH", ""),
        "ANTHROPIC_API_KEY":   os.getenv("ANTHROPIC_API_KEY", ""),
        "NOTION_TOKEN":        os.getenv("NOTION_TOKEN", ""),
        "NOTION_ROOT_PAGE_ID": os.getenv("NOTION_ROOT_PAGE_ID", ""),
    }
    return render_template("settings.html", current=current)


@app.route("/settings/save", methods=["POST"])
def settings_save():
    global writer
    payload = request.get_json(silent=True) or {}
    allowed_keys = {"WRITER_BACKEND", "VAULT_PATH", "ANTHROPIC_API_KEY",
                    "NOTION_TOKEN", "NOTION_ROOT_PAGE_ID"}
    updates = {k: v for k, v in payload.items() if k in allowed_keys}
    if "NOTION_ROOT_PAGE_ID" in updates:
        updates["NOTION_ROOT_PAGE_ID"] = _normalize_notion_id(updates["NOTION_ROOT_PAGE_ID"])
    try:
        _update_env_file(updates)
        load_dotenv(override=True)
        # Réinstancier le writer selon le nouveau backend
        new_backend = updates.get("WRITER_BACKEND", os.getenv("WRITER_BACKEND", "obsidian"))
        if new_backend == "notion":
            from writers.notion_writer import NotionWriter
            writer = NotionWriter()
        else:
            from writers.obsidian_writer import ObsidianWriter
            writer = ObsidianWriter()
        return jsonify({"ok": True, "NOTION_ROOT_PAGE_ID": updates.get("NOTION_ROOT_PAGE_ID", "")})
    except Exception as exc:
        return jsonify({"error": str(exc), "detail": traceback.format_exc()}), 500


@app.route("/config")
def config():
    return jsonify({"backend": os.getenv("WRITER_BACKEND", "obsidian")})


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
