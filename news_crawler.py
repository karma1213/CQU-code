#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch domestic news sources and generate the local news page."""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

import news_renderer
from crawler_utils import decode_response, safe_http_url, write_text_atomic


try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "news.html")
REQUEST_TIMEOUT = 18
MAX_ITEMS_PER_SOURCE = 30
MAX_TOTAL_ITEMS = 140
CST = timezone(timedelta(hours=8))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}

NewsItem = namedtuple(
    "NewsItem",
    "source_id source_name category title url date summary hot_score tags",
)

RSS_SOURCES = [
    {
        "id": "chinanews_china",
        "name": "中国新闻网 · 时政",
        "category": "国内",
        "url": "https://www.chinanews.com.cn/rss/china.xml",
    },
    {
        "id": "chinanews_society",
        "name": "中国新闻网 · 社会",
        "category": "社会",
        "url": "https://www.chinanews.com.cn/rss/society.xml",
    },
    {
        "id": "chinanews_finance",
        "name": "中国新闻网 · 财经",
        "category": "财经",
        "url": "https://www.chinanews.com.cn/rss/finance.xml",
    },
    {
        "id": "chinanews_world",
        "name": "中国新闻网 · 国际",
        "category": "国际",
        "url": "https://www.chinanews.com.cn/rss/world.xml",
    },
    {
        "id": "cctv_domestic_rss",
        "name": "央视网新闻 · 国内",
        "category": "国内",
        "url": "https://www.cctv.com/program/rss/02/01/index.xml",
    },
]

PAGE_SOURCES = [
    {
        "id": "xinhua_politics",
        "name": "新华网 · 时政",
        "category": "主线",
        "url": "https://www.news.cn/politics/",
        "base": "https://www.news.cn/politics/",
    },
    {
        "id": "xinhua_news",
        "name": "新华网 · 要闻",
        "category": "主线",
        "url": "https://www.news.cn/",
        "base": "https://www.news.cn/",
    },
    {
        "id": "cctv_china",
        "name": "央视网新闻 · 中国",
        "category": "国内",
        "url": "https://news.cctv.com/china/",
        "base": "https://news.cctv.com/",
    },
    {
        "id": "cctv_news",
        "name": "央视网新闻",
        "category": "国内",
        "url": "https://news.cctv.com/",
        "base": "https://news.cctv.com/",
    },
]

WEIBO_APIS = [
    "https://v2.xxapi.cn/api/weibohot",
    "https://api.xk.ee/hot/weibo.php",
]

CATEGORY_KEYWORDS = [
    ("会议", ["会议", "全会", "常委会", "代表大会", "座谈会", "论坛", "峰会"]),
    ("政策", ["政策", "条例", "办法", "意见", "通知", "规划", "方案", "决定", "发布", "国务院"]),
    ("主线", ["习近平", "党中央", "中央", "新华社", "总书记", "重要讲话", "主线"]),
    ("财经", ["经济", "金融", "股市", "财政", "产业", "消费", "企业", "市场"]),
    ("国际", ["国际", "外交", "美国", "俄罗斯", "欧洲", "联合国", "全球"]),
    ("社会", ["社会", "民生", "教育", "医疗", "就业", "交通", "天气"]),
    ("视频", ["视频", "新闻联播", "报道", "总台"]),
]

CATEGORIES = ["全部", "主线", "会议", "政策", "国内", "社会", "财经", "国际", "视频", "热搜"]


def clean_text(value, max_len=None):
    text = re.sub(r"\s+", " ", value or "").strip()
    if max_len and len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def normalize_url(url):
    normalized = safe_http_url(url)
    if not normalized:
        return ""
    parts = urlsplit(normalized)
    path = re.sub(r"/+", "/", parts.path)
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, parts.query, "")
    )


def parse_date(value):
    value = clean_text(value)
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=CST)
        return parsed.astimezone(CST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=CST)
        return parsed.astimezone(CST).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        pass
    match = re.search(r"(\d{4})\D{1,3}(\d{1,2})\D{1,3}(\d{1,2})", value)
    if match:
        return (
            f"{match.group(1)}-{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )
    return ""


def classify(title, summary="", default="国内"):
    content = f"{title} {summary}"
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in content for keyword in keywords):
            return category
    return default


