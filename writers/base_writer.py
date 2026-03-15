"""
Interface abstraite pour les backends d'écriture.
Chaque backend (Obsidian, Notion…) implémente cette classe.
"""

from abc import ABC, abstractmethod


class BaseWriter(ABC):

    @abstractmethod
    def write_chapter(self, data: dict, ch_num: int):
        """Crée la fiche du chapitre/passage."""
        pass

    @abstractmethod
    def update_index(self, data: dict, ch_num: int):
        """Crée ou met à jour l'index du livre."""
        pass

    @abstractmethod
    def update_personnages(self, data: dict):
        """Crée ou complète la liste agrégée des personnages du livre."""
        pass

    @abstractmethod
    def update_themes(self, data: dict):
        """Crée ou complète la liste agrégée des thèmes du livre."""
        pass

    @abstractmethod
    def update_citations(self, data: dict, ch_num: int):
        """Crée ou alimente le fichier de citations du livre."""
        pass

    @abstractmethod
    def write_auteur(self, data: dict):
        """Crée la fiche auteur si elle n'existe pas encore."""
        pass

    @abstractmethod
    def write_mouvement(self, data: dict):
        """Crée la fiche du mouvement littéraire si elle n'existe pas encore."""
        pass

    @abstractmethod
    def write_personnages_individuels(self, data: dict):
        """Crée une fiche individuelle pour chaque nouveau personnage."""
        pass

    @abstractmethod
    def update_bibliotheque(self, data: dict):
        """Crée ou met à jour l'index global de la bibliothèque."""
        pass

    @abstractmethod
    def get_existing_context(self, titre: str) -> dict:
        """
        Retourne le contexte existant du livre pour enrichir le prompt Claude
        lors des imports suivants.

        Doit retourner un dict avec :
          - "personnages"  : list[str]  — personnages déjà enregistrés
          - "themes"       : list[str]  — thèmes déjà enregistrés
          - "nb_chapitres" : int        — nombre de chapitres déjà importés
        """
        pass
