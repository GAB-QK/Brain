"""
Interface terminal — prévisualisation des fichiers à écrire et confirmation utilisateur.
"""

from config import VAULT_PATH
from writers import sanitize


def preview_and_confirm(data: dict, ch_num: int) -> bool:
    """
    Affiche un résumé lisible de ce qui sera créé ou mis à jour dans le vault,
    puis demande une confirmation [o/n] avant toute écriture.
    Retourne True si l'utilisateur confirme, False sinon.
    """
    titre_safe  = sanitize(data["titre"])
    auteur_safe = sanitize(data.get("fiche_auteur", {}).get("nom", data["auteur"]))
    mvt_safe    = sanitize(data.get("mouvement_litteraire", {}).get("nom", ""))
    ch_label    = f"Ch_{ch_num:02d}"
    personnages = data.get("personnages", [])

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
    print("=" * 72)

    avertissements = data.get("avertissements", [])
    if avertissements:
        print()
        print("⚠️  Points à vérifier dans ta note :")
        for a in avertissements:
            print(f"  - {a}")

    print()
    while True:
        ans = input("Enregistrer dans le vault Obsidian ? [o/n] : ").strip().lower()
        if ans in ("o", "oui", "y", "yes"):
            return True
        if ans in ("n", "non", "no"):
            return False


def print_report(data: dict, ch_num: int, results: dict) -> None:
    """Affiche le rapport final des fichiers écrits dans le vault."""

    def rel(p) -> str:
        return str(p.relative_to(VAULT_PATH))

    def status(created: bool) -> str:
        return "+" if created else "= (existant, non modifié)"

    print("\n✅ Vault mis à jour :")
    print(f"   +  {rel(results['chapter'])}")
    print(f"   ~  {rel(results['index'])}")
    print(f"   ~  {rel(results['personnages_livre'])}")
    print(f"   ~  {rel(results['themes'])}")
    print(f"   ~  {rel(results['citations'])}")
    print(f"   ~  {rel(results['bibliotheque'])}")
    print(f"   {status(results['auteur_created'])} {rel(results['auteur'])}")
    print(f"   {status(results['mouvement_created'])} {rel(results['mouvement'])}")
    for path, created in results["personnages_ind"]:
        print(f"   {status(created)} {rel(path)}")
