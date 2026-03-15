import pytest
from writers.obsidian_writer import ObsidianWriter


@pytest.fixture
def writer(vault_tmp):
    return ObsidianWriter()


# ---------------------------------------------------------------------------
# write_chapter
# ---------------------------------------------------------------------------

def test_write_chapter_creates_file(writer, data_ch1, vault_tmp):
    path = writer.write_chapter(data_ch1, 1)
    assert path.exists()
    content = path.read_text()
    assert "Ch_01" in content
    assert "Chapitre 1" in content
    assert "type/chapitre" in content


def test_write_chapter_numbering(writer, data_ch1, data_ch4, vault_tmp):
    writer.write_chapter(data_ch1, 1)
    writer.write_chapter(data_ch4, 4)

    litt = vault_tmp / "Littérature"
    ch_dir = litt / "Livres" / "Le Père Goriot" / "Chapitres"
    assert (ch_dir / "Ch_01.md").exists()
    assert (ch_dir / "Ch_04.md").exists()
    assert not (ch_dir / "Ch_02.md").exists()
    assert not (ch_dir / "Ch_03.md").exists()


# ---------------------------------------------------------------------------
# update_index
# ---------------------------------------------------------------------------

def test_update_index_created_on_first_import(writer, data_ch1, vault_tmp):
    writer.update_index(data_ch1, 1)
    index_path = vault_tmp / "Littérature" / "Livres" / "Le Père Goriot" / "00_Index.md"
    assert index_path.exists()
    content = index_path.read_text()
    assert "[[Ch_01]]" in content


def test_update_index_appends_on_second_import(writer, data_ch1, data_ch4, vault_tmp):
    writer.update_index(data_ch1, 1)
    writer.update_index(data_ch4, 4)
    index_path = vault_tmp / "Littérature" / "Livres" / "Le Père Goriot" / "00_Index.md"
    content = index_path.read_text()
    assert "[[Ch_01]]" in content
    assert "[[Ch_04]]" in content
    # Only one frontmatter block
    assert content.count("tags:") == 1


# ---------------------------------------------------------------------------
# write_auteur
# ---------------------------------------------------------------------------

def test_write_auteur_creates_file(writer, data_ch1, vault_tmp):
    path, created = writer.write_auteur(data_ch1)
    assert created is True
    assert path.exists()
    content = path.read_text()
    assert "Eugénie Grandet" in content


def test_write_auteur_no_overwrite(writer, data_ch1, vault_tmp):
    path1, created1 = writer.write_auteur(data_ch1)
    path2, created2 = writer.write_auteur(data_ch1)
    assert created1 is True
    assert created2 is False
    assert path1 == path2
    content = path2.read_text()
    assert content.count("Romancier français.") == 1


def test_write_auteur_enrichissement(writer, data_ch1, data_ch4, vault_tmp):
    writer.write_auteur(data_ch1)
    writer.write_auteur(data_ch4)

    path = vault_tmp / "Littérature" / "Auteurs" / "Honoré de Balzac.md"
    content = path.read_text()
    assert "César Birotteau" in content
    assert "Émile Zola" in content
    assert "Romancier français." in content
    assert content.count("Romancier français.") == 1


def test_write_auteur_no_duplicate_auteurs_lies(writer, data_ch1, data_ch4, vault_tmp):
    writer.write_auteur(data_ch1)  # crée avec Flaubert, Stendhal
    writer.write_auteur(data_ch4)  # Flaubert déjà présent, ne doit pas être dupliqué

    path = vault_tmp / "Littérature" / "Auteurs" / "Honoré de Balzac.md"
    content = path.read_text()
    fm_end = content.index("\n---\n", 3)
    fm_part = content[:fm_end]
    body_part = content[fm_end:]
    assert fm_part.count("Gustave Flaubert") == 1
    assert body_part.count("Gustave Flaubert") == 1


# ---------------------------------------------------------------------------
# write_mouvement
# ---------------------------------------------------------------------------

def test_write_mouvement_creates_file(writer, data_ch1, vault_tmp):
    path, created = writer.write_mouvement(data_ch1)
    assert created is True
    assert path.exists()


def test_write_mouvement_no_overwrite(writer, data_ch1, vault_tmp):
    path1, created1 = writer.write_mouvement(data_ch1)
    path2, created2 = writer.write_mouvement(data_ch1)
    assert created1 is True
    assert created2 is False
    assert path1 == path2


