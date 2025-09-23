from pathlib import Path
from typing import List


def list_images_raw(dir_path: Path, exts: tuple[str, ...] = (".jpg", ".png")) -> List[Path]:
    """
    Читает файлы из указанной папки в порядке ОС (без сортировки).
    Возвращает список путей к файлам, которые имеют разрешения exts.
    """
    if not dir_path.exists():
        raise FileNotFoundError(f"Папка {dir_path} не найдена")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"{dir_path} не является папкой")

    files: List[Path] = []
    for entry in dir_path.iterdir():  # порядок как отдаёт ОС
        if entry.is_file() and entry.suffix.lower() in exts:
            files.append(entry)
    return files


def scan_old_new(old_dir: Path, new_dir: Path, n: int | None = None) -> tuple[List[Path], List[Path], List[str]]:
    """
    Сканирует две папки (OLD и NEW).
    - Берёт список файлов как есть (без сортировки).
    - Ограничивает количество по n (по умолчанию n = len(old)).
    - Если файлов в new меньше, чем в old → урезаем до минимума и пишем предупреждение.

    Возвращает:
    (список OLD, список NEW, список предупреждений)
    """
    warnings: List[str] = []

    old_files = list_images_raw(old_dir)
    new_files = list_images_raw(new_dir)

    if not old_files:
        warnings.append("Папка OLD пуста")
    if not new_files:
        warnings.append("Папка NEW пуста")

    if n is None:
        n = len(old_files)

    if len(new_files) < n:
        warnings.append(
            f"В NEW меньше файлов ({len(new_files)}) чем в OLD ({len(old_files)}). "
            f"Будет использовано {len(new_files)} пар."
        )
        n = len(new_files)

    old_limited = old_files[:n]
    new_limited = new_files[:n]

    return old_limited, new_limited, warnings
