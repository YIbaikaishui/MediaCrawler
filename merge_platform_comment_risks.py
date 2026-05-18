from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from analyze_platform_comment_risks import DEFAULT_CSV_EXPORT_DIR, PLATFORM_CONFIGS
from csv_export_columns import canonicalize_fieldnames, read_csv_rows, write_csv_rows
from csv_export_naming import DEFAULT_MERGED_RISK_CSV_NAME


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_PATH = DEFAULT_CSV_EXPORT_DIR / DEFAULT_MERGED_RISK_CSV_NAME
TRUTHY_VALUES = {"1", "true", "yes", "y", "是"}


@dataclass(frozen=True)
class MergeResult:
    merged_csv_path: Path
    source_file_count: int
    row_count: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge per-platform comment risk CSV files into a single CSV.",
    )
    parser.add_argument(
        "--csv-root",
        type=Path,
        default=DEFAULT_CSV_EXPORT_DIR,
        help="Directory containing per-platform comment risk CSV files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the merged CSV file to.",
    )
    return parser.parse_args(argv)


def is_truthy(value: str) -> bool:
    return value.strip().lower() in TRUTHY_VALUES


def discover_output_paths(csv_root: Path) -> list[Path]:
    output_paths: list[Path] = []
    for config in PLATFORM_CONFIGS.values():
        for directory_name in (config.directory_name, config.legacy_directory_name):
            for file_name in (config.output_csv_name, config.legacy_output_csv_name):
                if not directory_name or not file_name:
                    continue
                candidate = csv_root / directory_name / file_name
                if candidate.exists() and candidate not in output_paths:
                    output_paths.append(candidate)
    return output_paths


def validate_fieldnames(current_path: Path, current_fieldnames: list[str], expected_fieldnames: list[str]) -> None:
    if current_fieldnames != expected_fieldnames:
        raise ValueError(
            f"CSV header mismatch in {current_path}. "
            f"Expected {expected_fieldnames}, got {current_fieldnames}."
        )


def merge_platform_outputs(csv_root: Path, output_path: Path | None = None) -> MergeResult:
    source_paths = discover_output_paths(csv_root)
    if not source_paths:
        raise FileNotFoundError(f"No platform comment risk CSV files found under: {csv_root}")

    merged_rows: list[dict[str, str]] = []
    expected_fieldnames: list[str] | None = None
    for source_path in source_paths:
        with source_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            current_fieldnames = canonicalize_fieldnames(list(reader.fieldnames or []), "comment_risk_analysis")
            if expected_fieldnames is None:
                expected_fieldnames = current_fieldnames
            else:
                validate_fieldnames(source_path, current_fieldnames, expected_fieldnames)

            for row in read_csv_rows(source_path, "comment_risk_analysis"):
                if is_truthy(row.get("is_problematic", "")):
                    merged_rows.append(dict(row))

    if expected_fieldnames is None:
        raise ValueError("Could not determine CSV headers from source files.")

    final_output_path = output_path or (csv_root / DEFAULT_MERGED_RISK_CSV_NAME)
    write_csv_rows(final_output_path, "merged_comment_risk_analysis", expected_fieldnames, merged_rows)

    return MergeResult(
        merged_csv_path=final_output_path,
        source_file_count=len(source_paths),
        row_count=len(merged_rows),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = merge_platform_outputs(args.csv_root, args.output)
    except FileNotFoundError as err:
        print(f"[WARN] {err}")
        return 0

    print(
        f"[DONE] merged {result.source_file_count} file(s), "
        f"{result.row_count} row(s) -> {result.merged_csv_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
