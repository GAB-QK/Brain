import sys
import pytest


def test_too_many_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "a.txt", "b.txt"])
    from input_handler import collect_raw_note
    with pytest.raises(SystemExit):
        collect_raw_note()


def test_unknown_extension(monkeypatch, tmp_path):
    fake_file = tmp_path / "document.pdf"
    fake_file.write_text("contenu")
    monkeypatch.setattr(sys, "argv", ["main.py", str(fake_file)])
    from input_handler import collect_raw_note
    with pytest.raises(SystemExit):
        collect_raw_note()


def test_audio_extension(monkeypatch, tmp_path):
    fake_file = tmp_path / "note.mp3"
    fake_file.write_bytes(b"audio data")
    monkeypatch.setattr(sys, "argv", ["main.py", str(fake_file)])
    from input_handler import collect_raw_note
    with pytest.raises(SystemExit):
        collect_raw_note()


def test_image_extension(monkeypatch, tmp_path):
    fake_file = tmp_path / "scan.jpg"
    fake_file.write_bytes(b"image data")
    monkeypatch.setattr(sys, "argv", ["main.py", str(fake_file)])
    from input_handler import collect_raw_note
    with pytest.raises(SystemExit):
        collect_raw_note()


def test_file_not_found(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "/nonexistent/path/note.txt"])
    from input_handler import collect_raw_note
    with pytest.raises(SystemExit):
        collect_raw_note()
