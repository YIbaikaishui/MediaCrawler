import csv
import sqlite3
from pathlib import Path

from export_sqlite_to_csv import export_database


def build_sample_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE filled (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("CREATE TABLE empty (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO filled (value) VALUES ('kept')")
    conn.commit()
    conn.close()


def test_export_database_skips_empty_tables_by_default(tmp_path: Path):
    db_path = tmp_path / "sample.db"
    output_dir = tmp_path / "csv"
    build_sample_db(db_path)

    results = export_database(db_path, output_dir, dry_run=False)

    assert [result.table_name for result in results] == ["filled"]
    assert (output_dir / "sample" / "filled.csv").exists()
    assert not (output_dir / "sample" / "empty.csv").exists()


def test_export_database_can_include_empty_tables(tmp_path: Path):
    db_path = tmp_path / "sample.db"
    output_dir = tmp_path / "csv"
    build_sample_db(db_path)

    results = export_database(db_path, output_dir, dry_run=False, include_empty=True)

    assert {result.table_name for result in results} == {"filled", "empty"}
    assert (output_dir / "sample" / "empty.csv").exists()


def test_export_database_uses_chinese_names_for_known_platform_tables(tmp_path: Path):
    db_path = tmp_path / "bili_sqlite.db"
    output_dir = tmp_path / "csv"

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE bilibili_video (id INTEGER PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO bilibili_video (title) VALUES ('示例视频')")
    conn.commit()
    conn.close()

    results = export_database(db_path, output_dir, dry_run=False)

    assert [result.table_name for result in results] == ["bilibili_video"]
    assert (output_dir / "B站数据" / "视频数据.csv").exists()
    with (output_dir / "B站数据" / "视频数据.csv").open("r", newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    assert header == ["编号", "标题"]
