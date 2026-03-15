from unittest.mock import patch
from claude_api import _strip_code_fences, IA_LEVEL_INSTRUCTIONS


# ---------------------------------------------------------------------------
# _strip_code_fences()
# ---------------------------------------------------------------------------

def test_strip_code_fences_no_fences():
    text = '{"titre": "Test"}'
    assert _strip_code_fences(text) == text


def test_strip_code_fences_with_json_fence():
    text = '```json\n{"titre": "Test"}\n```'
    result = _strip_code_fences(text)
    assert result == '{"titre": "Test"}'


def test_strip_code_fences_with_plain_fence():
    text = '```\n{"titre": "Test"}\n```'
    result = _strip_code_fences(text)
    assert result == '{"titre": "Test"}'


# ---------------------------------------------------------------------------
# extract_title()
# ---------------------------------------------------------------------------

def test_extract_title_returns_empty_on_error():
    from claude_api import extract_title
    with patch("claude_api.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("API error")
        result = extract_title("Une note quelconque")
        assert result == {}


# ---------------------------------------------------------------------------
# IA_LEVEL_INSTRUCTIONS
# ---------------------------------------------------------------------------

def test_ia_level_instructions_all_present():
    assert set(IA_LEVEL_INSTRUCTIONS.keys()) == {1, 2, 3, 4, 5}
    for level, instruction in IA_LEVEL_INSTRUCTIONS.items():
        assert isinstance(instruction, str)
        assert len(instruction) > 0