# ---------------------------------------------------------------------------
# write_personnages_individuels
# ---------------------------------------------------------------------------

def test_write_personnages_individuels_creates_files(writer, data_ch1, vault_tmp):
    results = writer.write_personnages_individuels(data_ch1, 1)
    perso_dir = vault_tmp / "Littérature" / "Personnages"
    assert (perso_dir / "Rastignac.md").exists()
    assert (perso_dir / "Vautrin.md").exists()
    assert (perso_dir / "Père Goriot.md").exists()
    for path, _ in results:
        assert "## Présent dans ces œuvres" in path.read_text()


def test_write_personnages_individuels_inter_oeuvres(writer, data_ch1, vault_tmp):
    writer.write_personnages_individuels(data_ch1, 1)

    # Simule un second livre avec Rastignac
    data_other = dict(data_ch1)
    data_other["titre"] = "Eugénie Grandet"
    data_other["personnages"] = ["Rastignac"]
    data_other["personnages_details"] = [
        {"nom": "Rastignac", "description": "Jeune provincial.", "apparition": "Caméo."},
    ]
    writer.write_personnages_individuels(data_other, 1)

    path = vault_tmp / "Littérature" / "Personnages" / "Rastignac.md"
    content = path.read_text()
    assert "Le Père Goriot" in content
    assert "Eugénie Grandet" in content


# ---------------------------------------------------------------------------
# update_citations
# ---------------------------------------------------------------------------

def test_update_citations_no_duplicate(writer, data_ch1, vault_tmp):
    writer.update_citations(data_ch1, 1)
    writer.update_citations(data_ch1, 1)
    path = vault_tmp / "Littérature" / "Livres" / "Le Père Goriot" / "Citations.md"
    content = path.read_text()
    assert content.count("Paris est un bourbier.") == 1


# ---------------------------------------------------------------------------
# update_themes
# ---------------------------------------------------------------------------

def test_update_themes_no_duplicate(writer, data_ch1, vault_tmp):
    writer.update_index(data_ch1, 1)  # crée le répertoire du livre
    writer.update_themes(data_ch1)
    writer.update_themes(data_ch1)
    path = vault_tmp / "Littérature" / "Livres" / "Le Père Goriot" / "Themes.md"
    content = path.read_text()
    assert content.count("#ambition") == 1


# ---------------------------------------------------------------------------
# get_existing_context
# ---------------------------------------------------------------------------

def test_get_existing_context_empty(writer):
    ctx = writer.get_existing_context("Livre inexistant")
    assert ctx == {"personnages": [], "themes": [], "nb_chapitres": 0}


def test_get_existing_context_after_import(writer, data_ch1, vault_tmp):
    writer.write_chapter(data_ch1, 1)
    writer.update_index(data_ch1, 1)
    writer.update_personnages(data_ch1)
    writer.update_themes(data_ch1)

    ctx = writer.get_existing_context("Le Père Goriot")
    assert ctx["nb_chapitres"] == 1
    assert "Rastignac" in ctx["personnages"]
    assert "ambition" in ctx["themes"]


# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------

def test_full_pipeline_two_chapters(writer, data_ch1, data_ch4, vault_tmp):
    litt = vault_tmp / "Littérature"

    for data, ch_num in [(data_ch1, 1), (data_ch4, 4)]:
        writer.write_chapter(data, ch_num)
        writer.update_index(data, ch_num)
        writer.update_personnages(data)
        writer.update_themes(data)
        writer.update_citations(data, ch_num)
        writer.write_auteur(data)
        writer.write_mouvement(data)
        writer.write_personnages_individuels(data, ch_num)
        writer.update_bibliotheque(data)

    assert (litt / "Livres" / "Le Père Goriot" / "Chapitres" / "Ch_01.md").exists()
    assert (litt / "Livres" / "Le Père Goriot" / "Chapitres" / "Ch_04.md").exists()
    assert (litt / "Livres" / "Le Père Goriot" / "00_Index.md").exists()
    assert (litt / "Auteurs" / "Honoré de Balzac.md").exists()
    assert (litt / "Mouvements" / "Réalisme.md").exists()

    bib = (litt / "00_Bibliotheque.md").read_text()
    assert "[[Le Père Goriot]]" in bib

    ctx = writer.get_existing_context("Le Père Goriot")
    assert ctx["nb_chapitres"] == 2
