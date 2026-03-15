# Tests

## Lancer les tests

```bash
pip install pytest
pytest tests/ -v                              # tous les tests
pytest tests/test_obsidian_writer.py -v       # writer seulement
pytest tests/test_markdown_builder.py -v      # markdown builder seulement
pytest tests/test_claude_api.py -v            # claude api seulement
pytest tests/test_input_handler.py -v         # input handler seulement
pytest tests/ -v --tb=short                   # traceback court
```

## Structure

| Fichier | Ce qui est testé |
|---------|-----------------|
| `test_obsidian_writer.py` | Pipeline complet Obsidian : chapitres, index, auteurs, mouvements, personnages, thèmes, citations, bibliothèque, contexte existant |
| `test_markdown_builder.py` | Fonctions `fm()` et `build_chapter_md()` : tags sans `#`, wikilinks quotés, dates non quotées, `aliases` toujours présent |
| `test_claude_api.py` | `_strip_code_fences()`, `extract_title()` (mock API), `IA_LEVEL_INSTRUCTIONS` |
| `test_input_handler.py` | Validation CLI : trop d'args, extension inconnue, audio, image, fichier introuvable |

## Isolation

Chaque test utilisant le vault reçoit un répertoire temporaire via la fixture `vault_tmp` (pytest `tmp_path`). Les constantes de `config.py` et `writers/obsidian_writer.py` sont monkeypatché pour pointer vers ce répertoire — aucun fichier n'est créé dans le vault réel.

Les variables d'environnement `VAULT_PATH` et `ANTHROPIC_API_KEY` sont initialisées à des valeurs fictives dans `conftest.py` avant tout import projet, évitant le `sys.exit(1)` de `config.py`.
