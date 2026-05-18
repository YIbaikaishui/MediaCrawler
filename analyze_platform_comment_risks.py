from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

import httpx
from csv_export_columns import read_csv_rows as read_canonical_csv_rows
from csv_export_columns import write_csv_rows as write_translated_csv_rows
from csv_export_naming import get_export_csv_name, get_export_directory_name


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_EXPORT_DIR = ROOT_DIR / "database" / "csv_export"
DEFAULT_MODEL = "huihui_ai/qwen3.5-abliterated:2B"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
MEETING_CONTEXT_TERMS = (
    "访华",
    "来华",
    "来访",
    "欢迎仪式",
    "国事访问",
    "来中国",
    "去中国",
    "天坛",
)
DIRECT_MEETING_OPPOSITION_TERMS = (
    "不欢迎",
    "别来",
    "别来了",
    "最好别来",
    "来干吗",
    "来干嘛",
    "来这干吗",
    "别谈",
    "不该来",
    "没必要来",
    "没有必要来",
    "没必要",
    "没有必要",
    "早该取消",
    "应该取消",
    "就该取消",
    "取消算了",
    "作秀",
    "演戏",
    "闹剧",
    "会谈是戏",
    "白来",
    "谈不成",
    "没结果",
    "做样子",
    "摆拍",
)
NEGATIVE_EMOTION_TERMS = (
    "恶心",
    "丢人",
    "虚伪",
    "笑话",
    "看吐了",
    "讨厌",
    "烦",
    "耻辱",
    "跪",
    "舔",
)
COMMENT_EVENT_TERMS = (
    "访华",
    "会晤",
    "会谈",
    "欢迎仪式",
    "来华",
    "来访",
    "访问",
    "会面",
)
SUPPORTIVE_TERMS = (
    "合作共赢",
    "互利互惠",
    "欢迎",
    "支持",
    "期待",
    "和平",
    "友好",
    "赞",
    "点赞",
)


RiskLevel = Literal["none", "low", "medium", "high"]
Sentiment = Literal["positive", "neutral", "negative"]


@dataclass(frozen=True)
class PlatformConfig:
    platform_name: str
    export_key: str
    directory_name: str
    content_csv_name: str
    comment_csv_name: str
    content_id_field: str
    comment_join_field: str
    content_title_fields: tuple[str, ...]
    content_summary_fields: tuple[str, ...]
    content_author_field: str
    content_url_fields: tuple[str, ...]
    canonical_url_builder: Callable[[dict[str, str]], str] | None = None
    comment_id_field: str = "comment_id"
    comment_text_field: str = "content"
    comment_author_field: str = "nickname"
    comment_like_field: str = "like_count"
    comment_parent_field: str = "parent_comment_id"
    legacy_directory_name: str | None = None
    legacy_content_csv_name: str | None = None
    legacy_comment_csv_name: str | None = None
    legacy_output_csv_name: str | None = None

    @property
    def output_csv_name(self) -> str:
        return get_export_csv_name(self.export_key, f"{self.platform_name}_comment_risk_analysis")


@dataclass(frozen=True)
class PostContext:
    content_id: str
    post_title: str
    post_summary: str
    post_author: str
    post_url: str
    canonical_post_url: str


@dataclass(frozen=True)
class CommentRecord:
    platform_name: str
    comment_id: str
    content_id: str
    comment_text: str
    comment_author: str
    comment_like_count: int
    parent_comment_id: str
    post_title: str
    post_summary: str
    post_author: str
    post_url: str
    canonical_post_url: str


@dataclass(frozen=True)
class PostThread:
    platform_name: str
    content_id: str
    post_title: str
    post_summary: str
    post_author: str
    post_url: str
    canonical_post_url: str
    comments: tuple[CommentRecord, ...]


@dataclass(frozen=True)
class CommentDecision:
    comment_id: str
    is_problematic: bool
    sentiment: Sentiment
    risk_level: RiskLevel
    category: str
    confidence: float
    reason: str


def normalize_url_for_output(url: str) -> str:
    stripped = url.strip()
    if not stripped:
        return ""
    return stripped.split("?", 1)[0]