def fetch_text(url, session=None):
    """Fetch one source document, optionally through a shared Session."""
    client = session or requests
    response = client.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    return decode_response(response)


def _xml_local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _xml_child_text(node, *names):
    wanted = {name.lower() for name in names}
    for child in list(node):
        if _xml_local_name(child.tag) not in wanted:
            continue
        href = child.attrib.get("href")
        if href:
            return href
        return "".join(child.itertext()).strip()
    return ""


def fetch_rss(source, session=None):
    """Parse both RSS ``item`` and Atom ``entry`` documents."""
    text = re.sub(
        r"^\s*<\?xml[^>]*?>", "", fetch_text(source["url"], session), count=1
    )
    root = ET.fromstring(text)
    entries = [
        node
        for node in root.iter()
        if _xml_local_name(node.tag) in {"item", "entry"}
    ]
    items = []
    for node in entries[:MAX_ITEMS_PER_SOURCE]:
        title = clean_text(_xml_child_text(node, "title"), 120)
        link = safe_http_url(clean_text(_xml_child_text(node, "link")))
        summary_markup = _xml_child_text(node, "description", "summary", "content")
        summary = clean_text(
            BeautifulSoup(summary_markup, "html.parser").get_text(" ", strip=True),
            140,
        )
        date = parse_date(
            _xml_child_text(node, "pubDate", "published", "updated", "date")
        )
        if title and link:
            items.append(
                NewsItem(
                    source["id"],
                    source["name"],
                    classify(title, summary, source["category"]),
                    title,
                    link,
                    date,
                    summary,
                    "",
                    [],
                )
            )
    return items


def _looks_like_article_url(url):
    path = urlsplit(url).path.lower().rstrip("/")
    if not path or path.endswith((".jpg", ".jpeg", ".png", ".gif", ".css", ".js")):
        return False
    return bool(
        re.search(r"(?:\d{4}[-_/]\d{1,2}[-_/]\d{1,2})", path)
        or re.search(r"/(?:article|content|news|detail)(?:/|$)", path)
        or re.search(r"\.(?:s?html?|shtml)$", path)
    )


def fetch_page_source(source, session=None):
    soup = BeautifulSoup(fetch_text(source["url"], session), "html.parser")
    items = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        title = clean_text(anchor.get_text(" ", strip=True), 120)
        if len(title) < 8 or any(
            word in title
            for word in [
                "首页", "客户端", "微博", "微信", "搜索", "English", "Español",
                "Français", "Deutsch", "Русский", "عربي", "日本語", "한국어",
            ]
        ):
            continue
        full_url = safe_http_url(
            anchor.get("href", ""),
            source["base"],
            allowed_hosts=("news.cn", "xinhuanet.com", "cctv.com", "cctv.cn"),
        )
        if not full_url:
            continue
        if not _looks_like_article_url(full_url):
            continue
        source_host = (urlsplit(source["base"]).hostname or "").lower()
        target_host = (urlsplit(full_url).hostname or "").lower()
        if source_host == "www.news.cn" and target_host != source_host:
            continue
        key = normalize_url(full_url)
        if key in seen:
            continue
        seen.add(key)
        parent = anchor.find_parent()
        parent_text = clean_text(
            parent.get_text(" ", strip=True) if parent else ""
        )
        items.append(
            NewsItem(
                source["id"],
                source["name"],
                classify(title, parent_text, source["category"]),
                title,
                full_url,
                parse_date(parent_text),
                "",
                "",
                [],
            )
        )
        if len(items) >= MAX_ITEMS_PER_SOURCE:
            break
    return items


def parse_weibo_payload(payload):
    candidates = payload
    for key in ["data", "result", "list", "hot", "newslist"]:
        if isinstance(candidates, dict) and key in candidates:
            candidates = candidates[key]
    if isinstance(candidates, dict):
        for key in ["data", "list", "hot"]:
            if key in candidates:
                candidates = candidates[key]
                break
    if not isinstance(candidates, list):
        return []

    items = []
    for index, entry in enumerate(candidates[:50], start=1):
        if not isinstance(entry, dict):
            continue
        title = clean_text(
            entry.get("title")
            or entry.get("word")
            or entry.get("name")
            or entry.get("keyword")
            or entry.get("query"),
            80,
        )
        if not title:
            continue
        score = str(
            entry.get("hotnum")
            or entry.get("hot")
            or entry.get("num")
            or entry.get("heat")
            or ""
        )
        url = safe_http_url(entry.get("url")) or (
            f"https://s.weibo.com/weibo?q={quote(title)}"
        )
        tag = clean_text(entry.get("tag") or entry.get("label") or "")
        items.append(
            NewsItem(
                "weibo_hot",
                "微博热搜",
                "热搜",
                f"{index}. {title}",
                url,
                datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
                tag,
                score,
                [tag] if tag else [],
            )
        )
    return items


