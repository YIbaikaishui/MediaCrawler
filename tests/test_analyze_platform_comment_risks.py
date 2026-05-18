import csv
from pathlib import Path

from analyze_platform_comment_risks import (
    PLATFORM_CONFIGS,
    batch_threads,
    build_batch_prompt,
    collect_platform_records,
    group_comment_threads,
    is_meeting_negative_candidate,
    parse_batch_decisions,
    split_batch_for_retry,
    write_platform_output,
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_collect_platform_records_merges_post_title_into_comment_context(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "搞得像作秀一样",
                "nickname": "路人",
                "like_count": "8",
                "parent_comment_id": "0",
            }
        ],
    )

    grouped_records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])

    assert list(grouped_records) == ["xhs"]
    record = grouped_records["xhs"][0]
    assert record.post_title == "特朗普访华欢迎仪式"
    assert record.post_summary == "北京现场报道"
    assert record.comment_text == "搞得像作秀一样"
    assert record.post_url == "https://example.com/note-1"
    assert record.canonical_post_url == "https://www.xiaohongshu.com/explore/note-1"


def test_collect_platform_records_supports_chinese_header_csvs(tmp_path: Path):
    platform_dir = tmp_path / "小红书数据"
    write_csv(
        platform_dir / "笔记数据.csv",
        ["笔记ID", "标题", "简介", "昵称", "笔记链接"],
        [
            {
                "笔记ID": "note-1",
                "标题": "特朗普访华欢迎仪式",
                "简介": "北京现场报道",
                "昵称": "媒体号",
                "笔记链接": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "笔记评论数据.csv",
        ["评论ID", "笔记ID", "评论内容", "昵称", "点赞数", "父评论ID"],
        [
            {
                "评论ID": "comment-1",
                "笔记ID": "note-1",
                "评论内容": "搞得像作秀一样",
                "昵称": "路人",
                "点赞数": "8",
                "父评论ID": "0",
            }
        ],
    )

    grouped_records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])

    assert grouped_records["xhs"][0].post_title == "特朗普访华欢迎仪式"
    assert grouped_records["xhs"][0].comment_text == "搞得像作秀一样"


def test_collect_platform_records_preserves_weibo_original_post_url(tmp_path: Path):
    platform_dir = tmp_path / "wb_sqlite"
    write_csv(
        platform_dir / "weibo_note.csv",
        ["note_id", "content", "nickname", "note_url"],
        [
            {
                "note_id": "wb-1",
                "content": "原微博正文",
                "nickname": "博主",
                "note_url": "https://m.weibo.cn/detail/wb-1",
            }
        ],
    )
    write_csv(
        platform_dir / "weibo_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "wb-1",
                "content": "评论内容",
                "nickname": "评论者",
                "like_count": "1",
                "parent_comment_id": "0",
            }
        ],
    )

    grouped_records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["wb"]])

    assert grouped_records["wb"][0].post_url == "https://m.weibo.cn/detail/wb-1"
    assert grouped_records["wb"][0].canonical_post_url == "https://m.weibo.cn/detail/wb-1"


def test_group_comment_threads_groups_comments_by_post(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "搞得像作秀一样",
                "nickname": "路人",
                "like_count": "8",
                "parent_comment_id": "0",
            },
            {
                "comment_id": "comment-2",
                "note_id": "note-1",
                "content": "太夸张了",
                "nickname": "路人2",
                "like_count": "2",
                "parent_comment_id": "0",
            },
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]
    threads = group_comment_threads(records)

    assert len(threads) == 1
    assert threads[0].content_id == "note-1"
    assert [comment.comment_id for comment in threads[0].comments] == ["comment-1", "comment-2"]


def test_batch_threads_splits_large_single_post_thread(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": f"comment-{index}",
                "note_id": "note-1",
                "content": f"评论 {index}",
                "nickname": f"用户{index}",
                "like_count": "0",
                "parent_comment_id": "0",
            }
            for index in range(1, 6)
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]
    threads = group_comment_threads(records)
    batches = batch_threads(threads, max_posts_per_batch=4, max_comments_per_batch=3)

    assert len(batches) == 2
    assert [len(batch[0].comments) for batch in batches] == [3, 2]
    assert all(batch[0].content_id == "note-1" for batch in batches)