def build_id_based_url(base_url: str, id_field: str) -> Callable[[dict[str, str]], str]:
    def _builder(row: dict[str, str]) -> str:
        content_id = row.get(id_field, "").strip()
        if not content_id:
            return ""
        return f"{base_url}{content_id}"

    return _builder


def build_zhihu_canonical_url(row: dict[str, str]) -> str:
    content_type = row.get("content_type", "").strip().lower()
    content_id = row.get("content_id", "").strip()
    question_id = row.get("question_id", "").strip()
    if content_type == "article" and content_id:
        return f"https://zhuanlan.zhihu.com/p/{content_id}"
    if content_type == "answer" and content_id and question_id:
        return f"https://www.zhihu.com/question/{question_id}/answer/{content_id}"
    if content_type == "zvideo" and content_id:
        return f"https://www.zhihu.com/zvideo/{content_id}"

    return normalize_url_for_output(row.get("content_url", ""))


PLATFORM_CONFIGS: dict[str, PlatformConfig] = {
    "bili": PlatformConfig(
        platform_name="bili",
        export_key="bili_sqlite",
        directory_name=get_export_directory_name("bili_sqlite"),
        content_csv_name=get_export_csv_name("bili_sqlite", "bilibili_video"),
        comment_csv_name=get_export_csv_name("bili_sqlite", "bilibili_video_comment"),
        content_id_field="video_id",
        comment_join_field="video_id",
        content_title_fields=("title",),
        content_summary_fields=("desc",),
        content_author_field="nickname",
        content_url_fields=("video_url",),
        canonical_url_builder=build_id_based_url("https://www.bilibili.com/video/av", "video_id"),
        legacy_directory_name="bili_sqlite",
        legacy_content_csv_name="bilibili_video.csv",
        legacy_comment_csv_name="bilibili_video_comment.csv",
        legacy_output_csv_name="bili_comment_risk_analysis.csv",
    ),
    "ks": PlatformConfig(
        platform_name="ks",
        export_key="ks_sqlite",
        directory_name=get_export_directory_name("ks_sqlite"),
        content_csv_name=get_export_csv_name("ks_sqlite", "kuaishou_video"),
        comment_csv_name=get_export_csv_name("ks_sqlite", "kuaishou_video_comment"),
        content_id_field="video_id",
        comment_join_field="video_id",
        content_title_fields=("title",),
        content_summary_fields=("desc",),
        content_author_field="nickname",
        content_url_fields=("video_url",),
        canonical_url_builder=build_id_based_url("https://www.kuaishou.com/short-video/", "video_id"),
        legacy_directory_name="ks_sqlite",
        legacy_content_csv_name="kuaishou_video.csv",
        legacy_comment_csv_name="kuaishou_video_comment.csv",
        legacy_output_csv_name="ks_comment_risk_analysis.csv",
    ),
    "wb": PlatformConfig(
        platform_name="wb",
        export_key="wb_sqlite",
        directory_name=get_export_directory_name("wb_sqlite"),
        content_csv_name=get_export_csv_name("wb_sqlite", "weibo_note"),
        comment_csv_name=get_export_csv_name("wb_sqlite", "weibo_note_comment"),
        content_id_field="note_id",
        comment_join_field="note_id",
        content_title_fields=("content",),
        content_summary_fields=("content",),
        content_author_field="nickname",
        content_url_fields=("note_url",),
        canonical_url_builder=build_id_based_url("https://m.weibo.cn/detail/", "note_id"),
        legacy_directory_name="wb_sqlite",
        legacy_content_csv_name="weibo_note.csv",
        legacy_comment_csv_name="weibo_note_comment.csv",
        legacy_output_csv_name="wb_comment_risk_analysis.csv",
    ),
    "xhs": PlatformConfig(
        platform_name="xhs",
        export_key="xhs_sqlite",
        directory_name=get_export_directory_name("xhs_sqlite"),
        content_csv_name=get_export_csv_name("xhs_sqlite", "xhs_note"),
        comment_csv_name=get_export_csv_name("xhs_sqlite", "xhs_note_comment"),
        content_id_field="note_id",
        comment_join_field="note_id",
        content_title_fields=("title",),
        content_summary_fields=("desc",),
        content_author_field="nickname",
        content_url_fields=("note_url",),
        canonical_url_builder=build_id_based_url("https://www.xiaohongshu.com/explore/", "note_id"),
        legacy_directory_name="xhs_sqlite",
        legacy_content_csv_name="xhs_note.csv",
        legacy_comment_csv_name="xhs_note_comment.csv",
        legacy_output_csv_name="xhs_comment_risk_analysis.csv",
    ),
    "zhihu": PlatformConfig(
        platform_name="zhihu",
        export_key="zhihu_sqlite",
        directory_name=get_export_directory_name("zhihu_sqlite"),
        content_csv_name=get_export_csv_name("zhihu_sqlite", "zhihu_content"),
        comment_csv_name=get_export_csv_name("zhihu_sqlite", "zhihu_comment"),
        content_id_field="content_id",
        comment_join_field="content_id",
        content_title_fields=("title",),
        content_summary_fields=("desc", "content_text"),
        content_author_field="author_name",
        content_url_fields=("content_url",),
        canonical_url_builder=build_zhihu_canonical_url,
        legacy_directory_name="zhihu_sqlite",
        legacy_content_csv_name="zhihu_content.csv",
        legacy_comment_csv_name="zhihu_comment.csv",
        legacy_output_csv_name="zhihu_comment_risk_analysis.csv",
    ),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze problematic and negative-intent comments across platform CSV exports with Ollama.",
    )
    parser.add_argument("--csv-root", type=Path, default=DEFAULT_CSV_EXPORT_DIR)
    parser.add_argument("--platforms", nargs="*", choices=sorted(PLATFORM_CONFIGS), default=None)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-posts-per-batch", type=int, default=4)
    parser.add_argument("--max-comments-per-batch", type=int, default=36)
    parser.add_argument("--limit-per-platform", type=int, default=None)
    parser.add_argument("--include-safe", action="store_true")
    return parser.parse_args(argv)


