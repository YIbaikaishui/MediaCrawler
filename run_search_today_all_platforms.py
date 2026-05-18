from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parent
LOG_DIR = ROOT_DIR / "logs" / "search-runs"
SQLITE_DIR = ROOT_DIR / "database" / "platform_sqlite"

UV_BIN = os.environ.get("UV_BIN", "uv")
LOGIN_TYPE = "qrcode"
SAVE_DATA_OPTION = "sqlite"
GET_COMMENT = True
GET_SUB_COMMENT = True
HEADLESS = False
MAX_CONCURRENCY_NUM = 3
MAX_COMMENTS_COUNT = 0

PLATFORM_KEYWORDS: dict[str, str] = {
    "xhs": "特朗普访华",
    "dy": "特朗普访华",
    "ks": "特朗普访华",
    "bili": "特朗普访华",
    "wb": "特朗普访华",
    "tieba": "特朗普访华",
    "zhihu": "特朗普访华",
}


@dataclass(frozen=True)
class PlatformTask:
    name: str
    keywords: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run today's all-platform MediaCrawler search with per-platform sqlite files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    parser.add_argument(
        "--platform",
        nargs="+",
        choices=sorted(PLATFORM_KEYWORDS),
        help="Only run selected platforms.",
    )
    parser.add_argument(
        "--only-empty-db",
        action="store_true",
        help="Skip platforms whose sqlite database already contains rows.",
    )
    parser.add_argument(
        "--disable-cdp",
        action="store_true",
        help="Disable CDP mode and launch a normal visible browser window instead.",
    )
    return parser.parse_args(argv)


def sqlite_db_has_data(sqlite_db_path: Path) -> bool:
    if not sqlite_db_path.exists():
        return False

    conn = sqlite3.connect(sqlite_db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (table_name,) in tables:
            row_count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            if row_count > 0:
                return True
        return False
    finally:
        conn.close()


def iter_tasks(
    selected_platforms: list[str] | None,
    *,
    only_empty_db: bool,
    sqlite_dir: Path = SQLITE_DIR,
) -> list[PlatformTask]:
    if not selected_platforms:
        selected_platforms = list(PLATFORM_KEYWORDS)

    tasks: list[PlatformTask] = []
    for platform in selected_platforms:
        sqlite_db_path = sqlite_dir / f"{platform}_sqlite.db"
        if only_empty_db and sqlite_db_has_data(sqlite_db_path):
            print(f"[SKIP] {platform} already has data in {sqlite_db_path}")
            continue
        tasks.append(PlatformTask(name=platform, keywords=PLATFORM_KEYWORDS[platform]))
    return tasks


def build_env(sqlite_db_path: Path, *, disable_cdp: bool) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["SQLITE_DB_PATH"] = str(sqlite_db_path)
    if disable_cdp:
        env["MEDIA_CRAWLER_ENABLE_CDP_MODE"] = "false"
        env["MEDIA_CRAWLER_CDP_CONNECT_EXISTING"] = "false"
    return env


def bool_arg(value: bool) -> str:
    return "true" if value else "false"


def command_to_text(command: Iterable[str]) -> str:
    return subprocess.list2cmdline(list(command))


def run_command(
    command: list[str],
    *,
    log_path: Path,
    env: dict[str, str],
    dry_run: bool,
) -> int:
    command_text = command_to_text(command)
    if dry_run:
        print(f"[DRY RUN] {command_text}")
        return 0

    with log_path.open("w", encoding="utf-8", newline="\n") as log_file:
        log_file.write(f"$ {command_text}\n\n")
        log_file.flush()
        result = subprocess.run(
            command,
            cwd=ROOT_DIR,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode


def run_platform(task: PlatformTask, *, dry_run: bool, disable_cdp: bool) -> int:
    sqlite_db_path = SQLITE_DIR / f"{task.name}_sqlite.db"
    env = build_env(sqlite_db_path, disable_cdp=disable_cdp)

    init_log_path = LOG_DIR / f"{task.name}_init.log"
    run_log_path = LOG_DIR / f"today_{task.name}.log"

    init_command = [UV_BIN, "run", "main.py", "--init_db", "sqlite"]
    run_command_args = [
        UV_BIN,
        "run",
        "main.py",
        "--platform",
        task.name,
        "--lt",
        LOGIN_TYPE,
        "--type",
        "search",
        "--keywords",
        task.keywords,
        "--save_data_option",
        SAVE_DATA_OPTION,
        "--get_comment",
        bool_arg(GET_COMMENT),
        "--get_sub_comment",
        bool_arg(GET_SUB_COMMENT),
        "--max_comments_count_singlenotes",
        str(MAX_COMMENTS_COUNT),
        "--max_concurrency_num",
        str(MAX_CONCURRENCY_NUM),
        "--headless",
        bool_arg(HEADLESS),
    ]

    print(f"[INIT] {task.name} | sqlite={sqlite_db_path}")
    init_exit_code = run_command(
        init_command,
        log_path=init_log_path,
        env=env,
        dry_run=dry_run,
    )
    if init_exit_code != 0:
        print(f"[ERROR] {task.name} init failed. See {init_log_path}")
        return init_exit_code

    print(f"[RUN] {task.name} | keywords={task.keywords} | sqlite={sqlite_db_path}")
    run_exit_code = run_command(
        run_command_args,
        log_path=run_log_path,
        env=env,
        dry_run=dry_run,
    )
    if run_exit_code != 0:
        print(f"[ERROR] {task.name} failed. See {run_log_path}")
    return run_exit_code


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_DIR.mkdir(parents=True, exist_ok=True)

    tasks = iter_tasks(
        args.platform,
        only_empty_db=args.only_empty_db,
        sqlite_dir=SQLITE_DIR,
    )
    if not tasks:
        print("[DONE] No platforms need to run.")
        return 0

    fail_count = 0
    for task in tasks:
        exit_code = run_platform(
            task,
            dry_run=args.dry_run,
            disable_cdp=args.disable_cdp,
        )
        if exit_code != 0:
            fail_count += 1

    print()
    if fail_count:
        print(f"[DONE WITH ERRORS] {fail_count} platform(s) failed.")
        return 1

    print("[DONE] All platforms finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
