from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_PLATFORMS = ("xhs", "zhihu")


@dataclass(frozen=True)
class PlatformExportResult:
    platform: str
    contents_csv: str
    comments_csv: str
    exit_code: int


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ribao social crawl for Zhihu and Xiaohongshu and normalize outputs into fixed CSV names.",
    )
    parser.add_argument("--date", required=True, help="Target date in YYYYMMDD format.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Final date directory, e.g. social_crawl/20260517",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        required=True,
        help="Search keyword. Repeat this flag for multiple keywords.",
    )
    parser.add_argument(
        "--platform",
        action="append",
        choices=sorted(DEFAULT_PLATFORMS),
        help="Platforms to run. Defaults to xhs + zhihu.",
    )
    parser.add_argument(
        "--login-type",
        default=os.environ.get("MEDIA_CRAWLER_LOGIN_TYPE", "qrcode"),
        help="MediaCrawler login type.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode.",
    )
    parser.add_argument(
        "--max-comments-count",
        type=int,
        default=0,
        help="Maximum first-level comments per post. 0 means all available.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=3,
        help="Maximum concurrent crawler workers.",
    )
    parser.add_argument(
        "--get-sub-comment",
        action="store_true",
        help="Also crawl second-level comments.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def prepare_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def discover_csv_path(
    staging_root: Path,
    platform: str,
    item_type: str,
) -> Path | None:
    csv_dir = staging_root / platform / "csv"
    if not csv_dir.exists():
        return None

    patterns = (
        f"search_{item_type}_*.csv",
        f"*_{item_type}_*.csv",
    )
    for pattern in patterns:
        matches = sorted(csv_dir.glob(pattern))
        if matches:
            return matches[-1]
    return None


def _build_platform_output_path(output_dir: Path, platform: str, item_type: str) -> Path:
    return output_dir / f"{platform}_{item_type}.csv"


def build_run_command(
    *,
    platform: str,
    keywords: tuple[str, ...],
    save_data_path: Path,
    login_type: str,
    headless: bool,
    max_comments_count: int,
    max_concurrency: int,
    get_sub_comment: bool,
) -> list[str]:
    return [
        sys.executable,
        "main.py",
        "--platform",
        platform,
        "--lt",
        login_type,
        "--type",
        "search",
        "--keywords",
        ",".join(keywords),
        "--save_data_option",
        "csv",
        "--save_data_path",
        str(save_data_path),
        "--get_comment",
        "true",
        "--get_sub_comment",
        "true" if get_sub_comment else "false",
        "--max_comments_count_singlenotes",
        str(max_comments_count),
        "--max_concurrency_num",
        str(max_concurrency),
        "--headless",
        "true" if headless else "false",
    ]


def _copy_or_create_empty_csv(source_path: Path | None, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path is None or not source_path.exists():
        destination_path.write_text("", encoding="utf-8")
        return
    shutil.copy2(source_path, destination_path)


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run_platform(
    *,
    platform: str,
    keywords: tuple[str, ...],
    output_dir: Path,
    log_file,
    login_type: str,
    headless: bool,
    max_comments_count: int,
    max_concurrency: int,
    get_sub_comment: bool,
) -> PlatformExportResult:
    staging_root = output_dir / "_staging" / platform
    staging_root.mkdir(parents=True, exist_ok=True)

    command = build_run_command(
        platform=platform,
        keywords=keywords,
        save_data_path=staging_root,
        login_type=login_type,
        headless=headless,
        max_comments_count=max_comments_count,
        max_concurrency=max_concurrency,
        get_sub_comment=get_sub_comment,
    )

    log_file.write(f"$ {subprocess.list2cmdline(command)}\n")
    log_file.flush()
    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
        env=_build_env(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log_file.write("\n")
    log_file.flush()

    contents_source = discover_csv_path(staging_root, platform, "contents")
    comments_source = discover_csv_path(staging_root, platform, "comments")
    contents_target = _build_platform_output_path(output_dir, platform, "contents")
    comments_target = _build_platform_output_path(output_dir, platform, "comments")
    _copy_or_create_empty_csv(contents_source, contents_target)
    _copy_or_create_empty_csv(comments_source, comments_target)

    return PlatformExportResult(
        platform=platform,
        contents_csv=str(contents_target),
        comments_csv=str(comments_target),
        exit_code=result.returncode,
    )


def _write_manifest(
    *,
    output_dir: Path,
    target_date: str,
    keywords: tuple[str, ...],
    platforms: tuple[str, ...],
    started_at: datetime,
    finished_at: datetime,
    success: bool,
    platform_results: list[PlatformExportResult],
) -> None:
    manifest = {
        "target_date": target_date,
        "keywords": list(keywords),
        "platforms": list(platforms),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "success": success,
        "files": {result.platform: asdict(result) for result in platform_results},
    }
    manifest_path = output_dir / "crawl_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir
    platforms = tuple(args.platform or DEFAULT_PLATFORMS)
    keywords = tuple(dict.fromkeys(keyword.strip() for keyword in args.keyword if keyword.strip()))
    if not keywords:
        raise ValueError("At least one non-empty keyword is required.")

    prepare_output_dir(output_dir)
    started_at = datetime.now()
    platform_results: list[PlatformExportResult] = []
    crawl_log_path = output_dir / "crawl.log"
    with crawl_log_path.open("w", encoding="utf-8", newline="\n") as log_file:
        for platform in platforms:
            platform_results.append(
                _run_platform(
                    platform=platform,
                    keywords=keywords,
                    output_dir=output_dir,
                    log_file=log_file,
                    login_type=args.login_type,
                    headless=args.headless,
                    max_comments_count=args.max_comments_count,
                    max_concurrency=args.max_concurrency,
                    get_sub_comment=args.get_sub_comment,
                )
            )

    finished_at = datetime.now()
    success = all(result.exit_code == 0 for result in platform_results)
    _write_manifest(
        output_dir=output_dir,
        target_date=args.date,
        keywords=keywords,
        platforms=platforms,
        started_at=started_at,
        finished_at=finished_at,
        success=success,
        platform_results=platform_results,
    )

    staging_dir = output_dir / "_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
