from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image


@dataclass(frozen=True)
class ReplaceResult:
    """Результат замены содержимого файла.

    Attributes:
        old: Путь к исходному файлу.
        new: Путь к файлу-назначению.
        action: Действие ("copy-bytes", "reencode->JPEG", "reencode->PNG", "dry-run", "error").
        bytes_before: Размер файла до замены.
        bytes_after: Размер файла после замены (при dry-run = bytes_before).
        ok: Признак успешного завершения операции.
        error: Текст ошибки (если ok=False).
    """

    old: Path
    new: Path
    action: str
    bytes_before: int
    bytes_after: int
    ok: bool
    error: str | None = None


def _target_format_for(new_path: Path, force_format: str | None) -> str:
    """Определяет целевой формат файла.

    Args:
        new_path: Путь к файлу-назначению.
        force_format: Принудительный формат ("jpg" | "jpeg" | "png").

    Returns:
        str: Целевой формат ("JPEG" или "PNG").

    Raises:
        ValueError: Если передан неподдерживаемый force_format.
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
    # По умолчанию — JPEG (в Steam чаще встречается JPEG)
    return "JPEG"


def _write_atomic(dst_path: Path, write_fn) -> None:
    """Атомарная запись в файл.

    Создаёт временный файл в директории назначения и заменяет его целевым файлом.

    Args:
        dst_path: Путь к целевому файлу.
        write_fn: Функция записи, принимающая путь к временному файлу.
    """
    dst_dir = dst_path.parent
    dst_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=dst_dir, suffix=dst_path.suffix + ".tmp"
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        write_fn(tmp_path)
        os.replace(tmp_path, dst_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _copy_bytes_atomic(src: Path, dst: Path) -> None:
    """Копирует файл побайтово с атомарной заменой."""

    def _do_write(tmp_path: Path) -> None:
        with src.open("rb") as rf, tmp_path.open("wb") as wf:
            shutil.copyfileobj(rf, wf, length=1024 * 1024)

    _write_atomic(dst, _do_write)


def _reencode_atomic(src: Path, dst: Path, fmt: str) -> None:
    """Перекодирует изображение в указанный формат.

    Args:
        src: Путь к исходному файлу.
        dst: Путь к файлу-назначению.
        fmt: Целевой формат ("JPEG" или "PNG").

    Raises:
        ValueError: Если указан неподдерживаемый формат.
    """

    def _do_write(tmp_path: Path) -> None:
        with Image.open(src) as im:
            if fmt == "JPEG":
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.save(tmp_path, format="JPEG", quality=95, optimize=True)
            elif fmt == "PNG":
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
        force_format: str | None = None,
        dry_run: bool = False,
) -> ReplaceResult:
    """Заменяет содержимое одного файла изображением из другого.

    Args:
        old_path: Путь к исходному файлу.
        new_path: Путь к файлу-назначению (имя сохраняется).
        force_format: Принудительный формат ("jpg" | "png").
        dry_run: Если True, операция только симулируется.

    Returns:
        ReplaceResult: Результат операции.
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
        )

    if not old_path.exists():
        return ReplaceResult(old_path, new_path, "dry-run", bytes_before, bytes_before, False, "OLD не найден")
    if not new_path.exists():
        return ReplaceResult(old_path, new_path, "dry-run", bytes_before, bytes_before, False, "NEW не найден")

    try:
        target_fmt = _target_format_for(new_path, force_format)

        src_fmt: str | None = None
        try:
            with Image.open(old_path) as im:
                src_fmt = (im.format or "").upper()
        except Exception:
            # Если Pillow не смог прочитать файл — пробуем перекодировать
            pass

        if src_fmt == target_fmt and force_format is None:
            _copy_bytes_atomic(old_path, new_path)
            action = "copy-bytes"
        else:
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
        force_format: str | None = None,
        dry_run: bool = False,
) -> list[ReplaceResult]:
    """Применяет replace_one ко всем парам файлов.

    Args:
        pairs: Итератор пар (old, new).
        force_format: Принудительный формат ("jpg" | "png").
        dry_run: Если True, операции только симулируются.

    Returns:
        list[ReplaceResult]: Список результатов.
    """
    results: list[ReplaceResult] = []
    for old_p, new_p in pairs:
        res = replace_one(old_p, new_p, force_format=force_format, dry_run=dry_run)
        results.append(res)
    return results
