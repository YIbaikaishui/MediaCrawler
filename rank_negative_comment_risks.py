from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from analyze_platform_comment_risks import DIRECT_MEETING_OPPOSITION_TERMS, NEGATIVE_EMOTION_TERMS
from csv_export_columns import read_csv_rows, write_csv_rows
from csv_export_naming import DEFAULT_TOP_NEGATIVE_CSV_NAME
from merge_platform_comment_risks import DEFAULT_OUTPUT_PATH as DEFAULT_MERGED_CSV_PATH


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_PATH = ROOT_DIR / "database" / "csv_export" / DEFAULT_TOP_NEGATIVE_CSV_NAME
RISK_LEVEL_SCORES = {
    "none": 0.0,
    "low": 18.0,
    "medium": 45.0,
    "high": 70.0,
}


@dataclass(frozen=True)
class NegativeRankingRecord:
    rank: int
    negativity_score: float
    intensity_bucket: str
    platform: str
    comment_id: str
    content_id: str
    comment_author: str
    comment_text: str
    comment_like_count: int
    parent_comment_id: str
    post_title: str
    post_summary: str
    post_author: str
    post_url: str
    canonical_post_url: str
    is_problematic: str
    sentiment: str
    risk_level: str
    category: str
    confidence: float
    reason: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank the strongest negative comments from the merged platform risk CSV.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_MERGED_CSV_PATH,
        help="Merged platform comment risk CSV path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output CSV path for ranked strongest negative comments.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="How many strongest negative comments to keep in the output.",
    )
    return parser.parse_args(argv)


def parse_float(value: str) -> float:
    try:
        return float(value.strip() or "0")
    except ValueError:
        return 0.0


def parse_int(value: str) -> int:
    try:
        return int(value.strip() or "0")
    except ValueError:
        return 0


def count_matching_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def score_comment_row(row: dict[str, str]) -> float:
    comment_text = row.get("comment_text", "")
    risk_score = RISK_LEVEL_SCORES.get(row.get("risk_level", "").strip().lower(), 0.0)
    confidence_score = parse_float(row.get("confidence", "")) * 20.0
    direct_opposition_score = count_matching_terms(comment_text, DIRECT_MEETING_OPPOSITION_TERMS) * 8.0
    negative_emotion_score = count_matching_terms(comment_text, NEGATIVE_EMOTION_TERMS) * 5.0
    punctuation_score = min(comment_text.count("!") + comment_text.count("！"), 3) * 1.5
    like_score = min(math.log1p(parse_int(row.get("comment_like_count", ""))) * 2.5, 10.0)
    return round(
        risk_score
        + confidence_score
        + direct_opposition_score
        + negative_emotion_score
        + punctuation_score
        + like_score,
        2,
    )


def determine_intensity_bucket(score: float) -> str:
    if score >= 95:
        return "extreme"
    if score >= 82:
        return "very_high"
    if score >= 68:
        return "high"
    return "moderate"


def rank_negative_rows(rows: list[dict[str, str]]) -> list[NegativeRankingRecord]:
    scored_rows = []
    for row in rows:
        score = score_comment_row(row)
        scored_rows.append(
            (
                score,
                parse_float(row.get("confidence", "")),
                parse_int(row.get("comment_like_count", "")),
                row.get("comment_id", ""),
                row,
            )
        )

    scored_rows.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))

    ranked_records: list[NegativeRankingRecord] = []
    for index, (score, _, _, _, row) in enumerate(scored_rows, start=1):
        ranked_records.append(
            NegativeRankingRecord(
                rank=index,
                negativity_score=score,
                intensity_bucket=determine_intensity_bucket(score),
                platform=row.get("platform", ""),
                comment_id=row.get("comment_id", ""),
                content_id=row.get("content_id", ""),
                comment_author=row.get("comment_author", ""),
                comment_text=row.get("comment_text", ""),
                comment_like_count=parse_int(row.get("comment_like_count", "")),
                parent_comment_id=row.get("parent_comment_id", ""),
                post_title=row.get("post_title", ""),
                post_summary=row.get("post_summary", ""),
                post_author=row.get("post_author", ""),
                post_url=row.get("post_url", ""),
                canonical_post_url=row.get("canonical_post_url", ""),
                is_problematic=row.get("is_problematic", ""),
                sentiment=row.get("sentiment", ""),
                risk_level=row.get("risk_level", ""),
                category=row.get("category", ""),
                confidence=parse_float(row.get("confidence", "")),
                reason=row.get("reason", ""),
            )
        )
    return ranked_records


def load_rows(path: Path) -> list[dict[str, str]]:
    return read_csv_rows(path, "merged_comment_risk_analysis")


def write_ranked_rows(path: Path, ranked_rows: list[NegativeRankingRecord]) -> None:
    fieldnames = [
        "rank",
        "negativity_score",
        "intensity_bucket",
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
    rows = [
        {
            "rank": row.rank,
            "negativity_score": f"{row.negativity_score:.2f}",
            "intensity_bucket": row.intensity_bucket,
            "platform": row.platform,
            "comment_id": row.comment_id,
            "content_id": row.content_id,
            "comment_author": row.comment_author,
            "comment_text": row.comment_text,
            "comment_like_count": row.comment_like_count,
            "parent_comment_id": row.parent_comment_id,
            "post_title": row.post_title,
            "post_summary": row.post_summary,
            "post_author": row.post_author,
            "post_url": row.post_url,
            "canonical_post_url": row.canonical_post_url,
            "is_problematic": row.is_problematic,
            "sentiment": row.sentiment,
            "risk_level": row.risk_level,
            "category": row.category,
            "confidence": f"{row.confidence:.2f}",
            "reason": row.reason,
        }
        for row in ranked_rows
    ]
    write_csv_rows(path, "top_negative_comment_risk_analysis", fieldnames, rows)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_rows(args.input)
    ranked_rows = rank_negative_rows(rows)
    limited_rows = ranked_rows[: max(args.top_n, 0)]
    write_ranked_rows(args.output, limited_rows)
    print(f"[DONE] ranked {len(rows)} row(s), kept {len(limited_rows)} -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
