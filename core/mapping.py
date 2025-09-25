from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image


@dataclass(frozen=True)
class ImageInfo:
    """Информация об изображении.

    Attributes:
        path: Путь к файлу изображения.
        width: Ширина изображения в пикселях.
        height: Высота изображения в пикселях.
        mode: Цветовой режим (например, "RGB").
        fmt: Формат файла (например, "PNG").
        size_bytes: Размер файла в байтах.
    """

    path: Path
    width: int
    height: int
    mode: str
    fmt: str
    size_bytes: int


@dataclass(frozen=True)
class Pair:
    """Пара файлов для замены содержимого.

    Attributes:
        old: Источник (контент берётся отсюда).
        new: Приёмник (имя файла сохраняется).
    """

    old: Path
    new: Path


def get_image_info(p: Path) -> ImageInfo:
    """Читает базовую информацию об изображении.

    Args:
        p: Путь к изображению.

    Returns:
        ImageInfo: Информация об изображении.
    """
    with Image.open(p) as im:
        im.load()
        fmt = (im.format or "").upper()
        return ImageInfo(
            path=p,
            width=int(im.width),
            height=int(im.height),
            mode=str(im.mode),
            fmt=fmt,
            size_bytes=p.stat().st_size,
        )


def build_pairs(
        old_files: list[Path],
        new_files: list[Path],
        n: int | None = None,
        strict_equal: bool = False,
) -> tuple[list[Pair], list[str]]:
    """Формирует список пар файлов для замены.

    Args:
        old_files: Список файлов-источников.
        new_files: Список файлов-приёмников.
        n: Максимальное количество пар. По умолчанию берётся минимальное
           из двух списков.
        strict_equal: Если True — требует равное количество файлов.

    Returns:
        tuple[list[Pair], list[str]]: (список пар, список предупреждений).

    Raises:
        ValueError: Если strict_equal=True и количество файлов не совпадает.
    """
    warnings: list[str] = []

    if n is None:
        n = min(len(old_files), len(new_files))

    if strict_equal and (len(old_files) != len(new_files)):
        raise ValueError(
            f"Количество файлов не совпадает: OLD={len(old_files)} vs NEW={len(new_files)}"
        )

    if len(old_files) != len(new_files):
        warnings.append(
            f"Будет использовано пар: {n} (OLD={len(old_files)}, NEW={len(new_files)})"
        )

    if len(old_files) < n or len(new_files) < n:
        warnings.append(
            f"Ограничение по количеству: {n} (OLD={len(old_files)}, NEW={len(new_files)})"
        )

    pairs = [Pair(old=o, new=nw) for o, nw in zip(old_files[:n], new_files[:n])]
    return pairs, warnings


def preview_pairs(
        pairs: Iterable[Pair],
        *,
        limit: int | None = 20,
) -> list[str]:
    """Готовит предпросмотр пар файлов.

    Показывает размеры и форматы изображений для первых `limit` записей.

    Args:
        pairs: Итератор пар файлов.
        limit: Ограничение на количество строк предпросмотра.

    Returns:
        list[str]: Список строк предпросмотра.
    """
    lines: list[str] = []
    count = 0
    for pr in pairs:
        try:
            old_info = get_image_info(pr.old)
            new_info = get_image_info(pr.new)
            line = (
                f"{pr.new.name} ← {pr.old.name} | "
                f"OLD: {old_info.width}x{old_info.height} {old_info.fmt}, "
                f"NEW: {new_info.width}x{new_info.height} {new_info.fmt}"
            )
        except Exception as e:
            line = f"{pr.new.name} ← {pr.old.name} | ⚠️ ошибка чтения: {e}"

        lines.append(line)
        count += 1
        if limit is not None and count >= limit:
            break
    return lines


def probe_conversion_warnings(
        pairs: Iterable[Pair],
        *,
        force_format: str | None = None,
) -> list[str]:
    """Проверяет возможную перекодировку изображений.

    Args:
        pairs: Итератор пар файлов.
        force_format: Принудительный формат ("jpg" или "png").
            Если None — определяется по расширению файла-приёмника.

    Returns:
        list[str]: Список предупреждений.
    """
    warns: list[str] = []
    ff = (force_format or "").lower()
    for pr in pairs:
        try:
            old_info = get_image_info(pr.old)
            new_ext = pr.new.suffix.lower()
            if ff in {"jpg", "jpeg"}:
                if old_info.fmt != "JPEG":
                    warns.append(
                        f"{pr.new.name}: принудительно JPEG (OLD был {old_info.fmt or '?'})"
                    )
            elif ff == "png":
                if old_info.fmt != "PNG":
                    warns.append(
                        f"{pr.new.name}: принудительно PNG (OLD был {old_info.fmt or '?'})"
                    )
            else:
                if new_ext in {".jpg", ".jpeg"} and old_info.fmt != "JPEG":
                    warns.append(
                        f"{pr.new.name}: будет JPEG (OLD был {old_info.fmt or '?'})"
                    )
                if new_ext == ".png" and old_info.fmt != "PNG":
                    warns.append(
                        f"{pr.new.name}: будет PNG (OLD был {old_info.fmt or '?'})"
                    )
        except Exception as e:
            warns.append(f"{pr.new.name}: ⚠️ ошибка чтения для проверки формата: {e}")
    return warns
