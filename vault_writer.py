"""
Écriture dans le vault Obsidian — toutes les fonctions write_* et update_*.
Utilitaires : sanitize(), next_chapter_number().
"""

import re
from pathlib import Path

from config import (
    VAULT_PATH,
    AUTEURS_DIR,
    MOUVEMENTS_DIR,
    PERSONNAGES_DIR,
    LIVRES_DIR,
    CITATIONS_DIR,
    LITTERATURE,
    BIBLIOTHEQUE,
)
from markdown_builder import (
    build_chapter_md,
    build_auteur_md,
    build_mouvement_md,
    build_personnage_md,
    build_index_md,
    build_citations_header,
    build_bibliotheque_header,
)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def sanitize(text: str) -> str:
    """Retire les caractères interdits dans les noms de fichiers/dossiers."""
    return re.sub(r'[\\/:*?"<>|]', "", text).strip()


def next_chapter_number(chapitres_dir: Path) -> int:
    """Retourne le prochain numéro de chapitre disponible."""
    if not chapitres_dir.exists():
        return 1
    nums = [
        int(m.group(1))
        for f in chapitres_dir.glob("Ch_*.md")
        if (m := re.match(r"Ch_(\d+)", f.stem))
    ]
    return max(nums) + 1 if nums else 1


# ---------------------------------------------------------------------------
# Écriture des fichiers
# ---------------------------------------------------------------------------

def write_chapter(data: dict, ch_num: int) -> Path:
    """Écrit Livres/<Titre>/Chapitres/Ch_XX.md."""
    ch_dir = LIVRES_DIR / sanitize(data["titre"]) / "Chapitres"
    ch_dir.mkdir(parents=True, exist_ok=True)
    ch_file = ch_dir / f"Ch_{ch_num:02d}.md"
    ch_file.write_text(build_chapter_md(data, ch_num), encoding="utf-8")
    return ch_file


def update_index(data: dict, ch_num: int) -> Path:
    """Crée ou met à jour Livres/<Titre>/00_Index.md."""
    titre_safe  = sanitize(data["titre"])
    mouvement   = data.get("mouvement_litteraire", {}).get("nom", "")
    index_path  = LIVRES_DIR / titre_safe / "00_Index.md"
    chapitre    = data.get("chapitre_ou_passage", "")
    new_line    = f"- [[Ch_{ch_num:02d}]] — {chapitre}"

    if not index_path.exists():
        index_path.write_text(
            build_index_md(
                data["titre"], data["auteur"], mouvement,
                data.get("contexte_historique_oeuvre", ""),
            ),
            encoding="utf-8",
        )

    content = index_path.read_text(encoding="utf-8")
    if new_line not in content:
        content = content.replace("<!-- chapitres -->", f"<!-- chapitres -->\n{new_line}")
        index_path.write_text(content, encoding="utf-8")

    return index_path


def update_personnages_livre(data: dict) -> Path:
    """Crée ou complète Livres/<Titre>/Personnages.md (append uniquement)."""
    path = LIVRES_DIR / sanitize(data["titre"]) / "Personnages.md"

    if not path.exists():
        path.write_text(f"# Personnages — {data['titre']}\n\n", encoding="utf-8")

    existing = path.read_text(encoding="utf-8")
    nouveaux = [p for p in data.get("personnages", []) if f"[[{p}]]" not in existing]
    if nouveaux:
        with path.open("a", encoding="utf-8") as f:
            for p in nouveaux:
                f.write(f"- [[{p}]]\n")
    return path


def update_themes(data: dict) -> Path:
    """Crée ou complète Livres/<Titre>/Themes.md (append uniquement)."""
    path = LIVRES_DIR / sanitize(data["titre"]) / "Themes.md"

    if not path.exists():
        path.write_text(f"# Thèmes — {data['titre']}\n\n", encoding="utf-8")

    existing = path.read_text(encoding="utf-8")
    nouveaux = [t for t in data.get("themes", []) if t not in existing]
    if nouveaux:
        with path.open("a", encoding="utf-8") as f:
            for t in nouveaux:
                f.write(f"- #{'_'.join(t.split())}\n")
    return path


