#!/usr/bin/env python3
"""
Carnet de lecture littéraire — génère des fiches Markdown Obsidian structurées
via l'API Claude (claude-sonnet-4-20250514).

Architecture du vault (sous VAULT_PATH/Littérature/) :
  00_Bibliotheque.md               ← index global (append)
  Auteurs/<Prénom Nom>.md          ← fiche auteur (créée une fois, jamais écrasée)
  Mouvements/<Mouvement>.md        ← fiche mouvement (créée une fois, jamais écrasée)
  Personnages/<Nom>.md             ← fiche personnage (créée une fois, jamais écrasée)
  Livres/<Titre>/
      00_Index.md                  ← mis à jour à chaque chapitre
      Personnages.md               ← append
      Themes.md                    ← append
      Chapitres/Ch_XX.md           ← créé à chaque import
  Citations/<Titre>_citations.md   ← append
"""

import json
import os
import re
import sys
import textwrap
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

MODEL = "claude-sonnet-4-20250514"

_vault_env = os.getenv("VAULT_PATH", "")
if not _vault_env:
    sys.exit("Erreur : VAULT_PATH non défini dans .env ou l'environnement.")
VAULT_PATH = Path(_vault_env)

LITTERATURE     = VAULT_PATH / "Littérature"
AUTEURS_DIR     = LITTERATURE / "Auteurs"
MOUVEMENTS_DIR  = LITTERATURE / "Mouvements"
PERSONNAGES_DIR = LITTERATURE / "Personnages"
LIVRES_DIR      = LITTERATURE / "Livres"
CITATIONS_DIR   = LITTERATURE / "Citations"
BIBLIOTHEQUE    = LITTERATURE / "00_Bibliotheque.md"

TODAY = date.today().isoformat()

SYSTEM_PROMPT = textwrap.dedent("""\
    Tu es un assistant spécialisé en analyse littéraire.
    À partir d'une note brute sur une lecture (extrait, résumé de chapitre,
    impressions), tu dois produire UNIQUEMENT un objet JSON valide (sans texte
    avant ni après) respectant exactement le schéma suivant :

    {
      "auteur": "Prénom Nom de l'auteur",
      "titre": "Titre complet de l'œuvre",
      "chapitre_ou_passage": "Ex : Partie I, Chapitre 3 — ou une courte description",
      "resume": "Résumé du chapitre ou du passage (3-8 phrases)",
      "personnages": ["Personnage 1", "Personnage 2"],
      "personnages_details": [
        {"nom": "Personnage 1", "description": "Description courte du personnage (1-2 phrases)"},
        {"nom": "Personnage 2", "description": "Description courte du personnage (1-2 phrases)"}
      ],
      "citations": ["Citation textuelle 1", "Citation textuelle 2"],
      "themes": ["theme1", "theme2", "theme3"],
      "mouvement_litteraire": {
        "nom": "Nom du mouvement",
        "epoque": "Ex : XIXe siècle, 1830-1880",
        "description": "Description du mouvement (2-3 phrases)",
        "contexte_historique": "Époque et contexte historique du mouvement (2-3 phrases)"
      },
      "contexte_historique_oeuvre": "Époque, événements contemporains à l'écriture (3-5 phrases)",
      "fiche_auteur": {
        "nom": "Prénom Nom",
        "dates": "AAAA-AAAA",
        "biographie": "Courte biographie (3-5 phrases)",
        "oeuvres_majeures": ["Titre 1", "Titre 2", "Titre 3"],
        "influences": ["Auteur ou courant influent 1", "Auteur influent 2"],
        "courant": "Nom du mouvement littéraire auquel il appartient"
      },
      "auteurs_lies": ["Auteur du même mouvement 1", "Auteur lié 2"]
    }

    Règles impératives :
    - Réponds UNIQUEMENT avec le JSON, sans balises de code, sans prose.
    - Si une information est inconnue ou non mentionnée dans la note,
      infère-la à partir de tes connaissances littéraires.
    - Les champs sont toujours présents, même si vides ([]).
    - personnages_details doit contenir une entrée pour chaque élément de personnages.
    - Les citations doivent être des phrases réelles tirées de l'œuvre, ou,
      à défaut, des phrases représentatives du style de l'auteur.
""")


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def sanitize(text: str) -> str:
    """Retire les caractères interdits dans les noms de fichiers/dossiers."""
    return re.sub(r'[\\/:*?"<>|]', "", text).strip()


