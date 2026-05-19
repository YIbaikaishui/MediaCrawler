# AGENTS.md

## 项目定位

- `MediaCrawler` 是一个多平台公开信息采集仓库。
- 当前默认推荐用法是单机轻量模式：抓少量内容，先落 `SQLite`，最后导出 `CSV`。
- 如果用户没有明确要求，不要默认升级成“代理池 + Redis + 多平台批量调度 + 分析成稿”的重模式。

## 默认操作模式

单机、低频、少量抓取时，按下面约束处理：

- 默认不启用代理池。
- 默认不要求 `Redis`。
- 默认使用 `sqlite` 作为落库方式。
- 默认通过 `export_sqlite_to_csv.py` 导出结构化 `CSV`。
- 默认优先单平台执行，不把 `run_search_today_all_platforms.py` 作为第一入口。

## Redis 边界

- `Redis` 不是这个项目的主数据存储。
- 当前 `Redis` 主要用于代理 IP 池缓存。
- 只有在启用代理抓取、需要复用未过期代理、或者需要多实例共享代理状态时，才值得启用 `Redis`。
- 对“一台电脑、每天抓几篇、最后导出 CSV”的场景，`Redis` 视为非必需。

## 推荐工作流

1. 进入仓库后执行 `uv sync`。
2. 用单平台命令采集目标内容，并明确 `--save_data_option sqlite`。
3. 数据默认写入 `database/platform_sqlite/`。
4. 执行 `uv run python export_sqlite_to_csv.py` 导出到 `database/csv_export/`。

## 推荐命令

- 安装依赖：
  - `uv sync`
- 单平台搜索采集：
  - `uv run main.py --platform xhs --lt qrcode --type search --keywords "关键词" --save_data_option sqlite`
- 导出全部 sqlite 到 CSV：
  - `uv run python export_sqlite_to_csv.py`
- 只导出某个平台：
  - `uv run python export_sqlite_to_csv.py --db xhs`

## 文档同步规则

只要改了这些事实，就同步更新 `README.md`、`PROJECT.md`、`AGENTS.md`：

- 默认推荐工作流
- `Redis` / 代理池是否属于必需前置
- 默认落库与导出路径
- 最简模式入口命令