def update_citations(data: dict, ch_num: int) -> Path:
    """Crée ou alimente Citations/<Titre>_citations.md (append uniquement)."""
    titre_safe = sanitize(data["titre"])
    CITATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path      = CITATIONS_DIR / f"{titre_safe}_citations.md"
    chapitre  = data.get("chapitre_ou_passage", f"Ch_{ch_num:02d}")
    citations = data.get("citations", [])

    if not path.exists():
        path.write_text(build_citations_header(data["titre"], data["auteur"]), encoding="utf-8")

    if citations:
        existing  = path.read_text(encoding="utf-8")
        nouvelles = [c for c in citations if c not in existing]
        if nouvelles:
            with path.open("a", encoding="utf-8") as f:
                f.write(f"\n## {chapitre}\n\n")
                for c in nouvelles:
                    f.write(f"> {c}\n\n")
    return path


def write_auteur(data: dict) -> tuple[Path, bool]:
    """Crée Auteurs/<Nom>.md si absent. Retourne (path, créé)."""
    AUTEURS_DIR.mkdir(parents=True, exist_ok=True)
    fiche     = data.get("fiche_auteur", {})
    nom       = sanitize(fiche.get("nom", data["auteur"]))
    mouvement = data.get("mouvement_litteraire", {}).get("nom", "")
    path      = AUTEURS_DIR / f"{nom}.md"

    if path.exists():
        return path, False

    path.write_text(
        build_auteur_md(fiche, mouvement, data.get("auteurs_lies", [])),
        encoding="utf-8",
    )
    return path, True


def write_mouvement(data: dict) -> tuple[Path, bool]:
    """Crée Mouvements/<Nom>.md si absent. Retourne (path, créé)."""
    MOUVEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    mouvement = data.get("mouvement_litteraire", {})
    nom       = sanitize(mouvement.get("nom", "Inconnu"))
    path      = MOUVEMENTS_DIR / f"{nom}.md"

    if path.exists():
        return path, False

    path.write_text(
        build_mouvement_md(mouvement, data["auteur"], data.get("auteurs_lies", [])),
        encoding="utf-8",
    )
    return path, True


def write_personnages_individuels(data: dict) -> list[tuple[Path, bool]]:
    """Crée Personnages/<Nom>.md pour chaque personnage, si absent."""
    PERSONNAGES_DIR.mkdir(parents=True, exist_ok=True)
    titre  = data["titre"]
    auteur = data["auteur"]

    details_map: dict[str, str] = {
        p["nom"]: p.get("description", "")
        for p in data.get("personnages_details", [])
        if isinstance(p, dict) and "nom" in p
    }

    results = []
    for nom in data.get("personnages", []):
        path = PERSONNAGES_DIR / f"{sanitize(nom)}.md"
        if path.exists():
            results.append((path, False))
            continue
        path.write_text(
            build_personnage_md(nom, details_map.get(nom, ""), titre, auteur),
            encoding="utf-8",
        )
        results.append((path, True))
    return results


def update_bibliotheque(data: dict) -> Path:
    """Crée ou met à jour Littérature/00_Bibliotheque.md (append uniquement)."""
    LITTERATURE.mkdir(parents=True, exist_ok=True)
    titre_safe = sanitize(data["titre"])
    new_line   = f"- [[{titre_safe}]] — [[{data['auteur']}]]"

    if not BIBLIOTHEQUE.exists():
        BIBLIOTHEQUE.write_text(build_bibliotheque_header(), encoding="utf-8")

    content = BIBLIOTHEQUE.read_text(encoding="utf-8")
    if new_line not in content:
        content = content.replace("<!-- livres -->", f"<!-- livres -->\n{new_line}")
        BIBLIOTHEQUE.write_text(content, encoding="utf-8")

    return BIBLIOTHEQUE
