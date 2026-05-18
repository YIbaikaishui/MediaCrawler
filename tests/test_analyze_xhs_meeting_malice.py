import csv
from pathlib import Path

from analyze_xhs_meeting_malice import (
    collect_records,
    parse_decision_payload,
    select_ollama_response_text,
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_decision_payload_handles_json_markdown():
    decision = parse_decision_payload(
        """```json
{"is_malicious": true, "risk_level": "high", "confidence": 0.91, "reason": "包含威胁表达", "target": "会议"}
```"""
    )

    assert decision.is_malicious is True
    assert decision.risk_level == "high"
    assert decision.target == "会议"
    assert decision.confidence == 0.91


def test_select_ollama_response_text_falls_back_to_thinking():
    raw_text = select_ollama_response_text(
        {
            "response": "",
            "thinking": '{"is_malicious": false, "risk_level": "none", "confidence": 0.5, "reason": "测试", "target": "无"}',
        }
    )

    assert raw_text.startswith('{"is_malicious": false')


def test_collect_records_merges_note_context(tmp_path: Path):
    notes_path = tmp_path / "xhs_note.csv"
    comments_path = tmp_path / "xhs_note_comment.csv"

    write_csv(
        notes_path,
        [
            "note_id",
            "title",
            "desc",
            "nickname",
            "source_keyword",
            "note_url",
            "like_count",
        ],
        [
            {
                "note_id": "note-1",
                "title": "特朗普将访华",
                "desc": "外交相关会谈",
                "nickname": "媒体号",
                "source_keyword": "特朗普访华",
                "note_url": "https://example.com/note-1",
                "like_count": "5",
            }
        ],
    )
    write_csv(
        comments_path,
        [
            "comment_id",
            "note_id",
            "content",
            "nickname",
            "parent_comment_id",
            "like_count",
        ],
        [
            {
                "comment_id": "comment-1",
                "note_id": "note-1",
                "content": "这种会谈早该取消",
                "nickname": "路人",
                "parent_comment_id": "0",
                "like_count": "3",
            }
        ],
    )

    records = collect_records(notes_path, comments_path, include_notes=True, include_comments=True)

    assert len(records) == 2
    comment_record = next(record for record in records if record.record_type == "comment")
    assert comment_record.note_title == "特朗普将访华"
    assert comment_record.source_keyword == "特朗普访华"
    assert comment_record.text == "这种会谈早该取消"
