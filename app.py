from pathlib import Path
from core.scanner import scan_old_new


def main():
    old_dir = Path(input("Введите путь к папке OLD: "))
    new_dir = Path(input("Введите путь к папке NEW: "))

    old, new, warnings = scan_old_new(old_dir, new_dir)

    print("\n--- Найдено ---")
    for o, n in zip(old, new):
        print(f"{n.name} ← {o.name}")

    if warnings:
        print("\n⚠️ Предупреждения:")
        for w in warnings:
            print(" -", w)


if __name__ == "__main__":
    main()
