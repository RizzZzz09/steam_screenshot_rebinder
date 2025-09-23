from pathlib import Path
from PIL import Image
from core.mapping import build_pairs, get_image_info


def _make_img(path: Path, size=(16, 16), color=(128, 128, 128), fmt="JPEG"):
    img = Image.new("RGB", size, color)
    img.save(path, format=fmt)


def test_build_pairs_counts(tmp_path: Path):
    old_dir = tmp_path / "old"; old_dir.mkdir()
    new_dir = tmp_path / "new"; new_dir.mkdir()

    _make_img(old_dir / "o1.jpg", fmt="JPEG")
    _make_img(old_dir / "o2.jpg", fmt="JPEG")
    _make_img(new_dir / "n1.jpg", fmt="JPEG")

    pairs, warns = build_pairs(
        [*(old_dir.iterdir())],
        [*(new_dir.iterdir())],
        n=None,
        strict_equal=False,
    )
    assert len(pairs) == 1
    assert any("Будет использовано пар" in w for w in warns)


def test_preview_pairs_and_info(tmp_path: Path):
    old = tmp_path / "old.jpg"
    new = tmp_path / "new.jpg"
    _make_img(old, size=(10, 12), fmt="JPEG")
    _make_img(new, size=(8, 8), fmt="JPEG")

    from core.mapping import Pair, preview_pairs
    lines = preview_pairs([Pair(old=old, new=new)], limit=5)
    assert len(lines) == 1
    assert "OLD: 10x12 JPEG" in lines[0]

    info = get_image_info(old)
    assert info.width == 10 and info.height == 12 and info.fmt == "JPEG"
