import hashlib
from pathlib import Path
from PIL import Image

from core.replacer import replace_one, replace_many


def _mk_img(path: Path, size=(16, 12), color=(200, 100, 50), fmt="JPEG"):
    img = Image.new("RGB", size, color)
    img.save(path, format=fmt)


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_replace_one_jpg_to_jpg(tmp_path: Path):
    old = tmp_path / "old.jpg"
    new = tmp_path / "new.jpg"
    _mk_img(old, size=(16, 12), color=(0, 255, 0), fmt="JPEG")
    _mk_img(new, size=(8, 8), color=(255, 0, 0), fmt="JPEG")

    before_hash = _md5(new)
    res = replace_one(old, new)
    after_hash = _md5(new)

    assert res.ok
    assert res.action in {"copy-bytes", "reencode->JPEG"}
    assert before_hash != after_hash  # содержимое реально поменялось
    with Image.open(new) as im:
        assert (im.format or "").upper() == "JPEG"


def test_replace_one_png_to_jpg(tmp_path: Path):
    old = tmp_path / "old.png"
    new = tmp_path / "new.jpg"
    _mk_img(old, size=(10, 10), color=(10, 20, 30), fmt="PNG")
    _mk_img(new, size=(5, 5), color=(200, 0, 0), fmt="JPEG")

    res = replace_one(old, new)  # auto: ориентируемся на расширение new (.jpg) => JPEG
    assert res.ok
    with Image.open(new) as im:
        assert (im.format or "").upper() == "JPEG"


def test_replace_one_force_png_even_if_new_is_jpg(tmp_path: Path):
    old = tmp_path / "old.jpg"
    new = tmp_path / "new.jpg"
    _mk_img(old, size=(7, 7), color=(1, 2, 3), fmt="JPEG")
    _mk_img(new, size=(8, 8), color=(4, 5, 6), fmt="JPEG")

    res = replace_one(old, new, force_format="png")
    assert res.ok
    # Имя осталось .jpg, но фактический формат PNG — допустимо
    with Image.open(new) as im:
        assert (im.format or "").upper() == "PNG"


def test_replace_many_dry_run(tmp_path: Path):
    old1 = tmp_path / "o1.jpg"; old2 = tmp_path / "o2.jpg"
    new1 = tmp_path / "n1.jpg"; new2 = tmp_path / "n2.jpg"
    for p in [old1, old2, new1, new2]:
        _mk_img(p, fmt="JPEG")

    res = replace_many([(old1, new1), (old2, new2)], dry_run=True)
    assert len(res) == 2
    assert all(r.ok and r.action == "dry-run" for r in res)
    # Файлы не трогали
    assert new1.stat().st_size > 0 and new2.stat().st_size > 0