def fm(tags: list, **kwargs) -> str:
    """Génère un bloc frontmatter YAML."""
    lines = ["---"]
    tag_str = ", ".join(tags)
    lines.append(f"tags: [{tag_str}]")
    for key, value in kwargs.items():
        lines.append(f'{key}: "{value}"')
    lines.append("---")
    return "\n".join(lines)


def collect_raw_note() -> str:
    """Lit la note brute depuis un fichier (argv[1]) ou stdin."""
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            sys.exit(f"Erreur : fichier introuvable → {path}")
        return path.read_text(encoding="utf-8")
    print("Entrez votre note brute (terminez avec EOF : Ctrl+D / Ctrl+Z) :")
    content = sys.stdin.read()
    if not content.strip():
        sys.exit("Erreur : note vide. Abandon.")
    return content


def call_claude(raw_note: str) -> dict:
    """Envoie la note à Claude et retourne le JSON parsé."""
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": "Voici ma note de lecture brute. Génère la fiche JSON :\n\n" + raw_note,
            }],
        )
    except anthropic.AuthenticationError:
        sys.exit("Erreur d'authentification : vérifiez votre ANTHROPIC_API_KEY.")
    except anthropic.BadRequestError as exc:
        sys.exit(f"Requête invalide : {exc.message}")
    except anthropic.RateLimitError:
        sys.exit("Limite de débit atteinte. Réessayez dans quelques instants.")
    except anthropic.APIConnectionError:
        sys.exit("Impossible de contacter l'API Anthropic. Vérifiez votre connexion.")
    except anthropic.APIStatusError as exc:
        sys.exit(f"Erreur API ({exc.status_code}) : {exc.message}")

    text_block = next((b.text for b in response.content if b.type == "text"), None)
    if not text_block:
        sys.exit("Erreur : réponse vide de Claude.")

    # Retire d'éventuelles balises ```json … ```
    text_block = re.sub(r"^```(?:json)?\s*", "", text_block.strip(), flags=re.MULTILINE)
    text_block = re.sub(r"\s*```$", "", text_block.strip(), flags=re.MULTILINE)

    try:
        return json.loads(text_block)
    except json.JSONDecodeError as exc:
        print("--- Réponse brute de Claude (debug) ---")
        print(text_block)
        sys.exit(f"Impossible de parser le JSON : {exc}")


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
# Constructeurs Markdown
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
        header,
        "",
        f"# {ch_label} — {chapitre}",
        "",
        f"**Livre :** [[{titre}]]",
        f"**Auteur :** [[{auteur}]]",
        f"**Mouvement :** [[{mvt_nom}]]",
        "",
        "---",
        "",
        "## 📖 Résumé",
        "",
        resume,
        "",
        "---",
        "",
        "## 👤 Personnages présents",
        "",
        perso_links,
        "",
        "---",
        "",
        "## 🏷️ Thèmes",
        "",
        theme_tags,
        "",
        "---",
        "",
        "## 🏛️ Contexte historique de l'œuvre",
        "",
        contexte,
        "",
        "---",
        "",
        "## 🔗 Voir aussi",
        "",
        f"- [[00_Index]] — Index de *{titre}*",
        f"- [[Personnages]] — Tous les personnages",
        f"- [[Themes]] — Tous les thèmes",
        f"- [[{titre}_citations]] — Toutes les citations",
        "",
    ])


def build_auteur_md(fiche: dict, mouvement_nom: str, auteurs_lies: list) -> str:
    nom        = fiche.get("nom", "")
    dates      = fiche.get("dates", "")
    bio        = fiche.get("biographie", "")
    oeuvres    = fiche.get("oeuvres_majeures", [])
    influences = fiche.get("influences", [])

    oeuvres_md    = "\n".join(f"- {o}" for o in oeuvres) or "_Non renseigné._"
    influences_md = "\n".join(f"- {i}" for i in influences) or "_Non renseigné._"
    lies_md       = "\n".join(f"- [[{a}]]" for a in auteurs_lies) or "_Aucun._"

    header = fm(
        ["auteur"],
        dates=dates,
        mouvement=f"[[{mouvement_nom}]]",
        date_creation=TODAY,
    )

    return "\n".join([
        header,
        "",
        f"# {nom}",
        "",
        f"**Dates :** {dates}",
        f"**Courant :** [[{mouvement_nom}]]",
        "",
        "---",
        "",
        "## Biographie",
        "",
        bio,
        "",
        "---",
        "",
        "## Œuvres majeures",
        "",
        oeuvres_md,
        "",
        "---",
        "",
        "## Influences",
        "",
        influences_md,
        "",
        "---",
        "",
        "## Auteurs du même mouvement",
        "",
        lies_md,
        "",
    ])


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
        header,
        "",
        f"# {nom}",
        "",
        f"**Époque :** {epoque}",
        "",
        desc,
        "",
        "---",
        "",
        "## Contexte historique",
        "",
        contexte,
        "",
        "---",
        "",
        "## Auteurs représentatifs",
        "",
        lies_md,
        "",
    ])