def read_csv_rows(path: Path, file_key: str | None = None) -> list[dict[str, str]]:
    if file_key is not None:
        return read_canonical_csv_rows(path, file_key)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def first_non_empty(row: dict[str, str], field_names: Iterable[str]) -> str:
    for field_name in field_names:
        value = row.get(field_name, "").strip()
        if value:
            return value
    return ""


def parse_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(str(value).strip() or "0")
    except ValueError:
        return 0


def truncate_text(text: str, *, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def unique_non_empty_names(*names: str | None) -> tuple[str, ...]:
    ordered_names: list[str] = []
    for name in names:
        if name and name not in ordered_names:
            ordered_names.append(name)
    return tuple(ordered_names)


def resolve_existing_child_path(parent: Path, *candidate_names: str | None) -> Path | None:
    for name in unique_non_empty_names(*candidate_names):
        candidate = parent / name
        if candidate.exists():
            return candidate
    return None


def compact_text_for_matching(*parts: str) -> str:
    return " ".join(" ".join(part.split()) for part in parts if part).lower()


def contains_any_term(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def is_meeting_negative_candidate(record: CommentRecord) -> bool:
    comment_text = compact_text_for_matching(record.comment_text)
    if not comment_text:
        return False

    context_text = compact_text_for_matching(record.post_title, record.post_summary, record.comment_text)
    if not contains_any_term(context_text, MEETING_CONTEXT_TERMS):
        return False

    if contains_any_term(comment_text, SUPPORTIVE_TERMS) and not contains_any_term(
        comment_text,
        DIRECT_MEETING_OPPOSITION_TERMS,
    ):
        return False

    if contains_any_term(comment_text, DIRECT_MEETING_OPPOSITION_TERMS):
        return True

    return contains_any_term(comment_text, NEGATIVE_EMOTION_TERMS) and contains_any_term(
        comment_text,
        COMMENT_EVENT_TERMS,
    )


def select_records_for_analysis(records: list[CommentRecord], *, include_safe: bool) -> list[CommentRecord]:
    if include_safe:
        return records
    return [record for record in records if is_meeting_negative_candidate(record)]


def build_canonical_post_url(config: PlatformConfig, row: dict[str, str], raw_url: str) -> str:
    if config.canonical_url_builder is not None:
        canonical_url = config.canonical_url_builder(row)
        if canonical_url:
            return canonical_url
    return normalize_url_for_output(raw_url)


def load_post_contexts(content_path: Path, config: PlatformConfig) -> dict[str, PostContext]:
    content_file_key = Path(config.legacy_content_csv_name or config.content_csv_name).stem
    post_contexts: dict[str, PostContext] = {}
    for row in read_csv_rows(content_path, content_file_key):
        content_id = row.get(config.content_id_field, "").strip()
        if not content_id:
            continue
        raw_post_url = first_non_empty(row, config.content_url_fields)
        post_contexts[content_id] = PostContext(
            content_id=content_id,
            post_title=first_non_empty(row, config.content_title_fields),
            post_summary=first_non_empty(row, config.content_summary_fields),
            post_author=row.get(config.content_author_field, "").strip(),
            post_url=raw_post_url,
            canonical_post_url=build_canonical_post_url(config, row, raw_post_url),
        )
    return post_contexts


def collect_platform_records(
    csv_root: Path,
    configs: Iterable[PlatformConfig],
    *,
    limit_per_platform: int | None = None,
) -> dict[str, list[CommentRecord]]:
    grouped_records: dict[str, list[CommentRecord]] = {}
    for config in configs:
        platform_dir = resolve_existing_child_path(
            csv_root,
            config.directory_name,
            config.legacy_directory_name,
        )
        if platform_dir is None:
            continue

        content_path = resolve_existing_child_path(
            platform_dir,
            config.content_csv_name,
            config.legacy_content_csv_name,
        )
        comment_path = resolve_existing_child_path(
            platform_dir,
            config.comment_csv_name,
            config.legacy_comment_csv_name,
        )
        if content_path is None or comment_path is None:
            continue

        post_contexts = load_post_contexts(content_path, config)
        records: list[CommentRecord] = []
        comment_file_key = Path(config.legacy_comment_csv_name or config.comment_csv_name).stem
        for row in read_csv_rows(comment_path, comment_file_key):
            comment_id = row.get(config.comment_id_field, "").strip()
            content_id = row.get(config.comment_join_field, "").strip()
            comment_text = row.get(config.comment_text_field, "").strip()
            if not comment_id or not content_id or not comment_text:
                continue
            context = post_contexts.get(
                content_id,
                PostContext(
                    content_id=content_id,
                    post_title="",
                    post_summary="",
                    post_author="",
                    post_url="",
                    canonical_post_url="",
                ),
            )
            records.append(
                CommentRecord(
                    platform_name=config.platform_name,
                    comment_id=comment_id,
                    content_id=content_id,
                    comment_text=comment_text,
                    comment_author=row.get(config.comment_author_field, "").strip(),
                    comment_like_count=parse_int(row.get(config.comment_like_field)),
                    parent_comment_id=row.get(config.comment_parent_field, "").strip(),
                    post_title=context.post_title,
                    post_summary=context.post_summary,
                    post_author=context.post_author,
                    post_url=context.post_url,
                    canonical_post_url=context.canonical_post_url,
                )
            )

        if limit_per_platform is not None:
            records = records[:limit_per_platform]
        grouped_records[config.platform_name] = records

    return grouped_records


def group_comment_threads(records: list[CommentRecord]) -> list[PostThread]:
    grouped: dict[str, list[CommentRecord]] = {}
    thread_meta: dict[str, CommentRecord] = {}
    order: list[str] = []
    for record in records:
        if record.content_id not in grouped:
            grouped[record.content_id] = []
            thread_meta[record.content_id] = record
            order.append(record.content_id)
        grouped[record.content_id].append(record)

    threads: list[PostThread] = []
    for content_id in order:
        meta = thread_meta[content_id]
        threads.append(
            PostThread(
                platform_name=meta.platform_name,
                content_id=content_id,
                post_title=meta.post_title,
                post_summary=meta.post_summary,
                post_author=meta.post_author,
                post_url=meta.post_url,
                canonical_post_url=meta.canonical_post_url,
                comments=tuple(grouped[content_id]),
            )
        )
    return threads


def extract_json_text(raw_text: str) -> str:
    stripped = raw_text.strip()
    if stripped.startswith("```"):
        lines = [line for line in stripped.splitlines() if not line.strip().startswith("```")]
        stripped = "\n".join(lines).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Could not find JSON object in Ollama response: {raw_text!r}")
    return stripped[start : end + 1]


def select_ollama_response_text(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("response"),
        payload.get("thinking"),
        payload.get("message", {}).get("content") if isinstance(payload.get("message"), dict) else None,
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    raise ValueError(f"Ollama response did not contain usable text: {payload}")


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是", "有问题", "problematic"}


def normalize_sentiment(value: Any) -> Sentiment:
    text = str(value).strip().lower()
    aliases = {
        "positive": "positive",
        "正向": "positive",
        "neutral": "neutral",
        "中性": "neutral",
        "negative": "negative",
        "负向": "negative",
        "负面": "negative",
    }
    return aliases.get(text, "neutral")


def normalize_risk_level(value: Any) -> RiskLevel:
    text = str(value).strip().lower()
    aliases = {
        "none": "none",
        "无": "none",
        "low": "low",
        "轻度": "low",
        "medium": "medium",
        "moderate": "medium",
        "中": "medium",
        "high": "high",
        "高": "high",
        "严重": "high",
    }
    return aliases.get(text, "none")


def normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def parse_batch_decisions(raw_text: str) -> dict[str, CommentDecision]:
    payload = json.loads(extract_json_text(raw_text))
    items = payload["items"] if isinstance(payload, dict) else payload
    decisions: dict[str, CommentDecision] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        comment_id = str(item.get("comment_id", "")).strip()
        if not comment_id:
            continue
        decisions[comment_id] = CommentDecision(
            comment_id=comment_id,
            is_problematic=normalize_bool(item.get("is_problematic")),
            sentiment=normalize_sentiment(item.get("sentiment")),
            risk_level=normalize_risk_level(item.get("risk_level")),
            category=str(item.get("category", "")).strip(),
            confidence=normalize_confidence(item.get("confidence")),
            reason=str(item.get("reason", "")).strip(),
        )
    return decisions


def split_batch_for_retry(batch: list[PostThread]) -> list[list[PostThread]]:
    if not batch:
        return []
    if len(batch) == 1 and len(batch[0].comments) > 1:
        thread = batch[0]
        midpoint = len(thread.comments) // 2
        return [
            [
                PostThread(
                    platform_name=thread.platform_name,
                    content_id=thread.content_id,
                    post_title=thread.post_title,
                    post_summary=thread.post_summary,
                    post_author=thread.post_author,
                    post_url=thread.post_url,
                    canonical_post_url=thread.canonical_post_url,
                    comments=thread.comments[:midpoint],
                )
            ],
            [
                PostThread(
                    platform_name=thread.platform_name,
                    content_id=thread.content_id,
                    post_title=thread.post_title,
                    post_summary=thread.post_summary,
                    post_author=thread.post_author,
                    post_url=thread.post_url,
                    canonical_post_url=thread.canonical_post_url,
                    comments=thread.comments[midpoint:],
                )
            ],
        ]

    midpoint = max(1, len(batch) // 2)
    return [batch[:midpoint], batch[midpoint:]]


def batch_threads(
    threads: list[PostThread],
    *,
    max_posts_per_batch: int,
    max_comments_per_batch: int,
) -> list[list[PostThread]]:
    normalized_threads: list[PostThread] = []
    for thread in threads:
        if len(thread.comments) <= max_comments_per_batch:
            normalized_threads.append(thread)
            continue

        for index in range(0, len(thread.comments), max_comments_per_batch):
            normalized_threads.append(
                PostThread(
                    platform_name=thread.platform_name,
                    content_id=thread.content_id,
                    post_title=thread.post_title,
                    post_summary=thread.post_summary,
                    post_author=thread.post_author,
                    post_url=thread.post_url,
                    canonical_post_url=thread.canonical_post_url,
                    comments=thread.comments[index : index + max_comments_per_batch],
                )
            )

    batches: list[list[PostThread]] = []
    current_batch: list[PostThread] = []
    current_comments = 0
    for thread in normalized_threads:
        thread_comment_count = len(thread.comments)
        too_many_posts = len(current_batch) >= max_posts_per_batch
        too_many_comments = current_batch and current_comments + thread_comment_count > max_comments_per_batch
        if too_many_posts or too_many_comments:
            batches.append(current_batch)
            current_batch = []
            current_comments = 0
        current_batch.append(thread)
        current_comments += thread_comment_count
    if current_batch:
        batches.append(current_batch)
    return batches


def build_batch_prompt(
    platform_name: str,
    batch: list[PostThread],
    *,
    require_all_comments: bool,
) -> str:
    serialized_threads = []
    for thread in batch:
        serialized_threads.append(
            {
                "content_id": thread.content_id,
                "post_title": truncate_text(thread.post_title or "无标题", limit=120),
                "post_summary": truncate_text(thread.post_summary or "", limit=180),
                "comments": [
                    {
                        "comment_id": comment.comment_id,
                        "comment_text": truncate_text(comment.comment_text, limit=180),
                    }
                    for comment in thread.comments
                ],
            }
        )

    if require_all_comments:
        return (
            "你是中文舆情分析助手。请根据帖子标题/摘要和评论文本，判断每条评论是否在针对本次会晤、访华、"
            "欢迎仪式或相关会谈表达明显反对、抵触、嘲讽或负面情绪。\n"
            "重点识别：直接反对这次会晤、认为不该来/没必要/应取消、把会晤说成作秀或闹剧、明显唱衰会谈结果、"
            "以及伴随辱骂挑衅的负面表态。\n"
            "不要把单纯事实转述、信息补充、普通提问、明确支持态度、或与这次会晤无关的情绪误判为有问题。\n\n"
            f"当前平台: {platform_name}\n"
            "请对每条记录返回：comment_id、is_problematic、sentiment、risk_level、category、confidence、reason。\n"
            "其中 is_problematic=true 表示该评论对本次会晤有明确反对或负面态度。\n"
            "sentiment 只能是 positive / neutral / negative。\n"
            "risk_level 只能是 none / low / medium / high。\n"
            "只返回 JSON，不要返回其他文字，格式如下：\n"
            "{\n"
            '  "items": [\n'
            "    {\n"
            '      "comment_id": "示例",\n'
            '      "is_problematic": true,\n'
            '      "sentiment": "negative",\n'
            '      "risk_level": "medium",\n'
            '      "category": "oppose_meeting",\n'
            '      "confidence": 0.82,\n'
            '      "reason": "明确说这场会谈早该取消，对本次会晤持反对态度"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"待分析数据：\n{json.dumps(serialized_threads, ensure_ascii=False, indent=2)}"
        )

    return (
        "你是中文舆情分析助手。请根据帖子标题/摘要和评论文本，筛选出对本次会晤、访华、欢迎仪式或相关会谈"
        "表达明显反对、抵触、嘲讽或负面情绪的评论。\n"
        "重点识别：认为这次会晤不该发生、应该取消、是在作秀/演戏/闹剧、明显唱衰结果、"
        "或带有辱骂挑衅的负面表态。\n"
        "不要返回单纯事实讨论、普通信息补充、中性疑问、明确支持态度，或与这次会晤无关的负面情绪。\n\n"
        f"当前平台: {platform_name}\n"
        "只返回有问题的评论，字段包括：comment_id、is_problematic、sentiment、risk_level、category、confidence、reason。\n"
        "其中 is_problematic=true 表示该评论对本次会晤有明确反对或负面态度。\n"
        "如果这一批全部都没有问题，返回 {\"items\": []}。\n"
        "sentiment 只能是 positive / neutral / negative。\n"
        "risk_level 只能是 none / low / medium / high。\n"
        "只返回 JSON，不要返回其他文字。\n\n"
        f"待分析数据：\n{json.dumps(serialized_threads, ensure_ascii=False, indent=2)}"
    )


def classify_batch_once(
    client: httpx.Client,
    model: str,
    platform_name: str,
    batch: list[PostThread],
    *,
    require_all_comments: bool,
) -> dict[str, CommentDecision]:
    response = client.post(
        "/api/generate",
        json={
            "model": model,
            "prompt": build_batch_prompt(
                platform_name,
                batch,
                require_all_comments=require_all_comments,
            ),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
    )
    response.raise_for_status()
    payload = response.json()
    raw_text = select_ollama_response_text(payload)
    decisions = parse_batch_decisions(raw_text)
    if require_all_comments:
        missing_ids = [
            comment.comment_id
            for thread in batch
            for comment in thread.comments
            if comment.comment_id not in decisions
        ]
        if missing_ids:
            raise ValueError(f"Missing decisions for comment ids: {missing_ids}")
    return decisions


def classify_batch(
    client: httpx.Client,
    model: str,
    platform_name: str,
    batch: list[PostThread],
    *,
    require_all_comments: bool,
) -> dict[str, CommentDecision]:
    try:
        return classify_batch_once(
            client,
            model,
            platform_name,
            batch,
            require_all_comments=require_all_comments,
        )
    except Exception:
        total_comments = sum(len(thread.comments) for thread in batch)
        if total_comments <= 1:
            raise

        decisions: dict[str, CommentDecision] = {}
        for sub_batch in split_batch_for_retry(batch):
            decisions.update(
                classify_batch(
                    client,
                    model,
                    platform_name,
                    sub_batch,
                    require_all_comments=require_all_comments,
                )
            )
        return decisions


def write_platform_output(
    platform_dir: Path,
    config: PlatformConfig,
    records: list[CommentRecord],
    decisions: dict[str, CommentDecision],
    *,
    include_safe: bool,
) -> Path:
    output_path = platform_dir / config.output_csv_name
    fieldnames = [
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
    rows: list[dict[str, str]] = []
    for record in records:
        decision = decisions.get(record.comment_id)
        if decision is None:
            if include_safe:
                raise KeyError(f"Missing decision for comment_id={record.comment_id}")
            continue
        if not include_safe and not decision.is_problematic:
            continue
        rows.append(
            {
                "platform": record.platform_name,
                "comment_id": record.comment_id,
                "content_id": record.content_id,
                "comment_author": record.comment_author,
                "comment_text": record.comment_text,
                "comment_like_count": record.comment_like_count,
                "parent_comment_id": record.parent_comment_id,
                "post_title": record.post_title,
                "post_summary": record.post_summary,
                "post_author": record.post_author,
                "post_url": record.post_url,
                "canonical_post_url": record.canonical_post_url,
                "is_problematic": decision.is_problematic,
                "sentiment": decision.sentiment,
                "risk_level": decision.risk_level,
                "category": decision.category,
                "confidence": decision.confidence,
                "reason": decision.reason,
            }
        )
    write_translated_csv_rows(output_path, "comment_risk_analysis", fieldnames, rows)
    return output_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    selected_platforms = args.platforms or sorted(PLATFORM_CONFIGS)
    configs = [PLATFORM_CONFIGS[platform_name] for platform_name in selected_platforms]
    grouped_records = collect_platform_records(
        args.csv_root,
        configs,
        limit_per_platform=args.limit_per_platform,
    )

    with httpx.Client(base_url=args.ollama_url, timeout=180.0) as client:
        for config in configs:
            records = grouped_records.get(config.platform_name, [])
            if not records:
                print(f"[SKIP] {config.platform_name}: no comments loaded")
                continue

            analysis_records = select_records_for_analysis(records, include_safe=args.include_safe)
            if not analysis_records and not args.include_safe:
                output_path = write_platform_output(
                    args.csv_root / config.directory_name,
                    config,
                    records,
                    decisions={},
                    include_safe=False,
                )
                print(
                    f"[DONE] {config.platform_name}: loaded={len(records)} "
                    f"candidates=0 flagged=0 output={output_path}"
                )
                continue

            threads = group_comment_threads(analysis_records)
            decisions: dict[str, CommentDecision] = {}
            batches = batch_threads(
                threads,
                max_posts_per_batch=args.max_posts_per_batch,
                max_comments_per_batch=args.max_comments_per_batch,
            )
            for index, batch in enumerate(batches, start=1):
                batch_decisions = classify_batch(
                    client,
                    args.model,
                    config.platform_name,
                    batch,
                    require_all_comments=args.include_safe,
                )
                decisions.update(batch_decisions)
                print(
                    f"[{config.platform_name}] batch {index}/{len(batches)} "
                    f"posts={len(batch)} comments={sum(len(thread.comments) for thread in batch)}"
                )

            output_path = write_platform_output(
                args.csv_root / config.directory_name,
                config,
                records,
                decisions,
                include_safe=args.include_safe,
            )
            flagged_count = sum(1 for decision in decisions.values() if decision.is_problematic)
            print(
                f"[DONE] {config.platform_name}: loaded={len(records)} "
                f"candidates={len(analysis_records)} "
                f"flagged={flagged_count} output={output_path}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
