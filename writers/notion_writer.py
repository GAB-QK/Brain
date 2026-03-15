"""
Backend Notion — écrit les fiches dans des databases Notion via l'API officielle.

Nécessite : notion-client>=2.2.1
Variables d'environnement : NOTION_TOKEN, NOTION_ROOT_PAGE_ID

Structure créée automatiquement sous NOTION_ROOT_PAGE_ID :
  📗 Livres      (database) — une page par livre + sous-page Citations
  📄 Chapitres   (database) — une page par chapitre/passage importé
  👤 Auteurs     (database) — une page par auteur (créée une fois)
  🎭 Personnages (database) — une page par personnage (mise à jour à chaque import)
  🏛️ Mouvements (database) — une page par mouvement littéraire (créée une fois)

Noms de propriétés — toujours en anglais pour éviter les conflits avec les
noms internes Notion (qui garde "Name" pour la propriété title par défaut) :

  Database   | Propriétés
  -----------|-----------------------------------------------------------
  Mouvements | Name (title), Period, Description, Context, Created
  Auteurs    | Name (title), Dates, Movement, Biography, Works, Created
  Livres     | Name (title), Author, Movement, Chapters, Created
  Personnages| Name (title), Books, Authors, Description, Appearances,
             |   Created, Modified
  Chapitres  | Name (title), Book, Author, Movement, Chapter, Summary,
             |   Themes, Date, Warnings

Note de compatibilité app.py / cli.py :
  Ces modules appellent rel(path) sur tous les retours, ce qui nécessite des
  objets Path. Le NotionWriter retourne des page_ids (str) ou None selon les
  méthodes. Une mise à jour future de app.py / cli.py permettra d'afficher
  les URLs Notion dans l'interface web.
"""

import logging
import time
from typing import Any, Optional

import httpx

try:
    from notion_client import Client
    from notion_client.errors import APIResponseError
except ImportError as _exc:
    raise ImportError(
        "notion-client n'est pas installé.\n"
        "Lance : pip install notion-client>=2.2.1"
    ) from _exc

from config import TODAY, NOTION_TOKEN, NOTION_ROOT_PAGE_ID
from writers.base_writer import BaseWriter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de construction de blocs Notion
# ---------------------------------------------------------------------------

def _rich_text(text: str) -> list[dict]:
    """Construit un rich_text array Notion (tronqué à 2000 chars par entrée)."""
    return [{"type": "text", "text": {"content": str(text)[:2000]}}]


def _para(text: str) -> dict:
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _h1(text: str) -> dict:
    return {
        "object": "block", "type": "heading_1",
        "heading_1": {"rich_text": _rich_text(text)},
    }


def _h2(text: str) -> dict:
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": _rich_text(text)},
    }


def _h3(text: str) -> dict:
    return {
        "object": "block", "type": "heading_3",
        "heading_3": {"rich_text": _rich_text(text)},
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(text)},
    }


