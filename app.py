from pathlib import Path
from core.scanner import scan_old_new
from core.mapping import build_pairs, preview_pairs
from core.replacer import replace_many


def main():
    old_dir = Path(input("Введите путь к папке OLD: ").strip('"'))
    new_dir = Path(input("Введите путь к папке NEW (screenshots): ").strip('"'))

    old, new, scan_warnings = scan_old_new(old_dir, new_dir)
    pairs, map_warnings = build_pairs(old, new)

    print("\n--- Предпросмотр (первые 20) ---")
    for line in preview_pairs(pairs, limit=20):
        print(line)

    if scan_warnings or map_warnings:
        print("\n⚠️ Предупреждения:")
        for w in [*scan_warnings, *map_warnings]:
            print(" -", w)

    ans = input("\nПродолжить замену? [y/N]: ").strip().lower()
    if ans != "y":
        print("Отмена.")
        return

    force = input("Принудительный формат (enter/jpg/png): ").strip().lower() or None
    dry = input("Сделать dry-run? [y/N]: ").strip().lower() == "y"

    results = replace_many([(p.old, p.new) for p in pairs], force_format=force, dry_run=dry)

    print("\n--- Результат ---")
    ok_cnt = 0
    for r in results:
        status = "OK" if r.ok else f"ERR: {r.error}"
        print(f"{r.new.name} ← {r.old.name}: {r.action} [{status}]")
        if r.ok and r.action != "dry-run":
            ok_cnt += 1

    print(f"\nГотово. Успешно обработано: {ok_cnt}/{len(results)} (dry_run={dry})")


if __name__ == "__main__":
    main()