def build_personnage_md(nom: str, description: str, titre: str, auteur: str) -> str:
    header = fm(
        ["personnage"],
        livre=f"[[{titre}]]",
        auteur=f"[[{auteur}]]",
        date_creation=TODAY,
    )

    return "\n".join([
        header,
        "",
        f"# {nom}",
        "",
        f"**Livre :** [[{titre}]]",
        f"**Auteur :** [[{auteur}]]",
        "",
        "---",
        "",
        "## Description",
        "",
        description,
        "",
    ])


def build_index_md(titre: str, auteur: str, mouvement_nom: str, contexte: str) -> str:
    header = fm(
        ["livre"],
        auteur=f"[[{auteur}]]",
        mouvement=f"[[{mouvement_nom}]]",
        date_creation=TODAY,
    )

    return "\n".join([
        header,
        "",
        f"# {titre}",
        "",
        f"**Auteur :** [[{auteur}]]",
        f"**Mouvement :** [[{mouvement_nom}]]",
        "",
        "---",
        "",
        "## Contexte historique de l'œuvre",
        "",
        contexte,
        "",
        "---",
        "",
        "## Chapitres",
        "",
        "<!-- chapitres -->",
        "",
        "---",
        "",
        "## Liens",
        "",
        f"- [[Personnages]]",
        f"- [[Themes]]",
        f"- [[{titre}_citations]]",
        "",
    ])


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


# ---------------------------------------------------------------------------
# Fonctions d'écriture dans le vault
# ---------------------------------------------------------------------------

def write_chapter(data: dict, ch_num: int) -> Path:
    """Écrit Livres/<Titre>/Chapitres/Ch_XX.md."""
    titre_safe = sanitize(data["titre"])
    ch_dir     = LIVRES_DIR / titre_safe / "Chapitres"
    ch_dir.mkdir(parents=True, exist_ok=True)
    ch_file    = ch_dir / f"Ch_{ch_num:02d}.md"
    ch_file.write_text(build_chapter_md(data, ch_num), encoding="utf-8")
    return ch_file


def update_index(data: dict, ch_num: int) -> Path:
    """Crée ou met à jour Livres/<Titre>/00_Index.md."""
    titre_safe = sanitize(data["titre"])
    mouvement  = data.get("mouvement_litteraire", {}).get("nom", "")
    index_path = LIVRES_DIR / titre_safe / "00_Index.md"
    chapitre   = data.get("chapitre_ou_passage", "")
    ch_label   = f"Ch_{ch_num:02d}"
    new_line   = f"- [[{ch_label}]] — {chapitre}"

    if not index_path.exists():
        index_path.write_text(
            build_index_md(data["titre"], data["auteur"], mouvement,
                           data.get("contexte_historique_oeuvre", "")),
            encoding="utf-8",
        )

    content = index_path.read_text(encoding="utf-8")
    if new_line not in content:
        content = content.replace("<!-- chapitres -->", f"<!-- chapitres -->\n{new_line}")
        index_path.write_text(content, encoding="utf-8")

    return index_path


