import csv
from pathlib import Path

from rank_negative_comment_risks import (
    NegativeRankingRecord,
    rank_negative_rows,
    write_ranked_rows,
)


def test_rank_negative_rows_prioritizes_direct_opposition():
    ranked = rank_negative_rows(
        [
            {
                "platform": "xhs",
                "comment_id": "c1",
                "comment_text": "不欢迎！！！",
                "comment_like_count": "5",
                "risk_level": "high",
                "confidence": "0.95",
                "sentiment": "negative",
            },
            {
                "platform": "ks",
                "comment_id": "c2",
                "comment_text": "人生闹剧",
                "comment_like_count": "5",
                "risk_level": "high",
                "confidence": "0.95",
                "sentiment": "negative",
            },
        ]
    )

    assert ranked[0].comment_id == "c1"
    assert ranked[0].negativity_score > ranked[1].negativity_score


def test_write_ranked_rows_writes_top_n_and_rank(tmp_path: Path):
    output_path = tmp_path / "top_negative.csv"
    ranked_rows = [
        NegativeRankingRecord(
            rank=1,
            negativity_score=96.25,
            intensity_bucket="extreme",
            platform="xhs",
            comment_id="c1",
            content_id="post-1",
            comment_author="user1",
            comment_text="不欢迎",
            comment_like_count=12,
            parent_comment_id="0",
            post_title="特朗普访华",
            post_summary="",
            post_author="媒体",
            post_url="https://example.com/1",
            canonical_post_url="https://example.com/1",
            is_problematic="True",
            sentiment="negative",
            risk_level="high",
            category="会晤态度",
            confidence=0.95,
            reason="直接反对",
        ),
        NegativeRankingRecord(
            rank=2,
            negativity_score=80.10,
            intensity_bucket="high",
            platform="wb",
            comment_id="c2",
            content_id="post-2",
            comment_author="user2",
            comment_text="演戏",
            comment_like_count=2,
            parent_comment_id="0",
            post_title="欢迎仪式",
            post_summary="",
            post_author="媒体",
            post_url="https://example.com/2",
            canonical_post_url="https://example.com/2",
            is_problematic="True",
            sentiment="negative",
            risk_level="high",
            category="会晤态度",
            confidence=0.90,
            reason="作秀化表达",
        ),
    ]

    write_ranked_rows(output_path, ranked_rows[:1])

    with output_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert len(rows) == 1
    assert reader.fieldnames == [
        "排名",
        "负面强度分",
        "强度分层",
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
    assert rows[0]["排名"] == "1"
    assert rows[0]["负面强度分"] == "96.25"
    assert rows[0]["评论ID"] == "c1"
