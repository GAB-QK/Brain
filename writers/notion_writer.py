"""
Backend Notion — écrit les fiches dans une base Notion via l'API officielle.
Toutes les méthodes sont des stubs pour l'instant.

Prérequis futurs :
  pip install notion-client
  Variables d'environnement : NOTION_TOKEN, NOTION_ROOT_PAGE_ID
"""

from writers.base_writer import BaseWriter


class NotionWriter(BaseWriter):
    """Écrit toutes les fiches dans Notion (à implémenter)."""

    # TODO: Créer une page dans la database Notion "Chapitres"
    # avec les propriétés : titre (title), auteur (relation vers DB Auteurs),
    # mouvement (relation vers DB Mouvements), chapitre_num (number),
    # tags (multi_select rempli depuis data["themes"]), date_import (date).
    # Le corps de la page = contenu Markdown converti en blocs Notion via
    # notion_client.blocks.children.append() avec des paragraph/quote blocks.
    def write_chapter(self, data: dict, ch_num: int):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer ou mettre à jour une page "Index" dans la database Notion "Livres".
    # Si la page existe déjà (recherche par titre), ajouter un lien vers le nouveau
    # chapitre dans un bloc liste (bulleted_list_item) avec mention @page.
    # Propriétés à maintenir : titre, auteur (relation), mouvement (relation),
    # contexte_historique (rich_text), date_modification (date).
    def update_index(self, data: dict, ch_num: int):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer ou mettre à jour une page "Personnages" dans la database Notion "Livres".
    # Ajouter les personnages manquants sous forme de liens (mention @page) vers
    # leurs fiches individuelles dans la database "Personnages".
    # Éviter les doublons en récupérant la liste existante avant l'append.
    def update_personnages(self, data: dict):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer ou mettre à jour une page "Thèmes" dans la database Notion "Livres".
    # Ajouter les thèmes manquants sous forme de tags (multi_select) ou de
    # bulleted_list_items. Éviter les doublons en récupérant le contenu existant.
    def update_themes(self, data: dict):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer ou mettre à jour une sous-page "Citations" rattachée à la page
    # du livre dans la database Notion "Livres" (pas une database globale Citations).
    # Si la sous-page "Citations" n'existe pas pour ce livre, la créer via
    # notion_client.pages.create() avec parent = page du livre.
    # Ajouter les nouvelles citations sous forme de quote blocks groupés par chapitre
    # (heading_2 pour le titre du chapitre, puis un quote block par citation).
    # Éviter les doublons en comparant avec le contenu existant de la page.
    def update_citations(self, data: dict, ch_num: int):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer une page dans la database Notion "Auteurs" si elle n'existe pas.
    # Vérifier l'existence par recherche sur le nom exact avant création.
    # Propriétés : nom (title), mouvement (relation), biographie (rich_text),
    # dates_naissance_mort (rich_text), auteurs_lies (relation multi).
    # Retourner (page_id, créé: bool) pour compatibilité avec app.py.
    def write_auteur(self, data: dict):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer une page dans la database Notion "Mouvements" si elle n'existe pas.
    # Vérifier l'existence par recherche sur le nom exact avant création.
    # Propriétés : nom (title), description (rich_text), periode (rich_text),
    # contexte_historique (rich_text), auteurs_lies (relation multi).
    # Retourner (page_id, créé: bool) pour compatibilité avec app.py.
    def write_mouvement(self, data: dict):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Pour chaque personnage dans data["personnages"] :
    # - Si la page n'existe pas dans la database Notion "Personnages" (recherche
    #   par nom exact), la créer avec : nom (title), description (rich_text),
    #   apparition (rich_text, depuis personnages_details[].apparition),
    #   livres (relation multi vers DB Livres), auteurs (relation multi vers DB Auteurs).
    # - Si la page existe déjà, AJOUTER le livre courant à la propriété relation
    #   "livres" sans supprimer les relations existantes (fetch + merge + update).
    # - Dans les deux cas, ajouter un bloc au corps de la page sous la section
    #   du livre courant (heading_2 = titre du livre, puis un paragraph block
    #   avec le lien chapitre et la phrase d'apparition).
    # Retourner list[(page_id, créé: bool)] pour compatibilité avec app.py.
    def write_personnages_individuels(self, data: dict, ch_num: int):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Créer ou mettre à jour une page "Bibliothèque" (page racine fixe,
    # identifiée par NOTION_ROOT_PAGE_ID). Ajouter le titre du livre comme
    # lien (mention @page vers la page Index du livre) si absent.
    # Éviter les doublons en récupérant le contenu existant de la page.
    def update_bibliotheque(self, data: dict):
        raise NotImplementedError("Notion writer — à implémenter")

    # TODO: Interroger l'API Notion pour récupérer le contexte existant du livre :
    # - personnages : requêter la database "Personnages" filtrée par relation livre
    # - thèmes : lire les multi_select de la page "Thèmes" du livre
    # - nb_chapitres : compter les pages dans la database "Chapitres" filtrées
    #   par relation livre
    # Retourner {"personnages": [...], "themes": [...], "nb_chapitres": int}
    def get_existing_context(self, titre: str) -> dict:
        raise NotImplementedError("Notion writer — à implémenter")
