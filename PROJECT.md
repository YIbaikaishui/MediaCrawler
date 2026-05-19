# PROJECT.md

## 一句话

`MediaCrawler` 是一个多平台公开信息采集仓库；当前默认交付路径是单机抓取后导出 `CSV`。

## 默认边界

当前默认只做这些事：

- 登录目标平台并采集公开内容。
- 把结果落到本地 `SQLite`。
- 最后导出成 `CSV`。

当前默认不做这些事：

- 不默认启用 `Redis`。
- 不默认启用代理池。
- 不默认走多平台批量调度。

## 最简工作流

1. 执行 `uv sync`。
2. 用单平台命令采集目标内容，保存方式使用 `sqlite`。
3. 数据默认落到 `database/platform_sqlite/`。
4. 执行 `uv run python export_sqlite_to_csv.py` 导出 `CSV` 到 `database/csv_export/`。

推荐入口：

```bash
uv run main.py --platform xhs --lt qrcode --type search --keywords "关键词" --save_data_option sqlite
uv run python export_sqlite_to_csv.py
```

## 为什么默认不用 Redis

- 主数据不存 `Redis`。
- 当前 `Redis` 主要服务代理 IP 池缓存。
- 对单机、低频、少量抓取场景，代理池通常不是刚需，所以 `Redis` 也不是刚需。

只有在这些条件出现时，才建议重新考虑 `Redis`：

- 需要启用代理抓取。
- 需要复用未过期代理，减少代理接口调用。
- 需要多实例共享代理状态。
