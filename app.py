from pathlib import Path
from core.scanner import scan_old_new
from core.mapping import build_pairs, preview_pairs, probe_conversion_warnings


def main():
    old_dir = Path(input("Введите путь к папке OLD: "))
    new_dir = Path(input("Введите путь к папке NEW: "))

    old, new, scan_warnings = scan_old_new(old_dir, new_dir)

    pairs, map_warnings = build_pairs(old, new)
    lines = preview_pairs(pairs, limit=20)

    print("\n--- Пары (предпросмотр, первые 20) ---")
    for line in lines:
        print(line)

    conv_warns = probe_conversion_warnings(pairs)
    all_warns = [*scan_warnings, *map_warnings, *conv_warns]

    if all_warns:
        print("\n⚠️ Предупреждения:")
        for w in all_warns:
            print(" -", w)

    print(f"\nИтого пар: {len(pairs)}")


if __name__ == "__main__":
    main()
