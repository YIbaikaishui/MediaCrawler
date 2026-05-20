from __future__ import annotations

from pathlib import Path
import csv

from run_ribao_social_crawl import (
    build_run_command,
    discover_csv_path,
    filter_csv_to_time_window,
    prepare_output_dir,
)
from tools.time_window import resolve_time_window


def test_prepare_output_dir_overwrites_same_day_directory(tmp_path: Path):
    output_dir = tmp_path / "20260517"
    output_dir.mkdir(parents=True)
    (output_dir / "old.txt").write_text("old", encoding="utf-8")

    prepare_output_dir(output_dir)

    assert output_dir.exists()
    assert list(output_dir.iterdir()) == []


def test_discover_csv_path_finds_export_file(tmp_path: Path):
    csv_dir = tmp_path / "xhs" / "csv"
    csv_dir.mkdir(parents=True)
    expected_path = csv_dir / "search_contents_2026-05-17.csv"
    expected_path.write_text("ok", encoding="utf-8")

    assert discover_csv_path(tmp_path, "xhs", "contents") == expected_path


def test_build_run_command_uses_csv_and_comment_flags(tmp_path: Path):
    command = build_run_command(
        platform="zhihu",
        keywords=("汶川地震", "地震评论"),
        save_data_path=tmp_path,
        login_type="qrcode",
        headless=False,
        max_comments_count=0,
        max_concurrency=3,
        get_sub_comment=False,
    )

    assert "--platform" in command
    assert "zhihu" in command
    assert "--save_data_option" in command
    assert "csv" in command
    assert "--get_comment" in command
    assert "true" in command


def test_resolve_time_window_uses_full_day_for_target_date():
    window = resolve_time_window(
        window_start=None,
        window_end=None,
        target_date="20260517",
    )

    assert window is not None
    assert window.start.isoformat().startswith("2026-05-17T00:00:00")
    assert window.end.isoformat().startswith("2026-05-18T00:00:00")


def test_filter_csv_to_time_window_keeps_recent_xhs_contents_and_matching_comments(tmp_path: Path):
    window = resolve_time_window(
        window_start="2026-05-17T00:00:00+08:00",
        window_end="2026-05-18T00:00:00+08:00",
        target_date=None,
    )
    assert window is not None

    contents_source = tmp_path / "search_contents_2026-05-17.csv"
    comments_source = tmp_path / "search_comments_2026-05-17.csv"
    contents_target = tmp_path / "xhs_contents.csv"
    comments_target = tmp_path / "xhs_comments.csv"

    with contents_source.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["note_id", "title", "time"])
        writer.writeheader()
        writer.writerow({"note_id": "n1", "title": "keep", "time": str(1778979600)})
        writer.writerow({"note_id": "n2", "title": "drop", "time": str(1778860800)})

    with comments_source.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["comment_id", "note_id", "create_time", "content"])
        writer.writeheader()
        writer.writerow({"comment_id": "c1", "note_id": "n1", "create_time": str(1778979700), "content": "keep"})
        writer.writerow({"comment_id": "c2", "note_id": "n2", "create_time": str(1778979700), "content": "drop by parent"})
        writer.writerow({"comment_id": "c3", "note_id": "n1", "create_time": str(1778860800), "content": "drop by time"})

    kept_ids = filter_csv_to_time_window(
        platform="xhs",
        item_type="contents",
        source_path=contents_source,
        destination_path=contents_target,
        window=window,
    )
    filter_csv_to_time_window(
        platform="xhs",
        item_type="comments",
        source_path=comments_source,
        destination_path=comments_target,
        window=window,
        allowed_parent_ids=kept_ids,
    )

    assert kept_ids == {"n1"}

    with contents_target.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["note_id"] for row in rows] == ["n1"]

    with comments_target.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["comment_id"] for row in rows] == ["c1"]


def test_filter_csv_to_time_window_keeps_recent_zhihu_contents(tmp_path: Path):
    window = resolve_time_window(
        window_start="2026-05-17T00:00:00+08:00",
        window_end="2026-05-18T00:00:00+08:00",
        target_date=None,
    )
    assert window is not None

    contents_source = tmp_path / "zhihu_contents_raw.csv"
    contents_target = tmp_path / "zhihu_contents.csv"
    with contents_source.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["content_id", "title", "created_time"])
        writer.writeheader()
        writer.writerow({"content_id": "z1", "title": "keep", "created_time": "1778979600"})
        writer.writerow({"content_id": "z2", "title": "drop", "created_time": "1778860800"})

    kept_ids = filter_csv_to_time_window(
        platform="zhihu",
        item_type="contents",
        source_path=contents_source,
        destination_path=contents_target,
        window=window,
    )

    assert kept_ids == {"z1"}
    with contents_target.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["content_id"] for row in rows] == ["z1"]
