from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence, TextIO

from tools.time_window import TimeWindow, resolve_time_window, timestamp_in_window


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORMS = ("xhs", "zhihu")


@dataclass(frozen=True)
class PlatformExportResult:
    platform: str
    contents_csv: str
    comments_csv: str
    exit_code: int


@dataclass(frozen=True)
class RibaoSocialCrawlRequest:
    target_date: str
    output_dir: Path
    keywords: tuple[str, ...]
    platforms: tuple[str, ...] = DEFAULT_PLATFORMS
    window_start: str | None = None
    window_end: str | None = None
    login_type: str = "qrcode"
    headless: bool = False
    max_comments_count: int = 0
    max_concurrency: int = 3
    get_sub_comment: bool = False


@dataclass(frozen=True)
class RibaoSocialCrawlResult:
    success: bool
    exit_code: int
    manifest_path: Path
    crawl_log_path: Path
    output_dir: Path
    platform_results: tuple[PlatformExportResult, ...]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ribao social crawl for Zhihu and Xiaohongshu and normalize outputs into fixed CSV names.",
    )
    parser.add_argument("--date", required=True, help="Target date in YYYYMMDD format.")
    parser.add_argument(
        "--window-start",
        help="Optional ISO datetime lower bound. If omitted, --date is treated as a full-day window.",
    )
    parser.add_argument(
        "--window-end",
        help="Optional ISO datetime upper bound. If omitted, --date is treated as a full-day window.",
    )
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


def build_ribao_social_crawl_request(args: argparse.Namespace) -> RibaoSocialCrawlRequest:
    keywords = tuple(dict.fromkeys(keyword.strip() for keyword in args.keyword if keyword.strip()))
    return RibaoSocialCrawlRequest(
        target_date=args.date,
        output_dir=args.output_dir,
        keywords=keywords,
        platforms=tuple(args.platform or DEFAULT_PLATFORMS),
        window_start=args.window_start,
        window_end=args.window_end,
        login_type=args.login_type,
        headless=args.headless,
        max_comments_count=args.max_comments_count,
        max_concurrency=args.max_concurrency,
        get_sub_comment=args.get_sub_comment,
    )


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


