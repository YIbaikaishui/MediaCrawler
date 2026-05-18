from __future__ import annotations

from pathlib import Path


PLATFORM_DIRECTORY_NAME_MAP: dict[str, str] = {
    "bili_sqlite": "B站数据",
    "douyin_sqlite": "抖音数据",
    "ks_sqlite": "快手数据",
    "tieba_sqlite": "贴吧数据",
    "wb_sqlite": "微博数据",
    "xhs_sqlite": "小红书数据",
    "zhihu_sqlite": "知乎数据",
}

TABLE_CSV_NAME_MAP: dict[tuple[str, str], str] = {
    ("bili_sqlite", "bilibili_up_info"): "UP主数据.csv",
    ("bili_sqlite", "bilibili_contact_info"): "联系信息数据.csv",
    ("bili_sqlite", "bilibili_up_dynamic"): "UP主动态数据.csv",
    ("bili_sqlite", "bilibili_video"): "视频数据.csv",
    ("bili_sqlite", "bilibili_video_comment"): "视频评论数据.csv",
    ("bili_sqlite", "bili_comment_risk_analysis"): "负面评论分析结果.csv",
    ("douyin_sqlite", "douyin_aweme"): "作品数据.csv",
    ("douyin_sqlite", "douyin_aweme_comment"): "作品评论数据.csv",
    ("douyin_sqlite", "dy_creator"): "创作者数据.csv",
    ("ks_sqlite", "kuaishou_video"): "视频数据.csv",
    ("ks_sqlite", "kuaishou_video_comment"): "视频评论数据.csv",
    ("ks_sqlite", "ks_comment_risk_analysis"): "负面评论分析结果.csv",
    ("tieba_sqlite", "tieba_note"): "帖子数据.csv",
    ("tieba_sqlite", "tieba_comment"): "帖子评论数据.csv",
    ("tieba_sqlite", "tieba_creator"): "创作者数据.csv",
    ("wb_sqlite", "weibo_note"): "博文数据.csv",
    ("wb_sqlite", "weibo_note_comment"): "博文评论数据.csv",
    ("wb_sqlite", "weibo_creator"): "创作者数据.csv",
    ("wb_sqlite", "wb_comment_risk_analysis"): "负面评论分析结果.csv",
    ("xhs_sqlite", "xhs_creator"): "创作者数据.csv",
    ("xhs_sqlite", "xhs_note"): "笔记数据.csv",
    ("xhs_sqlite", "xhs_note_comment"): "笔记评论数据.csv",
    ("xhs_sqlite", "xhs_comment_risk_analysis"): "负面评论分析结果.csv",
    ("zhihu_sqlite", "zhihu_content"): "内容数据.csv",
    ("zhihu_sqlite", "zhihu_comment"): "评论数据.csv",
    ("zhihu_sqlite", "zhihu_creator"): "创作者数据.csv",
    ("zhihu_sqlite", "zhihu_comment_risk_analysis"): "负面评论分析结果.csv",
}

ROOT_FILE_NAME_MAP: dict[str, str] = {
    "bg_script_test.log": "后台脚本测试.log",
    "bg_test.log": "后台测试.log",
    "full_comment_analysis.log": "全量评论分析.log",
    "all_platform_comment_risk_analysis.csv": "所有平台负面评论汇总.csv",
    "top_negative_comment_risk_analysis.csv": "负面情绪最强评论.csv",
}

DEFAULT_MERGED_RISK_CSV_NAME = "所有平台负面评论汇总.csv"
DEFAULT_TOP_NEGATIVE_CSV_NAME = "负面情绪最强评论.csv"
DEFAULT_PLATFORM_RISK_CSV_NAME = "负面评论分析结果.csv"

REVERSE_PLATFORM_DIRECTORY_NAME_MAP = {value: key for key, value in PLATFORM_DIRECTORY_NAME_MAP.items()}


def normalize_csv_name(csv_name_or_stem: str) -> str:
    name = Path(csv_name_or_stem).name
    return Path(name).stem


def get_export_directory_name(db_or_dir_name: str) -> str:
    return PLATFORM_DIRECTORY_NAME_MAP.get(db_or_dir_name, db_or_dir_name)


def get_legacy_export_directory_name(chinese_or_legacy_name: str) -> str | None:
    if chinese_or_legacy_name in PLATFORM_DIRECTORY_NAME_MAP:
        return chinese_or_legacy_name
    return REVERSE_PLATFORM_DIRECTORY_NAME_MAP.get(chinese_or_legacy_name)


def get_export_csv_name(db_or_dir_name: str, table_name_or_csv_name: str) -> str:
    normalized_table_name = normalize_csv_name(table_name_or_csv_name)
    direct_match = TABLE_CSV_NAME_MAP.get((db_or_dir_name, normalized_table_name))
    if direct_match is not None:
        return direct_match

    for (_, table_name), csv_name in TABLE_CSV_NAME_MAP.items():
        if table_name == normalized_table_name:
            return csv_name

    return f"{normalized_table_name}.csv"


def get_root_export_file_name(file_name: str) -> str:
    return ROOT_FILE_NAME_MAP.get(file_name, file_name)
