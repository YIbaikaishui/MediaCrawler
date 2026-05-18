import csv
from pathlib import Path

from csv_export_naming import DEFAULT_MERGED_RISK_CSV_NAME
from merge_platform_comment_risks import merge_platform_outputs


OUTPUT_FIELDNAMES = [
    "platform",
    "comment_id",
    "content_id",
    "comment_author",
    "comment_text",
    "comment_like_count",
    "parent_comment_id",
    "post_title",
    "post_summary",
    "post_author",
    "post_url",
    "canonical_post_url",
    "is_problematic",
    "sentiment",
    "risk_level",
    "category",
    "confidence",
    "reason",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_merge_platform_outputs_combines_existing_platform_csvs(tmp_path: Path):
    write_csv(
        tmp_path / "bili_sqlite" / "bili_comment_risk_analysis.csv",
        [
            {
                "platform": "bili",
                "comment_id": "b1",
                "content_id": "c1",
                "comment_author": "user1",
                "comment_text": "不欢迎",
                "comment_like_count": "10",
                "parent_comment_id": "0",
                "post_title": "特朗普访华",
                "post_summary": "",
                "post_author": "媒体",
                "post_url": "https://example.com/b1",
                "canonical_post_url": "https://example.com/b1",
                "is_problematic": "True",
                "sentiment": "negative",
                "risk_level": "high",
                "category": "会晤态度",
                "confidence": "0.95",
                "reason": "明确反对",
            }
        ],
    )
    write_csv(
        tmp_path / "xhs_sqlite" / "xhs_comment_risk_analysis.csv",
        [
            {
                "platform": "xhs",
                "comment_id": "x1",
                "content_id": "c2",
                "comment_author": "user2",
                "comment_text": "早该取消",
                "comment_like_count": "8",
                "parent_comment_id": "0",
                "post_title": "欢迎仪式",
                "post_summary": "",
                "post_author": "媒体",
                "post_url": "https://example.com/x1",
                "canonical_post_url": "https://example.com/x1",
                "is_problematic": "True",
                "sentiment": "negative",
                "risk_level": "high",
                "category": "访华态度",
                "confidence": "0.91",
                "reason": "唱衰会晤",
            }
        ],
    )

    result = merge_platform_outputs(tmp_path)

    assert result.row_count == 2
    assert result.merged_csv_path == tmp_path / DEFAULT_MERGED_RISK_CSV_NAME

    with result.merged_csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == [
        "平台",
        "评论ID",
        "内容ID",
        "评论作者",
        "评论内容",
        "评论点赞数",
        "父评论ID",
        "帖子标题",
        "帖子摘要",
        "帖子作者",
        "帖子链接",
        "标准帖子链接",
        "是否为负面评论",
        "情绪倾向",
        "风险等级",
        "分类",
        "置信度",
        "原因",
    ]
    assert [row["平台"] for row in rows] == ["bili", "xhs"]
    assert rows[0]["评论ID"] == "b1"
    assert rows[1]["评论ID"] == "x1"


def test_merge_platform_outputs_skips_missing_platform_csvs(tmp_path: Path):
    write_csv(
        tmp_path / "wb_sqlite" / "wb_comment_risk_analysis.csv",
        [
            {
                "platform": "wb",
                "comment_id": "w1",
                "content_id": "c3",
                "comment_author": "user3",
                "comment_text": "作秀",
                "comment_like_count": "3",
                "parent_comment_id": "0",
                "post_title": "欢迎仪式",
                "post_summary": "",
                "post_author": "媒体",
                "post_url": "https://example.com/w1",
                "canonical_post_url": "https://example.com/w1",
                "is_problematic": "True",
                "sentiment": "negative",
                "risk_level": "high",
                "category": "会晤态度",
                "confidence": "0.89",
                "reason": "嘲讽会晤",
            }
        ],
    )

    result = merge_platform_outputs(tmp_path)

    assert result.source_file_count == 1
    with result.merged_csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["平台"] == "wb"