def _build_env(window: TimeWindow | None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    if window is not None:
        env["MEDIA_CRAWLER_WINDOW_START"] = window.start.isoformat()
        env["MEDIA_CRAWLER_WINDOW_END"] = window.end.isoformat()
    return env


def _content_id_field(platform: str) -> str:
    if platform == "xhs":
        return "note_id"
    if platform == "zhihu":
        return "content_id"
    raise ValueError(f"Unsupported platform for time window filter: {platform}")


def _content_timestamp_field(platform: str) -> str:
    if platform == "xhs":
        return "time"
    if platform == "zhihu":
        return "created_time"
    raise ValueError(f"Unsupported platform for time window filter: {platform}")


def _comment_parent_field(platform: str) -> str:
    if platform == "xhs":
        return "note_id"
    if platform == "zhihu":
        return "content_id"
    raise ValueError(f"Unsupported platform for time window filter: {platform}")


def _comment_timestamp_field(platform: str) -> str:
    if platform == "xhs":
        return "create_time"
    if platform == "zhihu":
        return "publish_time"
    raise ValueError(f"Unsupported platform for time window filter: {platform}")


def _write_csv_rows(destination_path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with destination_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def filter_csv_to_time_window(
    *,
    platform: str,
    item_type: str,
    source_path: Path | None,
    destination_path: Path,
    window: TimeWindow | None,
    allowed_parent_ids: set[str] | None = None,
) -> set[str]:
    if source_path is None or not source_path.exists():
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text("", encoding="utf-8")
        return set()

    with source_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames:
        destination_path.write_text("", encoding="utf-8")
        return set()

    if window is None:
        _write_csv_rows(destination_path, fieldnames, rows)
        if item_type != "contents":
            return set()
        content_id_field = _content_id_field(platform)
        return {
            row.get(content_id_field, "").strip()
            for row in rows
            if row.get(content_id_field, "").strip()
        }

    filtered_rows: list[dict[str, str]] = []
    kept_ids: set[str] = set()
    if item_type == "contents":
        content_id_field = _content_id_field(platform)
        timestamp_field = _content_timestamp_field(platform)
        for row in rows:
            if not timestamp_in_window(window, row.get(timestamp_field)):
                continue
            filtered_rows.append(row)
            row_id = row.get(content_id_field, "").strip()
            if row_id:
                kept_ids.add(row_id)
        _write_csv_rows(destination_path, fieldnames, filtered_rows)
        return kept_ids

    parent_field = _comment_parent_field(platform)
    timestamp_field = _comment_timestamp_field(platform)
    parent_ids = allowed_parent_ids or set()
    for row in rows:
        parent_id = row.get(parent_field, "").strip()
        if parent_ids and parent_id not in parent_ids:
            continue
        if not timestamp_in_window(window, row.get(timestamp_field)):
            continue
        filtered_rows.append(row)
    _write_csv_rows(destination_path, fieldnames, filtered_rows)
    return set()


def _run_platform(
    *,
    platform: str,
    keywords: tuple[str, ...],
    output_dir: Path,
    log_file: TextIO,
    login_type: str,
    headless: bool,
    max_comments_count: int,
    max_concurrency: int,
    get_sub_comment: bool,
    window: TimeWindow | None,
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
        env=_build_env(window),
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
    kept_content_ids = filter_csv_to_time_window(
        platform=platform,
        item_type="contents",
        source_path=contents_source,
        destination_path=contents_target,
        window=window,
    )
    filter_csv_to_time_window(
        platform=platform,
        item_type="comments",
        source_path=comments_source,
        destination_path=comments_target,
        window=window,
        allowed_parent_ids=kept_content_ids,
    )

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
    window: TimeWindow | None,
) -> Path:
    manifest = {
        "target_date": target_date,
        "keywords": list(keywords),
        "platforms": list(platforms),
        "window_start": window.start.isoformat() if window else "",
        "window_end": window.end.isoformat() if window else "",
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
    return manifest_path


def run_ribao_social_crawl(request: RibaoSocialCrawlRequest) -> RibaoSocialCrawlResult:
    if not request.keywords:
        raise ValueError("At least one non-empty keyword is required.")

    window = resolve_time_window(
        window_start=request.window_start,
        window_end=request.window_end,
        target_date=request.target_date,
    )

    prepare_output_dir(request.output_dir)
    started_at = datetime.now()
    platform_results: list[PlatformExportResult] = []
    crawl_log_path = request.output_dir / "crawl.log"
    with crawl_log_path.open("w", encoding="utf-8", newline="\n") as log_file:
        for platform in request.platforms:
            platform_results.append(
                _run_platform(
                    platform=platform,
                    keywords=request.keywords,
                    output_dir=request.output_dir,
                    log_file=log_file,
                    login_type=request.login_type,
                    headless=request.headless,
                    max_comments_count=request.max_comments_count,
                    max_concurrency=request.max_concurrency,
                    get_sub_comment=request.get_sub_comment,
                    window=window,
                )
            )

    finished_at = datetime.now()
    success = all(result.exit_code == 0 for result in platform_results)
    manifest_path = _write_manifest(
        output_dir=request.output_dir,
        target_date=request.target_date,
        keywords=request.keywords,
        platforms=request.platforms,
        started_at=started_at,
        finished_at=finished_at,
        success=success,
        platform_results=platform_results,
        window=window,
    )

    staging_dir = request.output_dir / "_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    return RibaoSocialCrawlResult(
        success=success,
        exit_code=0 if success else 1,
        manifest_path=manifest_path,
        crawl_log_path=crawl_log_path,
        output_dir=request.output_dir,
        platform_results=tuple(platform_results),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    request = build_ribao_social_crawl_request(args)
    result = run_ribao_social_crawl(request)
    return result.exit_code


__all__ = [
    "DEFAULT_PLATFORMS",
    "PlatformExportResult",
    "RibaoSocialCrawlRequest",
    "RibaoSocialCrawlResult",
    "build_ribao_social_crawl_request",
    "build_run_command",
    "discover_csv_path",
    "filter_csv_to_time_window",
    "main",
    "parse_args",
    "prepare_output_dir",
    "run_ribao_social_crawl",
]
