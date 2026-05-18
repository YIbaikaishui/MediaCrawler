from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from analyze_platform_comment_risks import extract_json_text, normalize_confidence, select_ollama_response_text


@dataclass(frozen=True)
class MaliceDecision:
    is_malicious: bool
    risk_level: str
    confidence: float
    reason: str
    target: str


@dataclass(frozen=True)
class XhsRecord:
    record_type: str
    text: str
    note_id: str
    note_title: str
    note_desc: str
    note_author: str
    source_keyword: str
    note_url: str
    comment_id: str = ""
    comment_author: str = ""
    parent_comment_id: str = ""
    like_count: int = 0


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_like_count(raw_value: str | None) -> int:
    try:
        return int(str(raw_value or "0").strip() or "0")
    except ValueError:
        return 0


def parse_decision_payload(raw_text: str) -> MaliceDecision:
    payload = json.loads(extract_json_text(raw_text))
    return MaliceDecision(
        is_malicious=bool(payload.get("is_malicious")),
        risk_level=str(payload.get("risk_level", "")).strip().lower(),
        confidence=normalize_confidence(payload.get("confidence")),
        reason=str(payload.get("reason", "")).strip(),
        target=str(payload.get("target", "")).strip(),
    )


def collect_records(
    notes_path: Path,
    comments_path: Path,
    *,
    include_notes: bool,
    include_comments: bool,
) -> list[XhsRecord]:
    note_rows = _read_csv_rows(notes_path)
    note_context_by_id = {
        row.get("note_id", "").strip(): row
        for row in note_rows
        if row.get("note_id", "").strip()
    }

    records: list[XhsRecord] = []
    if include_notes:
        for row in note_rows:
            note_id = row.get("note_id", "").strip()
            if not note_id:
                continue
            records.append(
                XhsRecord(
                    record_type="note",
                    text=str(row.get("desc", "")).strip() or str(row.get("title", "")).strip(),
                    note_id=note_id,
                    note_title=str(row.get("title", "")).strip(),
                    note_desc=str(row.get("desc", "")).strip(),
                    note_author=str(row.get("nickname", "")).strip(),
                    source_keyword=str(row.get("source_keyword", "")).strip(),
                    note_url=str(row.get("note_url", "")).strip(),
                    like_count=_parse_like_count(row.get("like_count")),
                )
            )

    if include_comments:
        for row in _read_csv_rows(comments_path):
            note_id = row.get("note_id", "").strip()
            comment_id = row.get("comment_id", "").strip()
            text = str(row.get("content", "")).strip()
            if not note_id or not comment_id or not text:
                continue
            note_context = note_context_by_id.get(note_id, {})
            records.append(
                XhsRecord(
                    record_type="comment",
                    text=text,
                    note_id=note_id,
                    note_title=str(note_context.get("title", "")).strip(),
                    note_desc=str(note_context.get("desc", "")).strip(),
                    note_author=str(note_context.get("nickname", "")).strip(),
                    source_keyword=str(note_context.get("source_keyword", "")).strip(),
                    note_url=str(note_context.get("note_url", "")).strip(),
                    comment_id=comment_id,
                    comment_author=str(row.get("nickname", "")).strip(),
                    parent_comment_id=str(row.get("parent_comment_id", "")).strip(),
                    like_count=_parse_like_count(row.get("like_count")),
                )
            )

    return records


__all__ = [
    "MaliceDecision",
    "XhsRecord",
    "collect_records",
    "parse_decision_payload",
    "select_ollama_response_text",
]
