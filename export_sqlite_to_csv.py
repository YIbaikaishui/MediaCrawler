from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from csv_export_columns import translate_fieldnames
from csv_export_naming import get_export_csv_name, get_export_directory_name

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_DIR = ROOT_DIR / "database" / "platform_sqlite"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "database" / "csv_export"


@dataclass(frozen=True)
class ExportResult:
    db_path: Path
    table_name: str
    csv_path: Path
    row_count: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export MediaCrawler sqlite databases to CSV files.",
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=DEFAULT_DB_DIR,
        help="Directory containing sqlite database files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write CSV files to.",
    )
    parser.add_argument(
        "--db",
        nargs="+",
        help="Optional database file names or stems to export, for example xhs_sqlite.db or xhs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be exported without writing files.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Also export empty tables. By default empty tables are skipped.",
    )
    return parser.parse_args(argv)


def resolve_db_paths(db_dir: Path, selected: list[str] | None) -> list[Path]:
    if selected:
        resolved: list[Path] = []
        for item in selected:
            candidate = Path(item)
            direct = db_dir / candidate.name
            if candidate.suffix.lower() == ".db" and direct.exists():
                resolved.append(direct)
                continue

            stem = candidate.stem if candidate.suffix else item
            for name in (f"{stem}_sqlite.db", f"{stem}.db", f"{stem}.sqlite"):
                matched = db_dir / name
                if matched.exists():
                    resolved.append(matched)
                    break
            else:
                if candidate.exists():
                    resolved.append(candidate)
                    continue
                raise FileNotFoundError(f"Database not found: {item}")
            continue
        return resolved

    return sorted(db_dir.glob("*.db"))


def list_user_tables(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [row[0] for row in cursor.fetchall()]


def export_table(
    conn: sqlite3.Connection,
    db_path: Path,
    table_name: str,
    output_dir: Path,
    dry_run: bool,
    include_empty: bool,
) -> ExportResult | None:
    safe_db_name = db_path.stem
    table_dir = output_dir / get_export_directory_name(safe_db_name)
    csv_path = table_dir / get_export_csv_name(safe_db_name, table_name)

    row_cursor = conn.execute(f'SELECT * FROM "{table_name}"')
    columns = [description[0] for description in row_cursor.description or []]
    rows = row_cursor.fetchall()
    row_count = len(rows)

    if row_count == 0 and not include_empty:
        if dry_run:
            print(f"[SKIP] {db_path.name} -> {csv_path} (0 rows)")
        return None

    if dry_run:
        print(f"[DRY RUN] {db_path.name} -> {csv_path} ({row_count} rows)")
        return ExportResult(db_path=db_path, table_name=table_name, csv_path=csv_path, row_count=row_count)

    table_dir.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(translate_fieldnames(columns, table_name))
        writer.writerows(rows)

    return ExportResult(db_path=db_path, table_name=table_name, csv_path=csv_path, row_count=row_count)


def export_database(
    db_path: Path,
    output_dir: Path,
    dry_run: bool,
    include_empty: bool = False,
) -> list[ExportResult]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        tables = list_user_tables(conn)
        results: list[ExportResult] = []
        for table_name in tables:
            result = export_table(
                conn,
                db_path,
                table_name,
                output_dir,
                dry_run,
                include_empty=include_empty,
            )
            if result is not None:
                results.append(result)
        return results
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    db_dir: Path = args.db_dir
    output_dir: Path = args.output_dir

    if not db_dir.exists():
        print(f"[ERROR] Database directory not found: {db_dir}")
        return 1

    db_paths = resolve_db_paths(db_dir, args.db)
    if not db_paths:
        print(f"[WARN] No sqlite databases found in: {db_dir}")
        return 0

    total_tables = 0
    total_rows = 0
    for db_path in db_paths:
        print(f"[SCAN] {db_path}")
        results = export_database(
            db_path,
            output_dir,
            args.dry_run,
            include_empty=args.include_empty,
        )
        if not results:
            print(f"[WARN] No tables exported from {db_path.name}")
            continue

        for result in results:
            total_tables += 1
            total_rows += result.row_count
            print(f"[OK] {result.table_name} -> {result.csv_path} ({result.row_count} rows)")

    print(f"[DONE] exported {total_tables} table(s), {total_rows} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
