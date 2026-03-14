"""
Constructeurs Markdown — toutes les fonctions build_* et l'utilitaire fm().
Aucune écriture disque ici : retourne uniquement des chaînes.

Format Obsidian Properties / Dataview :
  - Tags hiérarchiques sans # (type/, theme/, mouvement/, statut/)
  - Wikilinks toujours entre guillemets doubles
  - Dates YYYY-MM-DD non quotées
  - aliases: [] toujours présent
  - Pas de YAML imbriqué
"""

import re

from config import TODAY


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _slug(s: str) -> str:
    """Convertit une chaîne en slug pour tags hiérarchiques (minuscules, espaces→_)."""
    return re.sub(r"\s+", "_", s.strip().lower()) if s else "inconnu"


def _yaml_scalar(value: str) -> str:
    """Date YYYY-MM-DD → non quotée ; tout le reste → entre guillemets doubles."""
    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return value
    return f'"{value}"'


# ---------------------------------------------------------------------------
# Utilitaire frontmatter
# ---------------------------------------------------------------------------

def fm(tags: list, **kwargs) -> str:
    """
    Génère un bloc frontmatter YAML compatible Obsidian Properties et Dataview.

    Conventions :
    - tags     : liste de tags hiérarchiques sans #  ex. ["type/chapitre", "theme/amour"]
    - aliases  : toujours présent, vide par défaut   ex. aliases=["alias1"]
    - Wikilinks dans les valeurs scalaires → détectés et encadrés de guillemets
    - Dates YYYY-MM-DD → non quotées
    - Listes → YAML block list ; items wikilink entre guillemets
    """
    lines = ["---"]

    # 1. Tags — bloc YAML, jamais de #
    lines.append("tags:")
    for tag in tags:
        lines.append(f"  - {tag}")

    # 2. aliases — toujours présent
    aliases = kwargs.pop("aliases", [])
    if aliases:
        lines.append("aliases:")
        for a in aliases:
            lines.append(f'  - "{a}"')
    else:
        lines.append("aliases: []")

    # 3. Autres propriétés
    for key, value in kwargs.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    s = str(item)
                    lines.append(f'  - "{s}"' if "[[" in s else f"  - {s}")
        else:
            lines.append(f"{key}: {_yaml_scalar(str(value))}")

    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fiche chapitre
# ---------------------------------------------------------------------------

def build_chapter_md(data: dict, ch_num: int) -> str:
    auteur      = data["auteur"]
    titre       = data["titre"]
    chapitre    = data.get("chapitre_ou_passage", "")
    resume      = data.get("resume", "")
    personnages = data.get("personnages", [])
    themes      = data.get("themes", [])
    mouvement   = data.get("mouvement_litteraire", {})
    contexte    = data.get("contexte_historique_oeuvre", "")
    mvt_nom     = mouvement.get("nom", "")
    ch_label    = f"Ch_{ch_num:02d}"

    tags = (
        ["type/chapitre", "type/lecture"]
        + [f"theme/{_slug(t)}" for t in themes]
        + ([f"mouvement/{_slug(mvt_nom)}"] if mvt_nom else [])
        + ["statut/importé"]
    )

    header = fm(
        tags,
        titre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        mouvement=f"[[{mvt_nom}]]" if mvt_nom else "",
        chapitre=chapitre,
        date_creation=TODAY,
        date_modification=TODAY,
    )

    theme_tags  = " ".join(f"#{'_'.join(t.split())}" for t in themes)
    perso_links = "\n".join(f"- [[{p}]]" for p in personnages) or "_Aucun personnage identifié._"

    return "\n".join([
        header, "",
        f"# {ch_label} — {chapitre}", "",
        f"**Livre :** [[{titre}]]",
        f"**Auteur :** [[{auteur}]]",
        f"**Mouvement :** [[{mvt_nom}]]", "",
        "---", "",
        "## 📖 Résumé", "",
        resume, "",
        "---", "",
        "## 👤 Personnages présents", "",
        perso_links, "",
        "---", "",
        "## 🏷️ Thèmes", "",
        theme_tags, "",
        "---", "",
        "## 🏛️ Contexte historique de l'œuvre", "",
        contexte, "",
        "---", "",
        "## 🔗 Voir aussi", "",
        f"- [[00_Index]] — Index de *{titre}*",
        f"- [[Personnages]] — Tous les personnages",
        f"- [[Themes]] — Tous les thèmes",
        f"- [[{titre}_citations]] — Toutes les citations",
        "",
    ])


# ---------------------------------------------------------------------------
# Fiche auteur
# ---------------------------------------------------------------------------

def build_auteur_md(fiche: dict, mouvement_nom: str, auteurs_lies: list) -> str:
    nom        = fiche.get("nom", "")
    dates      = fiche.get("dates", "")
    bio        = fiche.get("biographie", "")
    oeuvres    = fiche.get("oeuvres_majeures", [])
    influences = fiche.get("influences", [])

    tags = [
        "type/auteur",
        *(([f"mouvement/{_slug(mouvement_nom)}"] if mouvement_nom else [])),
        "statut/importé",
    ]

    header = fm(
        tags,
        nom=nom,
        dates=dates,
        mouvement=f"[[{mouvement_nom}]]" if mouvement_nom else "",
        auteurs_lies=[f"[[{a}]]" for a in auteurs_lies],
        date_creation=TODAY,
        date_modification=TODAY,
    )

    oeuvres_md    = "\n".join(f"- {o}" for o in oeuvres)    or "_Non renseigné._"
    influences_md = "\n".join(f"- {i}" for i in influences) or "_Non renseigné._"
    lies_md       = "\n".join(f"- [[{a}]]" for a in auteurs_lies) or "_Aucun._"

    return "\n".join([
        header, "",
        f"# {nom}", "",
        f"**Dates :** {dates}",
        f"**Courant :** [[{mouvement_nom}]]", "",
        "---", "",
        "## Biographie", "",
        bio, "",
        "---", "",
        "## Œuvres majeures", "",
        oeuvres_md, "",
        "---", "",
        "## Influences", "",
        influences_md, "",
        "---", "",
        "## Auteurs du même mouvement", "",
        lies_md, "",
    ])


# ---------------------------------------------------------------------------
# Fiche mouvement
# ---------------------------------------------------------------------------

def build_mouvement_md(mouvement: dict, auteur: str, auteurs_lies: list) -> str:
    nom      = mouvement.get("nom", "")
    epoque   = mouvement.get("epoque", "")
    desc     = mouvement.get("description", "")
    contexte = mouvement.get("contexte_historique", "")

    tous_auteurs = [auteur] + auteurs_lies

    header = fm(
        ["type/mouvement", "statut/importé"],
        nom=nom,
        epoque=epoque,
        auteurs=[f"[[{a}]]" for a in tous_auteurs],
        date_creation=TODAY,
        date_modification=TODAY,
    )

    lies_md = "\n".join(f"- [[{a}]]" for a in tous_auteurs) or "_Aucun._"

    return "\n".join([
        header, "",
        f"# {nom}", "",
        f"**Époque :** {epoque}", "",
        desc, "",
        "---", "",
        "## Contexte historique", "",
        contexte, "",
        "---", "",
        "## Auteurs représentatifs", "",
        lies_md, "",
    ])


# ---------------------------------------------------------------------------
# Fiche personnage individuel
# ---------------------------------------------------------------------------

def build_personnage_md(nom: str, description: str, titre: str, auteur: str) -> str:
    header = fm(
        ["type/personnage", "statut/importé"],
        nom=nom,
        livre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
        date_modification=TODAY,
    )

    return "\n".join([
        header, "",
        f"# {nom}", "",
        f"**Livre :** [[{titre}]]",
        f"**Auteur :** [[{auteur}]]", "",
        "---", "",
        "## Description", "",
        description, "",
    ])


# ---------------------------------------------------------------------------
# Index du livre (00_Index.md)
# ---------------------------------------------------------------------------

def build_index_md(titre: str, auteur: str, mouvement_nom: str, contexte: str) -> str:
    tags = [
        "type/livre",
        *(([f"mouvement/{_slug(mouvement_nom)}"] if mouvement_nom else [])),
        "statut/importé",
    ]

    header = fm(
        tags,
        titre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        mouvement=f"[[{mouvement_nom}]]" if mouvement_nom else "",
        date_creation=TODAY,
        date_modification=TODAY,
    )

    return "\n".join([
        header, "",
        f"# {titre}", "",
        f"**Auteur :** [[{auteur}]]",
        f"**Mouvement :** [[{mouvement_nom}]]", "",
        "---", "",
        "## Contexte historique de l'œuvre", "",
        contexte, "",
        "---", "",
        "## Chapitres", "",
        "<!-- chapitres -->", "",
        "---", "",
        "## Liens", "",
        f"- [[Personnages]]",
        f"- [[Themes]]",
        f"- [[{titre}_citations]]",
        "",
    ])


# ---------------------------------------------------------------------------
# En-têtes des fichiers Personnages.md et Themes.md par livre
# ---------------------------------------------------------------------------

def build_personnages_livre_md(titre: str, auteur: str) -> str:
    header = fm(
        ["type/personnages-livre", "statut/importé"],
        titre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
        date_modification=TODAY,
    )
    return f"{header}\n\n# Personnages — {titre}\n\n"


def build_themes_livre_md(titre: str, auteur: str) -> str:
    header = fm(
        ["type/themes-livre", "statut/importé"],
        titre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
        date_modification=TODAY,
    )
    return f"{header}\n\n# Thèmes — {titre}\n\n"


# ---------------------------------------------------------------------------
# En-têtes des fichiers Citations et Bibliothèque
# ---------------------------------------------------------------------------

def build_citations_header(titre: str, auteur: str) -> str:
    header = fm(
        ["type/citations", "statut/importé"],
        titre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
        date_modification=TODAY,
    )
    return f"{header}\n\n# Citations — {titre}\n\n"


def build_bibliotheque_header() -> str:
    header = fm(
        ["type/bibliotheque", "statut/importé"],
        date_creation=TODAY,
        date_modification=TODAY,
    )
    return f"{header}\n\n# 📚 Bibliothèque\n\n<!-- livres -->\n"
