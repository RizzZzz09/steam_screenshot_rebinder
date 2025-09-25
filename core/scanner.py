from pathlib import Path


def list_images_raw(dir_path: Path, exts: tuple[str, ...] = (".jpg", ".png")) -> list[Path]:
    """Возвращает список файлов изображений из указанной папки.

    Файлы выбираются в порядке, в котором их отдаёт ОС (без сортировки).

    Args:
        dir_path: Путь к директории.
        exts: Допустимые расширения файлов.

    Returns:
        list[Path]: Список путей к найденным файлам.

    Raises:
        FileNotFoundError: Если директория не существует.
        NotADirectoryError: Если путь не является директорией.
    """
    if not dir_path.exists():
        raise FileNotFoundError(f"Директория не найдена: {dir_path}")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"Указанный путь не является директорией: {dir_path}")

    files: list[Path] = []
    for entry in dir_path.iterdir():
        if entry.is_file() and entry.suffix.lower() in exts:
            files.append(entry)
    return files


def scan_old_new(old_dir: Path, new_dir: Path, n: int | None = None) -> tuple[list[Path], list[Path], list[str]]:
    """Сканирует директории OLD и NEW и подготавливает списки файлов.

    Поведение:
        - Берёт список файлов в порядке ОС (без сортировки).
        - Ограничивает количество файлов параметром n.
        - Если файлов в NEW меньше, чем в OLD, урезает до минимума и добавляет предупреждение.

    Args:
        old_dir: Путь к директории с исходными файлами (OLD).
        new_dir: Путь к директории с файлами-назначениями (NEW).
        n: Максимальное количество файлов (по умолчанию равно количеству в OLD).

    Returns:
        tuple[list[Path], list[Path], list[str]]:
            - Список файлов из OLD.
            - Список файлов из NEW.
            - Список предупреждений.
    """
    warnings: list[str] = []

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
            f"Файлов в NEW меньше ({len(new_files)}) чем в OLD ({len(old_files)}). "
            f"Будет использовано {len(new_files)} пар."
        )
        n = len(new_files)

    return old_files[:n], new_files[:n], warnings
