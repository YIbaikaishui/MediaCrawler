# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

from media_platform.douyin.core import DouYinCrawler
from media_platform.tieba.core import TieBaCrawler
from run_search_today_all_platforms import build_env, iter_tasks, sqlite_db_has_data


def test_sqlite_db_has_data_handles_missing_file(tmp_path: Path):
    assert sqlite_db_has_data(tmp_path / "missing.db") is False


def test_sqlite_db_has_data_detects_rows(tmp_path: Path):
    db_path = tmp_path / "sample.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO sample (value) VALUES ('x')")
    conn.commit()
    conn.close()

    assert sqlite_db_has_data(db_path) is True


def test_iter_tasks_only_keeps_empty_platforms(tmp_path: Path):
    non_empty_db = tmp_path / "bili_sqlite.db"
    conn = sqlite3.connect(non_empty_db)
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO sample (value) VALUES ('x')")
    conn.commit()
    conn.close()

    tasks = iter_tasks(
        ["bili", "dy", "wb"],
        only_empty_db=True,
        sqlite_dir=tmp_path,
    )

    assert [task.name for task in tasks] == ["dy", "wb"]


def test_build_env_can_disable_cdp(tmp_path: Path):
    env = build_env(tmp_path / "dy_sqlite.db", disable_cdp=True)

    assert env["SQLITE_DB_PATH"].endswith("dy_sqlite.db")
    assert env["MEDIA_CRAWLER_ENABLE_CDP_MODE"] == "false"
    assert env["MEDIA_CRAWLER_CDP_CONNECT_EXISTING"] == "false"


def test_douyin_manual_verification_title_detection():
    assert DouYinCrawler._needs_manual_verification("验证码中间页")
    assert not DouYinCrawler._needs_manual_verification("抖音")


def test_tieba_manual_verification_title_detection():
    assert TieBaCrawler._needs_manual_verification("百度安全验证")
    assert not TieBaCrawler._needs_manual_verification("百度贴吧")