def update_personnages_livre(data: dict) -> Path:
    """Crée ou complète Livres/<Titre>/Personnages.md (append uniquement)."""
    titre_safe = sanitize(data["titre"])
    path       = LIVRES_DIR / titre_safe / "Personnages.md"

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
    titre_safe = sanitize(data["titre"])
    path       = LIVRES_DIR / titre_safe / "Themes.md"

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
    """Crée Personnages/<Nom>.md pour chaque personnage si absent."""
    PERSONNAGES_DIR.mkdir(parents=True, exist_ok=True)
    titre  = data["titre"]
    auteur = data["auteur"]

    # Construit un dict nom → description depuis personnages_details
    details_map: dict[str, str] = {
        p["nom"]: p.get("description", "")
        for p in data.get("personnages_details", [])
        if isinstance(p, dict) and "nom" in p
    }

    results = []
    for nom in data.get("personnages", []):
        safe_nom = sanitize(nom)
        path     = PERSONNAGES_DIR / f"{safe_nom}.md"
        if path.exists():
            results.append((path, False))
            continue
        description = details_map.get(nom, "")
        path.write_text(
            build_personnage_md(nom, description, titre, auteur),
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


# ---------------------------------------------------------------------------
# Prévisualisation & confirmation
# ---------------------------------------------------------------------------

def preview_and_confirm(data: dict, ch_num: int) -> bool:
    """Affiche un résumé de ce qui va être écrit et demande confirmation."""
    titre_safe   = sanitize(data["titre"])
    auteur_safe  = sanitize(data.get("fiche_auteur", {}).get("nom", data["auteur"]))
    mvt_safe     = sanitize(data.get("mouvement_litteraire", {}).get("nom", ""))
    ch_label     = f"Ch_{ch_num:02d}"
    personnages  = data.get("personnages", [])

    print("\n" + "=" * 72)
    print(f"  Œuvre     : {data['titre']} — {data.get('chapitre_ou_passage', '')}")
    print(f"  Auteur    : {data['auteur']}")
    print(f"  Mouvement : {data.get('mouvement_litteraire', {}).get('nom', '')}")
    print(f"  Thèmes    : {', '.join(data.get('themes', []))}")
    print()
    print("  Fichiers qui seront créés (+) ou mis à jour (~) :")
    print(f"    +  Chapitres/{ch_label}.md")
    print(f"    ~  {titre_safe}/00_Index.md")
    print(f"    ~  {titre_safe}/Personnages.md")
    print(f"    ~  {titre_safe}/Themes.md")
    print(f"    ~  Citations/{titre_safe}_citations.md")
    print(f"    ~  00_Bibliotheque.md")
    print(f"    ?  Auteurs/{auteur_safe}.md  (créé si absent)")
    print(f"    ?  Mouvements/{mvt_safe}.md  (créé si absent)")
    for p in personnages:
        print(f"    ?  Personnages/{sanitize(p)}.md  (créé si absent)")
    print("=" * 72 + "\n")

    while True:
        ans = input("Enregistrer dans le vault Obsidian ? [o/n] : ").strip().lower()
        if ans in ("o", "oui", "y", "yes"):
            return True
        if ans in ("n", "non", "no"):
            return False


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> None:
    print("📚 Carnet de lecture littéraire — génération de fiches Obsidian")
    print(f"   Modèle : {MODEL}")
    print(f"   Vault  : {VAULT_PATH}\n")

    raw_note = collect_raw_note()

    print("\n⏳ Envoi à Claude en cours…")
    data = call_claude(raw_note)
    print(f"✔  Œuvre détectée : « {data.get('titre', '?')} » de {data.get('auteur', '?')}")

    titre_safe = sanitize(data["titre"])
    ch_dir     = LIVRES_DIR / titre_safe / "Chapitres"
    ch_num     = next_chapter_number(ch_dir)

    if not preview_and_confirm(data, ch_num):
        print("Annulé.")
        return

    # --- Écriture dans le vault ---
    ch_file                     = write_chapter(data, ch_num)
    idx_path                    = update_index(data, ch_num)
    perso_path                  = update_personnages_livre(data)
    theme_path                  = update_themes(data)
    cit_path                    = update_citations(data, ch_num)
    bib_path                    = update_bibliotheque(data)
    aut_path,  aut_created      = write_auteur(data)
    mvt_path,  mvt_created      = write_mouvement(data)
    perso_ind                   = write_personnages_individuels(data)

    # --- Rapport ---
    def rel(p: Path) -> str:
        return str(p.relative_to(VAULT_PATH))

    print("\n✅ Vault mis à jour :")
    print(f"   +  {rel(ch_file)}")
    print(f"   ~  {rel(idx_path)}")
    print(f"   ~  {rel(perso_path)}")
    print(f"   ~  {rel(theme_path)}")
    print(f"   ~  {rel(cit_path)}")
    print(f"   ~  {rel(bib_path)}")
    print(f"   {'+'  if aut_created else '='} {rel(aut_path)}{'' if aut_created else '  (existant, non modifié)'}")
    print(f"   {'+'  if mvt_created else '='} {rel(mvt_path)}{'' if mvt_created else '  (existant, non modifié)'}")
    for path, created in perso_ind:
        print(f"   {'+'  if created else '='} {rel(path)}{'' if created else '  (existant, non modifié)'}")


if __name__ == "__main__":
    main()
