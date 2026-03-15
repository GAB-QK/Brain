"""
Backend Obsidian — écrit des fichiers Markdown dans un vault Obsidian local.
Déplacement de vault_writer.py dans une classe ObsidianWriter(BaseWriter).
"""

import re
from pathlib import Path

from config import (
    TODAY,
    AUTEURS_DIR,
    MOUVEMENTS_DIR,
    PERSONNAGES_DIR,
    LIVRES_DIR,
    LITTERATURE,
    BIBLIOTHEQUE,
)
from markdown_builder import (
    build_chapter_md,
    build_auteur_md,
    build_mouvement_md,
    build_personnage_md,
    build_index_md,
    build_personnages_livre_md,
    build_themes_livre_md,
    build_citations_header,
    build_bibliotheque_header,
)
from writers.base_writer import BaseWriter


# ---------------------------------------------------------------------------
# Utilitaires (fonctions module-level, utilisables sans instancier la classe)
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


def _update_date_modification(path: Path) -> None:
    """Met à jour date_modification dans le frontmatter YAML du fichier."""
    content = path.read_text(encoding="utf-8")
    updated = re.sub(
        r"^(date_modification:\s*)\S+",
        rf"\g<1>{TODAY}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if updated != content:
        path.write_text(updated, encoding="utf-8")


# ---------------------------------------------------------------------------
# Backend Obsidian
# ---------------------------------------------------------------------------

class ObsidianWriter(BaseWriter):
    """Écrit toutes les fiches dans un vault Obsidian local (fichiers .md)."""

    # ── Chapitre ────────────────────────────────────────────────────────────

    def write_chapter(self, data: dict, ch_num: int) -> Path:
        """Écrit Livres/<Titre>/Chapitres/Ch_XX.md."""
        ch_dir = LIVRES_DIR / sanitize(data["titre"]) / "Chapitres"
        ch_dir.mkdir(parents=True, exist_ok=True)
        ch_file = ch_dir / f"Ch_{ch_num:02d}.md"
        ch_file.write_text(build_chapter_md(data, ch_num), encoding="utf-8")
        return ch_file

    # ── Index du livre ───────────────────────────────────────────────────────

    def update_index(self, data: dict, ch_num: int) -> Path:
        """Crée ou met à jour Livres/<Titre>/00_Index.md."""
        titre_safe = sanitize(data["titre"])
        mouvement  = data.get("mouvement_litteraire", {}).get("nom", "")
        index_path = LIVRES_DIR / titre_safe / "00_Index.md"
        chapitre   = data.get("chapitre_ou_passage", "")
        new_line   = f"- [[Ch_{ch_num:02d}]] — {chapitre}"

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
            _update_date_modification(index_path)

        return index_path

    # ── Personnages du livre ─────────────────────────────────────────────────

    def update_personnages(self, data: dict) -> Path:
        """Crée ou complète Livres/<Titre>/Personnages.md (append uniquement)."""
        path = LIVRES_DIR / sanitize(data["titre"]) / "Personnages.md"

        if not path.exists():
            path.write_text(
                build_personnages_livre_md(data["titre"], data["auteur"]),
                encoding="utf-8",
            )

        content  = path.read_text(encoding="utf-8")
        nouveaux = [p for p in data.get("personnages", []) if f"[[{p}]]" not in content]
        if nouveaux:
            new_content = content + "".join(f"- [[{p}]]\n" for p in nouveaux)
            path.write_text(new_content, encoding="utf-8")
            _update_date_modification(path)

        return path

    # ── Thèmes du livre ──────────────────────────────────────────────────────

    def update_themes(self, data: dict) -> Path:
        """Crée ou complète Livres/<Titre>/Themes.md (append uniquement)."""
        path = LIVRES_DIR / sanitize(data["titre"]) / "Themes.md"

        if not path.exists():
            path.write_text(
                build_themes_livre_md(data["titre"], data["auteur"]),
                encoding="utf-8",
            )

        content  = path.read_text(encoding="utf-8")
        # Vérifie la forme stockée (#theme_avec_underscores) pour éviter les doublons
        nouveaux = [t for t in data.get("themes", []) if f"#{'_'.join(t.split())}" not in content]
        if nouveaux:
            new_content = content + "".join(f"- #{'_'.join(t.split())}\n" for t in nouveaux)
            path.write_text(new_content, encoding="utf-8")
            _update_date_modification(path)

        return path

    # ── Citations ────────────────────────────────────────────────────────────

    def update_citations(self, data: dict, ch_num: int) -> Path:
        """Crée ou alimente Livres/<Titre>/Citations.md (append uniquement)."""
        titre_safe = sanitize(data["titre"])
        livre_dir  = LIVRES_DIR / titre_safe
        livre_dir.mkdir(parents=True, exist_ok=True)
        path      = livre_dir / "Citations.md"
        chapitre  = data.get("chapitre_ou_passage", f"Ch_{ch_num:02d}")
        citations = data.get("citations", [])

        if not path.exists():
            path.write_text(build_citations_header(data["titre"], data["auteur"]), encoding="utf-8")

        if citations:
            content   = path.read_text(encoding="utf-8")
            nouvelles = [c for c in citations if c not in content]
            if nouvelles:
                new_content = content + f"\n## {chapitre}\n\n" + "".join(f"> {c}\n\n" for c in nouvelles)
                path.write_text(new_content, encoding="utf-8")
                _update_date_modification(path)

        return path

    # ── Auteur ───────────────────────────────────────────────────────────────

    def write_auteur(self, data: dict) -> tuple[Path, bool]:
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

    # ── Mouvement ────────────────────────────────────────────────────────────

    def write_mouvement(self, data: dict) -> tuple[Path, bool]:
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

    # ── Personnages individuels ───────────────────────────────────────────────

    def write_personnages_individuels(self, data: dict, ch_num: int) -> list[tuple[Path, bool]]:
        """Crée ou met à jour Personnages/<Nom>.md avec liens inter-œuvres."""
        PERSONNAGES_DIR.mkdir(parents=True, exist_ok=True)
        titre  = data["titre"]
        auteur = data["auteur"]

        details_map: dict[str, dict] = {
            p["nom"]: p
            for p in data.get("personnages_details", [])
            if isinstance(p, dict) and "nom" in p
        }

        results = []
        for nom in data.get("personnages", []):
            path    = PERSONNAGES_DIR / f"{sanitize(nom)}.md"
            details = details_map.get(nom, {})
            if not path.exists():
                path.write_text(
                    build_personnage_md(
                        nom,
                        details.get("description", ""),
                        titre, auteur,
                        ch_num,
                        details.get("apparition", ""),
                    ),
                    encoding="utf-8",
                )
                results.append((path, True))
            else:
                self._update_personnage_existing(
                    path, titre, auteur,
                    f"Ch_{ch_num:02d}",
                    details.get("apparition", ""),
                )
                results.append((path, False))
        return results

    def _update_personnage_existing(
        self, path: Path, titre: str, auteur: str, ch_label: str, apparition: str,
    ) -> None:
        """Met à jour une fiche personnage existante avec un nouveau livre/chapitre."""
        content  = path.read_text(encoding="utf-8")
        modified = False
        _FM_SEP  = "\n---\n"

        # ── 1. Frontmatter : ajouter [[titre]] à oeuvres_liees ───────────────
        try:
            fm_close = content.index(_FM_SEP, 3)
        except ValueError:
            fm_close = -1

        if fm_close != -1:
            frontmatter = content[:fm_close]
            body        = content[fm_close + len(_FM_SEP):]
            wikilink    = f"[[{titre}]]"

            if wikilink not in frontmatter:
                entry = f'  - "{wikilink}"'
                if "oeuvres_liees:" in frontmatter:
                    new_fm = re.sub(
                        r'(oeuvres_liees:(?:\n  - "[^"]*")*)',
                        rf'\1\n{entry}',
                        frontmatter,
                        count=1,
                    )
                else:
                    new_fm = frontmatter.replace(
                        "\naliases: []",
                        f"\noeuvres_liees:\n{entry}\naliases: []",
                    )
                if new_fm != frontmatter:
                    content  = new_fm + _FM_SEP + body
                    modified = True

        # ── 2. Corps : section "Présent dans ces œuvres" ────────────────────
        ligne_oeuvre = f"- [[{titre}]] — [[{auteur}]]"
        if ligne_oeuvre not in content:
            section_hdr = "## Présent dans ces œuvres"
            if section_hdr in content:
                idx       = content.index(section_hdr) + len(section_hdr)
                end_match = re.search(r"\n---\n|\n## ", content[idx:])
                end       = idx + end_match.start() if end_match else len(content)
                sec       = content[idx:end]
                content   = content[:idx] + sec.rstrip("\n") + f"\n{ligne_oeuvre}\n" + content[end:]
                modified  = True

        # ── 3. Corps : section "Apparitions par œuvre" ──────────────────────
        ch_line     = f"- [[{ch_label}]] — {apparition}" if apparition else f"- [[{ch_label}]]"
        section_app = "## Apparitions par œuvre"
        subsection  = f"### [[{titre}]]"

        if section_app in content and ch_line not in content:
            app_idx = content.index(section_app)
            sub_idx = content.find(subsection, app_idx)
            if sub_idx == -1:
                # Nouvelle sous-section à la fin du fichier
                content  = content.rstrip("\n") + f"\n\n{subsection}\n\n{ch_line}\n"
                modified = True
            else:
                sub_start  = sub_idx + len(subsection)
                next_sub   = re.search(r"\n### ", content[sub_start:])
                sub_end    = sub_start + next_sub.start() if next_sub else len(content)
                sub_sec    = content[sub_start:sub_end]
                content    = (
                    content[:sub_start]
                    + sub_sec.rstrip("\n") + f"\n{ch_line}\n"
                    + content[sub_end:]
                )
                modified = True

        # ── 4. date_modification ─────────────────────────────────────────────
        if modified:
            content = re.sub(
                r"^(date_modification:\s*)\S+",
                rf"\g<1>{TODAY}",
                content, count=1, flags=re.MULTILINE,
            )
            path.write_text(content, encoding="utf-8")

    # ── Bibliothèque globale ─────────────────────────────────────────────────

    def update_bibliotheque(self, data: dict) -> Path:
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
            _update_date_modification(BIBLIOTHEQUE)

        return BIBLIOTHEQUE

    # ── Contexte existant ────────────────────────────────────────────────────

    def get_existing_context(self, titre: str) -> dict:
        """
        Lit les fichiers Obsidian existants pour le livre et retourne le contexte
        (personnages, thèmes, nombre de chapitres) à transmettre à Claude lors
        des imports suivants.
        """
        titre_safe  = sanitize(titre)
        livre_dir   = LIVRES_DIR / titre_safe
        ch_dir      = livre_dir / "Chapitres"
        perso_path  = livre_dir / "Personnages.md"
        themes_path = livre_dir / "Themes.md"

        # Nombre de chapitres déjà importés
        nb_chapitres = 0
        if ch_dir.exists():
            nb_chapitres = len([
                f for f in ch_dir.glob("Ch_*.md")
                if re.match(r"Ch_\d+", f.stem)
            ])

        # Personnages déjà enregistrés (extraits des wikilinks [[Nom]])
        personnages: list[str] = []
        if perso_path.exists():
            content = perso_path.read_text(encoding="utf-8")
            personnages = re.findall(r"\[\[([^\]]+)\]\]", content)

        # Thèmes déjà enregistrés (extraits des tags #theme_slug)
        themes: list[str] = []
        if themes_path.exists():
            content = themes_path.read_text(encoding="utf-8")
            slugs   = re.findall(r"#(\w+)", content)
            themes  = [s.replace("_", " ") for s in slugs]

        return {
            "personnages":  personnages,
            "themes":       themes,
            "nb_chapitres": nb_chapitres,
        }
