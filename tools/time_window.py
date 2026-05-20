# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/time_window.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


def _local_tz():
    return datetime.now().astimezone().tzinfo


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    @property
    def start_ts(self) -> int:
        return int(self.start.timestamp())

    @property
    def end_ts(self) -> int:
        return int(self.end.timestamp())


def parse_datetime_value(value: str) -> datetime:
    normalized = value.strip()
    if not normalized:
        raise ValueError("time window datetime value cannot be empty")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_local_tz())
    return parsed


def build_day_window(target_date: str) -> TimeWindow:
    normalized = target_date.strip()
    date_format = "%Y%m%d" if normalized.isdigit() and len(normalized) == 8 else "%Y-%m-%d"
    day_start = datetime.strptime(normalized, date_format).replace(tzinfo=_local_tz())
    day_end = day_start + timedelta(days=1)
    return TimeWindow(start=day_start, end=day_end)


def resolve_time_window(
    *,
    window_start: Optional[str],
    window_end: Optional[str],
    target_date: Optional[str] = None,
) -> Optional[TimeWindow]:
    if window_start and window_end:
        start = parse_datetime_value(window_start)
        end = parse_datetime_value(window_end)
        if end <= start:
            raise ValueError("window_end must be later than window_start")
        return TimeWindow(start=start, end=end)

    if target_date:
        return build_day_window(target_date)

    return None


def normalize_unix_timestamp(raw_value: object) -> Optional[int]:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        numeric = int(float(text))
    except ValueError:
        return None
    if numeric <= 0:
        return None
    if numeric > 1_000_000_000_000:
        return numeric // 1000
    return numeric


def timestamp_in_window(window: Optional[TimeWindow], raw_value: object) -> bool:
    if window is None:
        return True
    timestamp = normalize_unix_timestamp(raw_value)
    if timestamp is None:
        return False
    return window.start_ts <= timestamp < window.end_ts
