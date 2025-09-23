from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from PIL import Image


@dataclass(frozen=True)
class ReplaceResult:
    old: Path
    new: Path
    action: str         # "copy-bytes" | "reencode->JPEG" | "reencode->PNG" | "dry-run"
    bytes_before: int
    bytes_after: int    # при dry-run == bytes_before
    ok: bool
    error: str | None = None


def _target_format_for(new_path: Path, force_format: Optional[str]) -> str:
    """
    Определяем формат назначения:
    - Если force_format задан: 'jpg'|'jpeg'|'png' -> 'JPEG'|'PNG'
    - Иначе ориентируемся на расширение файла new_path: .jpg/.jpeg -> 'JPEG', .png -> 'PNG'
    """
    if force_format:
        f = force_format.lower()
        if f in {"jpg", "jpeg"}:
            return "JPEG"
        if f == "png":
            return "PNG"
        raise ValueError(f"Неизвестный force_format: {force_format}")
    ext = new_path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "JPEG"
    if ext == ".png":
        return "PNG"
    # По умолчанию — JPEG (в Steam чаще jpg)
    return "JPEG"


def _write_atomic(dst_path: Path, write_fn) -> None:
    """
    Атомарная запись: создаём временный файл в той же директории и затем os.replace.
    write_fn(temp_path) должен записать финальные байты в temp_path.
    """
    dst_dir = dst_path.parent
    dst_dir.mkdir(parents=True, exist_ok=True)
    # расширение временного файла оставим как у dst, чтобы редакторы не путались
    with tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=dst_dir, suffix=dst_path.suffix + ".tmp"
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        write_fn(tmp_path)
        os.replace(tmp_path, dst_path)  # атомарная замена
    except Exception:
        # прибираем временный файл, если что-то пошло не так
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        finally:
            raise


def _copy_bytes_atomic(src: Path, dst: Path) -> None:
    def _do_write(tmp_path: Path) -> None:
        with src.open("rb") as rf, tmp_path.open("wb") as wf:
            shutil.copyfileobj(rf, wf, length=1024 * 1024)
    _write_atomic(dst, _do_write)


def _reencode_atomic(src: Path, dst: Path, fmt: str) -> None:
    """
    Перекодируем через Pillow в нужный формат.
    - Для JPEG конвертируем в RGB (без альфы).
    - Для PNG сохраняем альфу, если есть.
    """
    def _do_write(tmp_path: Path) -> None:
        with Image.open(src) as im:
            if fmt == "JPEG":
                # JPEG не поддерживает альфу; приводим к RGB
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.save(tmp_path, format="JPEG", quality=95, optimize=True)
            elif fmt == "PNG":
                # PNG: стараемся сохранить альфу; если нет — можно оставить RGB/L
                if im.mode in ("P", "LA"):
                    im = im.convert("RGBA")
                im.save(tmp_path, format="PNG", optimize=True)
            else:
                raise ValueError(f"Неподдерживаемый формат назначения: {fmt}")
    _write_atomic(dst, _do_write)


def replace_one(
    old_path: Path,
    new_path: Path,
    *,
    force_format: Optional[str] = None,
    dry_run: bool = False,
) -> ReplaceResult:
    """
    Подменяет содержимое new_path картинкой из old_path (имя new_path сохраняем).
    Поведение:
      - Если force_format=None: ориентируемся на расширение new_path (.jpg/.png).
      - Если force_format задан ('jpg'|'png'): перекодируем вне зависимости от расширения.
      - Если формат old совпадает с целевым, можно копировать байты без перекодирования.
    Атомарная запись через временный файл.

    ВАЖНО: имя файла (и его расширение) НЕ меняем.
    """
    bytes_before = new_path.stat().st_size if new_path.exists() else 0

    if dry_run:
        return ReplaceResult(
            old=old_path,
            new=new_path,
            action="dry-run",
            bytes_before=bytes_before,
            bytes_after=bytes_before,
            ok=True,
            error=None,
        )

    if not old_path.exists():
        return ReplaceResult(old_path, new_path, "dry-run", bytes_before, bytes_before, False, "OLD не найден")
    if not new_path.exists():
        return ReplaceResult(old_path, new_path, "dry-run", bytes_before, bytes_before, False, "NEW не найден")

    try:
        target_fmt = _target_format_for(new_path, force_format)
        # Определим формат источника
        src_fmt = None
        try:
            with Image.open(old_path) as im:
                src_fmt = (im.format or "").upper()
        except Exception:
            # Если Pillow не смог прочитать — копнём как есть, возможно это валидный jpeg/png без EXIF
            # но безопаснее всё-таки попытаться перекодировать позже
            pass

        if src_fmt == target_fmt and force_format is None:
            # Совпадает целевой формат и исходник — можно копировать байты
            _copy_bytes_atomic(old_path, new_path)
            action = "copy-bytes"
        else:
            # Перекодируем в нужный формат (или принудительный)
            _reencode_atomic(old_path, new_path, target_fmt)
            action = f"reencode->{target_fmt}"

        bytes_after = new_path.stat().st_size if new_path.exists() else 0
        return ReplaceResult(
            old=old_path,
            new=new_path,
            action=action,
            bytes_before=bytes_before,
            bytes_after=bytes_after,
            ok=True,
            error=None,
        )
    except Exception as e:
        return ReplaceResult(
            old=old_path,
            new=new_path,
            action="error",
            bytes_before=bytes_before,
            bytes_after=bytes_before,
            ok=False,
            error=str(e),
        )


def replace_many(
    pairs: Iterable[tuple[Path, Path]],
    *,
    force_format: Optional[str] = None,
    dry_run: bool = False,
) -> List[ReplaceResult]:
    """
    Применяет replace_one ко всем парам (old, new) и возвращает список результатов.
    """
    results: List[ReplaceResult] = []
    for old_p, new_p in pairs:
        res = replace_one(old_p, new_p, force_format=force_format, dry_run=dry_run)
        results.append(res)
    return results