def test_split_batch_for_retry_splits_single_thread_by_comment_count(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": f"comment-{index}",
                "note_id": "note-1",
                "content": f"评论 {index}",
                "nickname": f"用户{index}",
                "like_count": "0",
                "parent_comment_id": "0",
            }
            for index in range(1, 5)
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]
    thread = group_comment_threads(records)[0]
    batches = split_batch_for_retry([thread])

    assert len(batches) == 2
    assert [len(batch[0].comments) for batch in batches] == [2, 2]


def test_build_batch_prompt_can_request_flagged_items_only(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "搞得像作秀一样",
                "nickname": "路人",
                "like_count": "8",
                "parent_comment_id": "0",
            }
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]
    thread = group_comment_threads(records)[0]
    prompt = build_batch_prompt("xhs", [thread], require_all_comments=False)

    assert "只返回有问题的评论" in prompt
    assert '"items": []' in prompt


def test_build_batch_prompt_targets_negative_stance_toward_meeting(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "这种会谈早该取消",
                "nickname": "路人",
                "like_count": "8",
                "parent_comment_id": "0",
            }
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]
    thread = group_comment_threads(records)[0]
    prompt = build_batch_prompt("xhs", [thread], require_all_comments=False)

    assert "本次会晤" in prompt
    assert "反对" in prompt


def test_is_meeting_negative_candidate_uses_post_context_for_opposition(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "这种会谈早该取消",
                "nickname": "路人",
                "like_count": "8",
                "parent_comment_id": "0",
            }
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]

    assert is_meeting_negative_candidate(records[0]) is True


def test_is_meeting_negative_candidate_skips_obviously_supportive_comment(tmp_path: Path):
    platform_dir = tmp_path / "bili_sqlite"
    write_csv(
        platform_dir / "bilibili_video.csv",
        ["video_id", "title", "desc", "nickname", "video_url"],
        [
            {
                "video_id": "video-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "video_url": "https://example.com/video-1",
            }
        ],
    )
    write_csv(
        platform_dir / "bilibili_video_comment.csv",
        ["comment_id", "video_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "video_id": "video-1",
                "content": "合作共赢",
                "nickname": "路人",
                "like_count": "8",
                "parent_comment_id": "0",
            }
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["bili"]])["bili"]

    assert is_meeting_negative_candidate(records[0]) is False


def test_parse_batch_decisions_reads_items_payload():
    decisions = parse_batch_decisions(
        """{
  "items": [
    {
      "comment_id": "comment-1",
      "is_problematic": true,
      "sentiment": "negative",
      "risk_level": "medium",
      "category": "mockery",
      "confidence": 0.82,
      "reason": "带有明显贬损倾向"
    }
  ]
}"""
    )

    assert decisions["comment-1"].is_problematic is True
    assert decisions["comment-1"].sentiment == "negative"
    assert decisions["comment-1"].risk_level == "medium"


def test_parse_batch_decisions_ignores_non_object_items():
    decisions = parse_batch_decisions(
        """{
  "items": [
    0.5,
    {
      "comment_id": "comment-1",
      "is_problematic": true,
      "sentiment": "negative",
      "risk_level": "medium",
      "category": "mockery",
      "confidence": 0.82,
      "reason": "带有明显贬损倾向"
    }
  ]
}"""
    )

    assert list(decisions) == ["comment-1"]


def test_write_platform_output_skips_safe_comments_when_decisions_missing(tmp_path: Path):
    platform_dir = tmp_path / "xhs_sqlite"
    write_csv(
        platform_dir / "xhs_note.csv",
        ["note_id", "title", "desc", "nickname", "note_url"],
        [
            {
                "note_id": "note-1",
                "title": "特朗普访华欢迎仪式",
                "desc": "北京现场报道",
                "nickname": "媒体号",
                "note_url": "https://example.com/note-1",
            }
        ],
    )
    write_csv(
        platform_dir / "xhs_note_comment.csv",
        ["comment_id", "note_id", "content", "nickname", "like_count", "parent_comment_id"],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "普通评论",
                "nickname": "路人",
                "like_count": "0",
                "parent_comment_id": "0",
            }
        ],
    )

    records = collect_platform_records(tmp_path, [PLATFORM_CONFIGS["xhs"]])["xhs"]
    output_path = write_platform_output(
        platform_dir,
        PLATFORM_CONFIGS["xhs"],
        records,
        decisions={},
        include_safe=False,
    )

    assert output_path.name == "负面评论分析结果.csv"
    with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    assert fieldnames == [
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
    with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == []
