"""
Constructeurs Markdown — toutes les fonctions build_* et l'utilitaire fm().
Aucune écriture disque ici : retourne uniquement des chaînes.
"""

from config import TODAY


# ---------------------------------------------------------------------------
# Utilitaire frontmatter
# ---------------------------------------------------------------------------

def fm(tags: list, **kwargs) -> str:
    """Génère un bloc frontmatter YAML Obsidian."""
    tag_str = ", ".join(tags)
    lines   = ["---", f"tags: [{tag_str}]"]
    for key, value in kwargs.items():
        lines.append(f'{key}: "{value}"')
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

    theme_tags  = " ".join(f"#{'_'.join(t.split())}" for t in themes)
    perso_links = "\n".join(f"- [[{p}]]" for p in personnages) or "_Aucun personnage identifié._"

    header = fm(
        ["lecture", "chapitre"] + [t.replace(" ", "_") for t in themes],
        auteur=f"[[{auteur}]]",
        titre=f"[[{titre}]]",
        mouvement=f"[[{mvt_nom}]]",
        date_import=TODAY,
    )

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

    oeuvres_md    = "\n".join(f"- {o}" for o in oeuvres)    or "_Non renseigné._"
    influences_md = "\n".join(f"- {i}" for i in influences) or "_Non renseigné._"
    lies_md       = "\n".join(f"- [[{a}]]" for a in auteurs_lies) or "_Aucun._"

    header = fm(
        ["auteur"],
        dates=dates,
        mouvement=f"[[{mouvement_nom}]]",
        date_creation=TODAY,
    )

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
    lies_md  = "\n".join(f"- [[{a}]]" for a in [auteur] + auteurs_lies) or "_Aucun._"

    header = fm(
        ["mouvement"],
        epoque=epoque,
        date_creation=TODAY,
    )

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
        ["personnage"],
        livre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
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
# Index du livre
# ---------------------------------------------------------------------------

def build_index_md(titre: str, auteur: str, mouvement_nom: str, contexte: str) -> str:
    header = fm(
        ["livre"],
        auteur=f"[[{auteur}]]",
        mouvement=f"[[{mouvement_nom}]]",
        date_creation=TODAY,
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
# En-têtes des fichiers append
# ---------------------------------------------------------------------------

def build_citations_header(titre: str, auteur: str) -> str:
    header = fm(
        ["citations"],
        livre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
    )
    return f"{header}\n\n# Citations — {titre}\n\n"


def build_bibliotheque_header() -> str:
    header = fm(["bibliotheque"], date_creation=TODAY)
    return f"{header}\n\n# 📚 Bibliothèque\n\n<!-- livres -->\n"
