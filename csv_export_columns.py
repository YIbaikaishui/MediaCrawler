from __future__ import annotations

import csv
from pathlib import Path


CSV_COLUMN_NAME_MAPS: dict[str, dict[str, str]] = {
    "bilibili_up_info": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "sex": "性别",
        "sign": "签名",
        "avatar": "头像链接",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "total_fans": "粉丝数",
        "total_liked": "总获赞数",
        "user_rank": "用户等级",
        "is_official": "是否认证",
    },
    "bilibili_video": {
        "id": "编号",
        "video_id": "视频ID",
        "video_url": "视频链接",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "liked_count": "点赞数",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "video_type": "视频类型",
        "title": "标题",
        "desc": "简介",
        "create_time": "发布时间戳",
        "disliked_count": "点踩数",
        "video_play_count": "播放量",
        "video_favorite_count": "收藏数",
        "video_share_count": "分享数",
        "video_coin_count": "投币数",
        "video_danmaku": "弹幕数",
        "video_comment": "评论数",
        "video_cover_url": "封面链接",
        "source_keyword": "来源关键词",
    },
    "bilibili_video_comment": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "sex": "性别",
        "sign": "签名",
        "avatar": "头像链接",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "comment_id": "评论ID",
        "video_id": "视频ID",
        "content": "评论内容",
        "create_time": "发布时间戳",
        "sub_comment_count": "子评论数",
        "parent_comment_id": "父评论ID",
        "like_count": "点赞数",
    },
    "kuaishou_video": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "video_id": "视频ID",
        "video_type": "视频类型",
        "title": "标题",
        "desc": "简介",
        "create_time": "发布时间戳",
        "liked_count": "点赞数",
        "viewd_count": "播放量",
        "video_url": "视频链接",
        "video_cover_url": "封面链接",
        "video_play_url": "视频播放链接",
        "source_keyword": "来源关键词",
    },
    "kuaishou_video_comment": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "comment_id": "评论ID",
        "video_id": "视频ID",
        "content": "评论内容",
        "create_time": "发布时间戳",
        "sub_comment_count": "子评论数",
    },
    "weibo_note": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "gender": "性别",
        "profile_url": "主页链接",
        "ip_location": "IP归属地",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "note_id": "博文ID",
        "content": "博文内容",
        "create_time": "发布时间戳",
        "create_date_time": "发布时间",
        "liked_count": "点赞数",
        "comments_count": "评论数",
        "shared_count": "转发数",
        "note_url": "博文链接",
        "source_keyword": "来源关键词",
    },
    "weibo_note_comment": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "gender": "性别",
        "profile_url": "主页链接",
        "ip_location": "IP归属地",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "comment_id": "评论ID",
        "note_id": "博文ID",
        "content": "评论内容",
        "create_time": "发布时间戳",
        "create_date_time": "发布时间",
        "comment_like_count": "点赞数",
        "sub_comment_count": "子评论数",
        "parent_comment_id": "父评论ID",
    },
    "xhs_note": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "ip_location": "IP归属地",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "note_id": "笔记ID",
        "type": "内容类型",
        "title": "标题",
        "desc": "简介",
        "video_url": "视频链接",
        "time": "发布时间戳",
        "last_update_time": "内容更新时间戳",
        "liked_count": "点赞数",
        "collected_count": "收藏数",
        "comment_count": "评论数",
        "share_count": "分享数",
        "image_list": "图片列表",
        "tag_list": "话题标签",
        "note_url": "笔记链接",
        "source_keyword": "来源关键词",
        "xsec_token": "xsec令牌",
    },
    "xhs_note_comment": {
        "id": "编号",
        "user_id": "用户ID",
        "nickname": "昵称",
        "avatar": "头像链接",
        "ip_location": "IP归属地",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
        "comment_id": "评论ID",
        "create_time": "发布时间戳",
        "note_id": "笔记ID",
        "content": "评论内容",
        "sub_comment_count": "子评论数",
        "pictures": "图片列表",
        "parent_comment_id": "父评论ID",
        "like_count": "点赞数",
    },
    "zhihu_content": {
        "id": "编号",
        "content_id": "内容ID",
        "content_type": "内容类型",
        "content_text": "内容正文",
        "content_url": "内容链接",
        "question_id": "问题ID",
        "title": "标题",
        "desc": "摘要",
        "created_time": "创建时间",
        "updated_time": "更新时间",
        "voteup_count": "赞同数",
        "comment_count": "评论数",
        "source_keyword": "来源关键词",
        "user_id": "用户ID",
        "user_link": "用户主页链接",
        "user_nickname": "用户昵称",
        "user_avatar": "用户头像链接",
        "user_url_token": "用户令牌",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
    },
    "zhihu_comment": {
        "id": "编号",
        "comment_id": "评论ID",
        "parent_comment_id": "父评论ID",
        "content": "评论内容",
        "publish_time": "发布时间",
        "ip_location": "IP归属地",
        "sub_comment_count": "子评论数",
        "like_count": "点赞数",
        "dislike_count": "点踩数",
        "content_id": "内容ID",
        "content_type": "内容类型",
        "user_id": "用户ID",
        "user_link": "用户主页链接",
        "user_nickname": "用户昵称",
        "user_avatar": "用户头像链接",
        "add_ts": "采集时间戳",
        "last_modify_ts": "最后更新时间戳",
    },
    "comment_risk_analysis": {
        "platform": "平台",
        "comment_id": "评论ID",
        "content_id": "内容ID",
        "comment_author": "评论作者",
        "comment_text": "评论内容",
        "comment_like_count": "评论点赞数",
        "parent_comment_id": "父评论ID",
        "post_title": "帖子标题",
        "post_summary": "帖子摘要",
        "post_author": "帖子作者",
        "post_url": "帖子链接",
        "canonical_post_url": "标准帖子链接",
        "is_problematic": "是否为负面评论",
        "sentiment": "情绪倾向",
        "risk_level": "风险等级",
        "category": "分类",
        "confidence": "置信度",
        "reason": "原因",
    },
    "merged_comment_risk_analysis": {
        "platform": "平台",
        "comment_id": "评论ID",
        "content_id": "内容ID",
        "comment_author": "评论作者",
        "comment_text": "评论内容",
        "comment_like_count": "评论点赞数",
        "parent_comment_id": "父评论ID",
        "post_title": "帖子标题",
        "post_summary": "帖子摘要",
        "post_author": "帖子作者",
        "post_url": "帖子链接",
        "canonical_post_url": "标准帖子链接",
        "is_problematic": "是否为负面评论",
        "sentiment": "情绪倾向",
        "risk_level": "风险等级",
        "category": "分类",
        "confidence": "置信度",
        "reason": "原因",
    },
    "top_negative_comment_risk_analysis": {
        "rank": "排名",
        "negativity_score": "负面强度分",
        "intensity_bucket": "强度分层",
        "platform": "平台",
        "comment_id": "评论ID",
        "content_id": "内容ID",
        "comment_author": "评论作者",
        "comment_text": "评论内容",
        "comment_like_count": "评论点赞数",
        "parent_comment_id": "父评论ID",
        "post_title": "帖子标题",
        "post_summary": "帖子摘要",
        "post_author": "帖子作者",
        "post_url": "帖子链接",
        "canonical_post_url": "标准帖子链接",
        "is_problematic": "是否为负面评论",
        "sentiment": "情绪倾向",
        "risk_level": "风险等级",
        "category": "分类",
        "confidence": "置信度",
        "reason": "原因",
    },
}


