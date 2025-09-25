from pathlib import Path

from core import scanner


def test_list_images_raw(tmp_path: Path) -> None:
    """Проверяет фильтрацию файлов по расширениям."""
    (tmp_path / "img1.jpg").write_text("a")
    (tmp_path / "img2.png").write_text("b")
    (tmp_path / "note.txt").write_text("c")

    files = scanner.list_images_raw(tmp_path)
    names = [f.name for f in files]

    assert "img1.jpg" in names
    assert "img2.png" in names
    assert "note.txt" not in names


def test_scan_old_new(tmp_path: Path) -> None:
    """Проверяет сканирование папок OLD и NEW и возврат списков файлов."""
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()

    (old_dir / "a.jpg").write_text("1")
    (old_dir / "b.jpg").write_text("2")
    (new_dir / "x.jpg").write_text("3")
    (new_dir / "y.jpg").write_text("4")

    old, new, warnings = scanner.scan_old_new(old_dir, new_dir)

    assert len(old) == 2
    assert len(new) == 2
    assert warnings == []
