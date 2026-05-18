from __future__ import annotations

from pathlib import Path

from run_ribao_social_crawl import (
    build_run_command,
    discover_csv_path,
    prepare_output_dir,
)


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
