from pathlib import Path

from csv_export_naming import (
    DEFAULT_MERGED_RISK_CSV_NAME,
    DEFAULT_TOP_NEGATIVE_CSV_NAME,
    get_export_csv_name,
    get_export_directory_name,
)


def test_get_export_directory_name_uses_chinese_platform_name():
    assert get_export_directory_name("bili_sqlite") == "B站数据"
    assert get_export_directory_name("xhs_sqlite") == "小红书数据"


def test_get_export_csv_name_uses_chinese_table_name():
    assert get_export_csv_name("bili_sqlite", "bilibili_video") == "视频数据.csv"
    assert get_export_csv_name("bili_sqlite", "bilibili_video_comment") == "视频评论数据.csv"
    assert get_export_csv_name("bili_sqlite", "bili_comment_risk_analysis") == "负面评论分析结果.csv"
    assert get_export_csv_name("bili_sqlite", "douyin_aweme") == "作品数据.csv"


def test_default_merged_and_ranked_output_names_are_chinese():
    assert DEFAULT_MERGED_RISK_CSV_NAME == "所有平台负面评论汇总.csv"
    assert DEFAULT_TOP_NEGATIVE_CSV_NAME == "负面情绪最强评论.csv"