def fetch_weibo_hot(session=None):
    errors = []
    client = session or requests
    for api in WEIBO_APIS:
        try:
            response = client.get(api, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            response.raise_for_status()
            items = parse_weibo_payload(response.json())
            if items:
                return items[:MAX_ITEMS_PER_SOURCE], None
            errors.append(f"{api}: empty payload")
        except Exception as exc:
            errors.append(f"{api}: {exc}")
    return [], "；".join(errors[-2:])


def dedupe_items(items):
    seen = set()
    result = []
    for item in items:
        key = normalize_url(item.url) if item.url else ""
        if item.source_id == "weibo_hot":
            key = "weibo:" + re.sub(r"^\d+\.\s*", "", item.title)
        if not key:
            key = f"{item.source_id}:{item.title}"
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def select_balanced_items(items, limit):
    groups = {}
    order = []
    for item in items:
        if item.source_id not in groups:
            groups[item.source_id] = []
            order.append(item.source_id)
        groups[item.source_id].append(item)

    selected = []
    index = 0
    while len(selected) < limit:
        added = False
        for key in order:
            group = groups[key]
            if index < len(group):
                selected.append(group[index])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        index += 1
    return selected


def _crawl_one(kind, source, session):
    if kind == "rss":
        return fetch_rss(source, session)
    return fetch_page_source(source, session)


def crawl_all():
    """Fetch independent news sources concurrently with one HTTP session."""
    all_items = []
    errors = []
    jobs = [("rss", source) for source in RSS_SOURCES]
    jobs.extend(("page", source) for source in PAGE_SOURCES)
    raw_workers = os.environ.get("CQU_NEWS_WORKERS", "4")
    try:
        worker_count = int(raw_workers)
    except ValueError:
        worker_count = 4
    worker_count = max(1, min(6, worker_count))

    with requests.Session() as session:
        session.headers.update(HEADERS)
        with ThreadPoolExecutor(max_workers=min(worker_count, len(jobs))) as pool:
            futures = [
                pool.submit(_crawl_one, kind, source, session)
                for kind, source in jobs
            ]
            for (kind, source), future in zip(jobs, futures):
                try:
                    all_items.extend(future.result())
                except Exception as exc:
                    errors.append({"source": source["name"], "message": str(exc)})

        try:
            weibo_items, weibo_error = fetch_weibo_hot(session)
        except Exception as exc:
            weibo_items, weibo_error = [], str(exc)
        all_items.extend(weibo_items)
        if weibo_error:
            errors.append({"source": "微博热搜", "message": weibo_error})

    items = dedupe_items(all_items)
    return select_balanced_items(items, MAX_TOTAL_ITEMS), errors


generate_html = news_renderer.generate_html


def main():
    print("=" * 50)
    print("国内新闻聚合爬虫")
    print(f"运行时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    items, errors = crawl_all()
    if not items:
        detail = f"，失败来源 {len(errors)}" if errors else ""
        if os.path.exists(OUTPUT_FILE):
            raise RuntimeError(f"未抓取到任何新闻{detail}；已保留上一版页面")
        initial_errors = errors or [
            {"source": "全部来源", "message": "暂无可用新闻数据"}
        ]
        write_text_atomic(
            OUTPUT_FILE, generate_html([], initial_errors, datetime.now(CST))
        )
        print(f"未抓取到新闻，已生成空状态页面 → {OUTPUT_FILE}")
        return
    write_text_atomic(
        OUTPUT_FILE, generate_html(items, errors, datetime.now(CST))
    )
    print(f"共 {len(items)} 条新闻 → {OUTPUT_FILE}")
    if errors:
        print(f"部分来源失败: {len(errors)}")
        for error in errors:
            print(f"  [WARN] {error['source']}: {error['message']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