def _quote(text: str) -> dict:
    return {
        "object": "block", "type": "quote",
        "quote": {"rich_text": _rich_text(text)},
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


# ---------------------------------------------------------------------------
# NotionWriter
# ---------------------------------------------------------------------------

class NotionWriter(BaseWriter):
    """Écrit toutes les fiches dans Notion via l'API officielle."""

    # Ordre de création respectant les dépendances de relations
    _CREATION_ORDER = ["Mouvements", "Auteurs", "Livres", "Personnages", "Chapitres"]

    def __init__(self):
        if not NOTION_TOKEN:
            raise ValueError(
                "NOTION_TOKEN manquant dans .env — "
                "configure NOTION_TOKEN pour utiliser le backend Notion."
            )
        if not NOTION_ROOT_PAGE_ID:
            raise ValueError(
                "NOTION_ROOT_PAGE_ID manquant dans .env — "
                "configure NOTION_ROOT_PAGE_ID pour utiliser le backend Notion."
            )

        self.notion = Client(auth=NOTION_TOKEN)
        self._root_id = NOTION_ROOT_PAGE_ID
        self._db_ids: dict[str, str] = {}
        self._ensure_databases()

    # ─────────────────────────────────────────────────────────────────────────
    # Initialisation des databases
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_databases(self) -> None:
        """Vérifie et crée les databases manquantes sous NOTION_ROOT_PAGE_ID."""
        existing = self._list_child_databases()
        for name in self._CREATION_ORDER:
            if name in existing:
                self._db_ids[name] = existing[name]
            else:
                schema = self._db_schema(name)
                db = self._retry(
                    self.notion.databases.create,
                    parent={"type": "page_id", "page_id": self._root_id},
                    title=_rich_text(name),
                    properties=schema,
                )
                self._db_ids[name] = db["id"]
                logger.info("Database Notion créée : %s (%s)", name, db["id"])

    def _list_child_databases(self) -> dict[str, str]:
        """Retourne {nom: id} des databases enfants directs de la page racine."""
        found: dict[str, str] = {}
        cursor: Optional[str] = None
        while True:
            kwargs: dict[str, Any] = {"block_id": self._root_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = self._retry(self.notion.blocks.children.list, **kwargs)
            for block in resp.get("results", []):
                if block.get("type") == "child_database":
                    title = block.get("child_database", {}).get("title", "")
                    if title:
                        found[title] = block["id"]
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return found

    def _db_schema(self, name: str) -> dict:
        """Retourne le schéma de propriétés pour une database donnée.
        Appelé dans l'ordre _CREATION_ORDER : les IDs des dépendances sont déjà dans _db_ids.
        Toutes les propriétés sont nommées en anglais — Notion garde "Name" pour le
        champ title par défaut et peut ignorer les noms non-ASCII à la création."""

        def _rel(db_name: str) -> dict:
            return {"relation": {"database_id": self._db_ids[db_name]}}

        if name == "Mouvements":
            return {
                "Name":        {"title": {}},
                "Period":      {"rich_text": {}},
                "Description": {"rich_text": {}},
                "Context":     {"rich_text": {}},
                "Created":     {"date": {}},
            }
        if name == "Auteurs":
            return {
                "Name":      {"title": {}},
                "Dates":     {"rich_text": {}},
                "Movement":  _rel("Mouvements"),
                "Biography": {"rich_text": {}},
                "Works":     {"rich_text": {}},
                "Created":   {"date": {}},
            }
        if name == "Livres":
            return {
                "Name":     {"title": {}},
                "Author":   _rel("Auteurs"),
                "Movement": _rel("Mouvements"),
                "Chapters": {"number": {}},
                "Created":  {"date": {}},
            }
        if name == "Personnages":
            return {
                "Name":         {"title": {}},
                "Books":        _rel("Livres"),
                "Authors":      _rel("Auteurs"),
                "Description":  {"rich_text": {}},
                "Appearances":  {"rich_text": {}},
                "Created":      {"date": {}},
                "Modified":     {"date": {}},
            }
        if name == "Chapitres":
            return {
                "Name":     {"title": {}},
                "Book":     _rel("Livres"),
                "Author":   _rel("Auteurs"),
                "Movement": _rel("Mouvements"),
                "Chapter":  {"rich_text": {}},
                "Summary":  {"rich_text": {}},
                "Themes":   {"multi_select": {}},
                "Date":     {"date": {}},
                "Warnings": {"rich_text": {}},
            }
        raise ValueError(f"Database inconnue : {name}")

    # ─────────────────────────────────────────────────────────────────────────
    # Retry avec backoff exponentiel (rate limit Notion)
    # ─────────────────────────────────────────────────────────────────────────

    def _retry(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Exécute func(*args, **kwargs) avec 3 tentatives et backoff exponentiel."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except APIResponseError as exc:
                if exc.status == 429 and attempt < max_attempts - 1:
                    wait = 2 ** attempt  # 1s, 2s
                    logger.warning(
                        "Rate limit Notion — attente %ds (tentative %d/%d)",
                        wait, attempt + 1, max_attempts,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Erreur API Notion %s : %s", exc.status, exc.body
                    )
                    raise

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers de recherche
    # ─────────────────────────────────────────────────────────────────────────

    def _db_query(
        self,
        database_id: str,
        filter: Optional[dict] = None,
        sorts: Optional[list] = None,
    ) -> dict:
        """Interroge une database Notion via POST /v1/databases/{id}/query.
        Utilise httpx directement — compatible notion-client v2 et v3."""
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        body: dict = {}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        max_attempts = 3
        for attempt in range(max_attempts):
            resp = httpx.post(url, headers=headers, json=body, timeout=60.0)
            if resp.status_code == 429 and attempt < max_attempts - 1:
                wait = 2 ** attempt
                logger.warning(
                    "Rate limit Notion — attente %ds (tentative %d/%d)",
                    wait, attempt + 1, max_attempts,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()

    def _find_page_by_title(
        self, db_name: str, title: str, prop: str = "title"
    ) -> Optional[dict]:
        """Cherche une page par son champ title.
        Notion identifie toujours la propriété title via l'ID interne "title",
        indépendamment du nom affiché (Name, Nom, Titre…)."""
        resp = self._db_query(
            self._db_ids[db_name],
            filter={"property": prop, "title": {"equals": title}},
        )
        results = resp.get("results", [])
        return results[0] if results else None

    def _get_page_id(
        self, db_name: str, title: str, prop: str = "title"
    ) -> Optional[str]:
        """Retourne l'id d'une page ou None si introuvable."""
        page = self._find_page_by_title(db_name, title, prop)
        return page["id"] if page else None

    def _find_citations_subpage(self, livre_page_id: str) -> Optional[str]:
        """Trouve la sous-page Citations d'une page livre. Retourne son id ou None."""
        cursor: Optional[str] = None
        while True:
            kwargs: dict[str, Any] = {"block_id": livre_page_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = self._retry(self.notion.blocks.children.list, **kwargs)
            for block in resp.get("results", []):
                if block.get("type") == "child_page":
                    if block.get("child_page", {}).get("title") == "Citations":
                        return block["id"]
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return None

    def _get_all_block_plaintext(self, page_id: str) -> str:
        """Retourne le contenu textuel brut de tous les blocs d'une page (pour dédoublonnage)."""
        texts: list[str] = []
        cursor: Optional[str] = None
        while True:
            kwargs: dict[str, Any] = {"block_id": page_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = self._retry(self.notion.blocks.children.list, **kwargs)
            for block in resp.get("results", []):
                btype = block.get("type", "")
                for rt in block.get(btype, {}).get("rich_text", []):
                    texts.append(rt.get("plain_text", ""))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return "\n".join(texts)

    def _append_blocks(self, block_id: str, children: list[dict]) -> None:
        """Ajoute des blocs à une page, par lots de 100 (limite Notion)."""
        for i in range(0, len(children), 100):
            self._retry(
                self.notion.blocks.children.append,
                block_id=block_id,
                children=children[i:i + 100],
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Chapitre
    # ─────────────────────────────────────────────────────────────────────────

    def write_chapter(self, data: dict, ch_num: int) -> str:
        """Crée une page dans la database Chapitres. Retourne le page_id."""
        titre          = data["titre"]
        auteur         = data["auteur"]
        mouvement      = data.get("mouvement_litteraire", {}).get("nom", "")
        chapitre       = data.get("chapitre_ou_passage", f"Ch_{ch_num:02d}")
        resume         = data.get("resume", "") or ""
        themes         = data.get("themes", [])
        personnages    = data.get("personnages", [])
        citations      = data.get("citations", [])
        avertissements = data.get("avertissements", [])
        ch_label       = f"Ch_{ch_num:02d}"

        livre_id  = self._get_page_id("Livres", titre)
        auteur_id = self._get_page_id("Auteurs", auteur)
        mvt_id    = self._get_page_id("Mouvements", mouvement) if mouvement else None

        props: dict[str, Any] = {
            "Name":     {"title": _rich_text(f"{ch_label} — {chapitre}")},
            "Chapter":  {"rich_text": _rich_text(chapitre)},
            "Summary":  {"rich_text": _rich_text(resume[:2000])},
            "Themes":   {"multi_select": [{"name": t} for t in themes]},
            "Date":     {"date": {"start": TODAY}},
            "Warnings": {"rich_text": _rich_text("; ".join(avertissements))},
        }
        if livre_id:
            props["Book"] = {"relation": [{"id": livre_id}]}
        if auteur_id:
            props["Author"] = {"relation": [{"id": auteur_id}]}
        if mvt_id:
            props["Movement"] = {"relation": [{"id": mvt_id}]}

        children: list[dict] = [
            _h1(f"{ch_label} — {chapitre}"),
            _divider(),
            _h2("📖 Résumé"),
            _para(resume),
            _divider(),
            _h2("👤 Personnages présents"),
            *(_bullet(p) for p in personnages),
            _divider(),
            _h2("💬 Citations"),
            *(_quote(c) for c in citations),
        ]
        if avertissements:
            children += [_divider(), _h2("⚠️ Avertissements")]
            children += [_bullet(a) for a in avertissements]

        page = self._retry(
            self.notion.pages.create,
            parent={"database_id": self._db_ids["Chapitres"]},
            properties=props,
            children=children[:100],
        )
        page_id = page["id"]
        if len(children) > 100:
            self._append_blocks(page_id, children[100:])
        return page_id

    # ─────────────────────────────────────────────────────────────────────────
    # Index du livre (database Livres + sous-page Citations)
    # ─────────────────────────────────────────────────────────────────────────

    def update_index(self, data: dict, ch_num: int) -> str:
        """Crée ou met à jour la page livre dans Livres. Retourne le page_id."""
        titre     = data["titre"]
        auteur    = data["auteur"]
        mouvement = data.get("mouvement_litteraire", {}).get("nom", "")
        contexte  = data.get("contexte_historique_oeuvre", "")
        chapitre  = data.get("chapitre_ou_passage", f"Ch_{ch_num:02d}")
        ch_label  = f"Ch_{ch_num:02d}"

        auteur_id = self._get_page_id("Auteurs", auteur)
        mvt_id    = self._get_page_id("Mouvements", mouvement) if mouvement else None

        existing = self._find_page_by_title("Livres", titre)
        if existing is None:
            props: dict[str, Any] = {
                "Name":     {"title": _rich_text(titre)},
                "Chapters": {"number": 1},
                "Created":  {"date": {"start": TODAY}},
            }
            if auteur_id:
                props["Author"] = {"relation": [{"id": auteur_id}]}
            if mvt_id:
                props["Movement"] = {"relation": [{"id": mvt_id}]}

            livre_page = self._retry(
                self.notion.pages.create,
                parent={"database_id": self._db_ids["Livres"]},
                properties=props,
                children=[
                    _h1(titre),
                    _para(f"Auteur : {auteur}"),
                    *([_para(f"Mouvement : {mouvement}")] if mouvement else []),
                    *([_divider(), _h2("Contexte historique"), _para(contexte)] if contexte else []),
                    _divider(),
                    _h2("📚 Chapitres"),
                    _bullet(f"{ch_label} — {chapitre}"),
                ],
            )
            livre_id = livre_page["id"]

            # Créer la sous-page Citations vide
            self._retry(
                self.notion.pages.create,
                parent={"type": "page_id", "page_id": livre_id},
                properties={"title": [{"type": "text", "text": {"content": "Citations"}}]},
                children=[_h1(f"Citations — {titre}"), _divider()],
            )
        else:
            livre_id = existing["id"]
            nb = (
                existing.get("properties", {})
                .get("Chapters", {})
                .get("number") or 0
            )
            self._retry(
                self.notion.pages.update,
                page_id=livre_id,
                properties={"Chapters": {"number": nb + 1}},
            )
            self._append_blocks(livre_id, [_bullet(f"{ch_label} — {chapitre}")])

        return livre_id

    # ─────────────────────────────────────────────────────────────────────────
    # Personnages (liste agrégée par livre) — no-op pour Notion
    # ─────────────────────────────────────────────────────────────────────────

    def update_personnages(self, data: dict) -> None:
        """No-op : pour Notion, les personnages sont gérés par write_personnages_individuels."""
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Thèmes — no-op pour Notion
    # ─────────────────────────────────────────────────────────────────────────

    def update_themes(self, data: dict) -> None:
        """No-op : pour Notion, les thèmes sont portés par le champ multi_select des Chapitres."""
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Citations (sous-page de la page livre)
    # ─────────────────────────────────────────────────────────────────────────

    def update_citations(self, data: dict, ch_num: int) -> Optional[str]:
        """Ajoute les nouvelles citations dans la sous-page Citations du livre. Retourne le page_id."""
        titre     = data["titre"]
        chapitre  = data.get("chapitre_ou_passage", f"Ch_{ch_num:02d}")
        citations = data.get("citations", [])

        if not citations:
            return None

        livre_page = self._find_page_by_title("Livres", titre)
        if livre_page is None:
            return None

        cit_page_id = self._find_citations_subpage(livre_page["id"])
        if cit_page_id is None:
            return None

        existing_text = self._get_all_block_plaintext(cit_page_id)
        nouvelles = [c for c in citations if c not in existing_text]
        if nouvelles:
            blocks: list[dict] = [_h2(chapitre)]
            blocks += [_quote(c) for c in nouvelles]
            self._append_blocks(cit_page_id, blocks)

        return cit_page_id

    # ─────────────────────────────────────────────────────────────────────────
    # Auteur
    # ─────────────────────────────────────────────────────────────────────────

    def write_auteur(self, data: dict) -> tuple[str, bool]:
        """Crée la page auteur dans Auteurs si absente. Retourne (page_id, créé)."""
        fiche     = data.get("fiche_auteur", {})
        nom       = fiche.get("nom", data["auteur"])
        dates     = fiche.get("dates", "")
        bio       = fiche.get("biographie", "")
        oeuvres   = fiche.get("oeuvres_majeures", [])
        mouvement = data.get("mouvement_litteraire", {}).get("nom", "")

        existing = self._find_page_by_title("Auteurs", nom)
        if existing:
            return existing["id"], False

        mvt_id = self._get_page_id("Mouvements", mouvement) if mouvement else None

        props: dict[str, Any] = {
            "Name":      {"title": _rich_text(nom)},
            "Dates":     {"rich_text": _rich_text(dates)},
            "Biography": {"rich_text": _rich_text(bio[:2000])},
            "Works":     {"rich_text": _rich_text(", ".join(oeuvres))},
            "Created":   {"date": {"start": TODAY}},
        }
        if mvt_id:
            props["Movement"] = {"relation": [{"id": mvt_id}]}

        children: list[dict] = [
            _h1(nom),
            *([_para(f"Dates : {dates}")] if dates else []),
            *([_para(f"Courant : {mouvement}")] if mouvement else []),
            _divider(),
            _h2("Biographie"),
            _para(bio),
        ]
        if oeuvres:
            children += [_divider(), _h2("Œuvres majeures")]
            children += [_bullet(o) for o in oeuvres]

        page = self._retry(
            self.notion.pages.create,
            parent={"database_id": self._db_ids["Auteurs"]},
            properties=props,
            children=children[:100],
        )
        return page["id"], True

    # ─────────────────────────────────────────────────────────────────────────
    # Mouvement
    # ─────────────────────────────────────────────────────────────────────────

    def write_mouvement(self, data: dict) -> tuple[str, bool]:
        """Crée la page mouvement dans Mouvements si absente. Retourne (page_id, créé)."""
        mouvement = data.get("mouvement_litteraire", {})
        nom       = mouvement.get("nom", "Inconnu")
        epoque    = mouvement.get("epoque", "")
        desc      = mouvement.get("description", "")
        contexte  = mouvement.get("contexte_historique", "")

        existing = self._find_page_by_title("Mouvements", nom)
        if existing:
            return existing["id"], False

        props: dict[str, Any] = {
            "Name":        {"title": _rich_text(nom)},
            "Period":      {"rich_text": _rich_text(epoque)},
            "Description": {"rich_text": _rich_text(desc[:2000])},
            "Context":     {"rich_text": _rich_text(contexte[:2000])},
            "Created":     {"date": {"start": TODAY}},
        }

        children: list[dict] = [
            _h1(nom),
            *([_para(f"Époque : {epoque}")] if epoque else []),
            _para(desc),
            _divider(),
            _h2("Contexte historique"),
            _para(contexte),
        ]

        page = self._retry(
            self.notion.pages.create,
            parent={"database_id": self._db_ids["Mouvements"]},
            properties=props,
            children=children[:100],
        )
        return page["id"], True

    # ─────────────────────────────────────────────────────────────────────────
    # Personnages individuels (database Personnages, liens inter-œuvres)
    # ─────────────────────────────────────────────────────────────────────────

    def write_personnages_individuels(
        self, data: dict, ch_num: int
    ) -> list[tuple[str, bool]]:
        """Crée ou met à jour les fiches personnages. Retourne list[(page_id, créé)]."""
        titre    = data["titre"]
        auteur   = data["auteur"]
        ch_label = f"Ch_{ch_num:02d}"

        details_map: dict[str, dict] = {
            p["nom"]: p
            for p in data.get("personnages_details", [])
            if isinstance(p, dict) and "nom" in p
        }

        livre_id  = self._get_page_id("Livres", titre)
        auteur_id = self._get_page_id("Auteurs", auteur)

        results: list[tuple[str, bool]] = []
        for nom in data.get("personnages", []):
            details         = details_map.get(nom, {})
            desc            = details.get("description", "")
            apparition      = details.get("apparition", "")
            apparition_line = f"{ch_label} — {apparition}" if apparition else ch_label

            existing = self._find_page_by_title("Personnages", nom)
            if existing is None:
                props: dict[str, Any] = {
                    "Name":        {"title": _rich_text(nom)},
                    "Description": {"rich_text": _rich_text(desc[:2000])},
                    "Appearances": {"rich_text": _rich_text(apparition_line)},
                    "Created":     {"date": {"start": TODAY}},
                    "Modified":    {"date": {"start": TODAY}},
                }
                if livre_id:
                    props["Books"] = {"relation": [{"id": livre_id}]}
                if auteur_id:
                    props["Authors"] = {"relation": [{"id": auteur_id}]}

                children: list[dict] = [
                    _h1(nom),
                    _para(f"Livre d'origine : {titre}"),
                    _para(f"Auteur : {auteur}"),
                    _divider(),
                    _h2("Description"),
                    _para(desc),
                    _divider(),
                    _h2("Présent dans ces œuvres"),
                    _bullet(f"{titre} — {auteur}"),
                    _divider(),
                    _h2("Apparitions par œuvre"),
                    _h3(titre),
                    _bullet(apparition_line),
                ]

                page = self._retry(
                    self.notion.pages.create,
                    parent={"database_id": self._db_ids["Personnages"]},
                    properties=props,
                    children=children[:100],
                )
                results.append((page["id"], True))
            else:
                self._update_personnage_existing(
                    existing["id"], existing,
                    livre_id, auteur_id,
                    titre, auteur, apparition_line,
                )
                results.append((existing["id"], False))

        return results

    def _update_personnage_existing(
        self,
        page_id: str,
        page: dict,
        livre_id: Optional[str],
        auteur_id: Optional[str],
        titre: str,
        auteur: str,
        apparition_line: str,
    ) -> None:
        """Met à jour une fiche personnage existante (append-only, non destructif)."""
        props = page.get("properties", {})

        # ── 1. Mettre à jour les relations Books / Authors ────────────────────
        update_props: dict[str, Any] = {
            "Modified": {"date": {"start": TODAY}},
        }

        if livre_id:
            existing_livres = [r["id"] for r in props.get("Books", {}).get("relation", [])]
            if livre_id not in existing_livres:
                update_props["Books"] = {
                    "relation": [{"id": lid} for lid in existing_livres + [livre_id]]
                }

        if auteur_id:
            existing_auteurs = [r["id"] for r in props.get("Authors", {}).get("relation", [])]
            if auteur_id not in existing_auteurs:
                update_props["Authors"] = {
                    "relation": [{"id": aid} for aid in existing_auteurs + [auteur_id]]
                }

        # ── 2. Mettre à jour le champ Appearances (rich_text résumé) ──────────
        existing_app = "".join(
            rt.get("plain_text", "")
            for rt in props.get("Appearances", {}).get("rich_text", [])
        )
        if apparition_line not in existing_app:
            new_app = (existing_app + "\n" + apparition_line).strip()
            update_props["Appearances"] = {"rich_text": _rich_text(new_app[:2000])}

        self._retry(self.notion.pages.update, page_id=page_id, properties=update_props)

        # ── 3. Mettre à jour le corps de la page ──────────────────────────────
        all_text = self._get_all_block_plaintext(page_id)

        # Ajouter dans "Présent dans ces œuvres"
        oeuvre_line = f"{titre} — {auteur}"
        blocks_to_add: list[dict] = []
        if oeuvre_line not in all_text:
            blocks_to_add.append(_bullet(oeuvre_line))

        # Ajouter sous "Apparitions par œuvre"
        if apparition_line not in all_text:
            if titre not in all_text:
                # Premier chapitre de ce livre : ajouter le titre de section
                blocks_to_add += [_h3(titre), _bullet(apparition_line)]
            else:
                # Livre déjà présent, ajouter juste la ligne d'apparition
                blocks_to_add.append(_bullet(apparition_line))

        if blocks_to_add:
            self._append_blocks(page_id, blocks_to_add)

    # ─────────────────────────────────────────────────────────────────────────
    # Bibliothèque — no-op pour Notion
    # ─────────────────────────────────────────────────────────────────────────

    def update_bibliotheque(self, data: dict) -> None:
        """No-op : pour Notion, la bibliothèque est la database Livres elle-même."""
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Contexte existant (pour enrichir le prompt Claude)
    # ─────────────────────────────────────────────────────────────────────────

    def get_existing_context(self, titre: str) -> dict:
        """
        Interroge Notion pour récupérer le contexte existant d'un livre.
        Retourne {personnages, themes, nb_chapitres}.
        """
        livre_page = self._find_page_by_title("Livres", titre)
        if livre_page is None:
            return {"personnages": [], "themes": [], "nb_chapitres": 0}

        livre_id = livre_page["id"]
        nb = (
            livre_page.get("properties", {})
            .get("Chapters", {})
            .get("number") or 0
        )

        # Personnages liés à ce livre
        personnages: list[str] = []
        resp = self._db_query(
            self._db_ids["Personnages"],
            filter={"property": "Books", "relation": {"contains": livre_id}},
        )
        for p in resp.get("results", []):
            for rt in p.get("properties", {}).get("Name", {}).get("title", []):
                name = rt.get("plain_text", "")
                if name:
                    personnages.append(name)

        # Thèmes des chapitres liés à ce livre
        themes_set: set[str] = set()
        resp_ch = self._db_query(
            self._db_ids["Chapitres"],
            filter={"property": "Book", "relation": {"contains": livre_id}},
        )
        for ch in resp_ch.get("results", []):
            for opt in ch.get("properties", {}).get("Themes", {}).get("multi_select", []):
                name = opt.get("name", "")
                if name:
                    themes_set.add(name)

        return {
            "personnages":  personnages,
            "themes":       list(themes_set),
            "nb_chapitres": int(nb),
        }
