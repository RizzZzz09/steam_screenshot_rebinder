from pathlib import Path

from core import scanner


def test_ignore_thumbnails_subdir(tmp_path: Path) -> None:
    """Проверяет, что подпапка thumbnails игнорируется при сканировании."""
    screenshots = tmp_path / "screenshots"
    thumbnails = screenshots / "thumbnails"
    screenshots.mkdir()
    thumbnails.mkdir()

    (screenshots / "shot1.jpg").write_text("x")
    (thumbnails / "thumb1.jpg").write_text("y")

    files = scanner.list_images_raw(screenshots)
    names = [p.name for p in files]

    assert "shot1.jpg" in names
    # Подпапки игнорируются (non-recursive)
    assert "thumb1.jpg" not in names