def get_column_name_map(file_key: str) -> dict[str, str]:
    return CSV_COLUMN_NAME_MAPS.get(file_key, {})


def get_reverse_column_name_map(file_key: str) -> dict[str, str]:
    column_name_map = get_column_name_map(file_key)
    return {chinese: english for english, chinese in column_name_map.items()}


def translate_fieldnames(fieldnames: list[str], file_key: str) -> list[str]:
    column_name_map = get_column_name_map(file_key)
    return [column_name_map.get(fieldname, fieldname) for fieldname in fieldnames]


def canonicalize_fieldnames(fieldnames: list[str], file_key: str) -> list[str]:
    reverse_column_name_map = get_reverse_column_name_map(file_key)
    return [reverse_column_name_map.get(fieldname, fieldname) for fieldname in fieldnames]


def canonicalize_row(row: dict[str, str], file_key: str) -> dict[str, str]:
    reverse_column_name_map = get_reverse_column_name_map(file_key)
    return {reverse_column_name_map.get(key, key): value for key, value in row.items()}


def read_csv_rows(path: Path, file_key: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [canonicalize_row(dict(row), file_key) for row in reader]


def write_csv_rows(path: Path, file_key: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    translated_fieldnames = translate_fieldnames(fieldnames, file_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=translated_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    translated_fieldname: row.get(fieldname, "")
                    for fieldname, translated_fieldname in zip(fieldnames, translated_fieldnames, strict=True)
                }
            )
