"""
Appel à l'API Claude — prompt système, envoi de la note, parsing du JSON.
Gère toutes les exceptions Anthropic et quitte proprement en cas d'erreur.
"""

import json
import re
import sys
import textwrap

import anthropic

from config import MODEL

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
        {"nom": "Personnage 1", "description": "Description courte (1-2 phrases)"},
        {"nom": "Personnage 2", "description": "Description courte (1-2 phrases)"}
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


def call_claude(raw_note: str) -> dict:
    """
    Envoie la note brute à Claude et retourne le JSON structuré parsé.
    Quitte le processus en cas d'erreur API ou de JSON invalide.
    """
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
    text_block = re.sub(r"\s*```$",          "", text_block.strip(), flags=re.MULTILINE)

    try:
        return json.loads(text_block)
    except json.JSONDecodeError as exc:
        print("--- Réponse brute de Claude (debug) ---")
        print(text_block)
        sys.exit(f"Impossible de parser le JSON : {exc}")
