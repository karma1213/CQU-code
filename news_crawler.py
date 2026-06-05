#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Domestic news aggregation crawler and static page generator."""

import html as html_lib
import json
import os
import re
import sys
from collections import namedtuple
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


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
        "url": "http://www.cctv.com/program/rss/02/01/index.xml",
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
    if not url:
        return ""
    parts = urlsplit(url.strip())
    path = re.sub(r"/+", "/", parts.path)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def parse_date(value):
    value = clean_text(value)
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CST)
        return dt.astimezone(CST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    match = re.search(r"(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})", value)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return value[:20]


def classify(title, summary="", default="国内"):
    content = f"{title} {summary}"
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in content for keyword in keywords):
            return category
    return default


def fetch_text(url):
    response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def fetch_rss(source):
    text = fetch_text(source["url"])
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text, count=1)
    root = ET.fromstring(text)
    items = []
    for node in root.findall(".//item")[:MAX_ITEMS_PER_SOURCE]:
        title = clean_text(node.findtext("title"), 120)
        link = clean_text(node.findtext("link"))
        summary = clean_text(node.findtext("description"), 140)
        date = parse_date(node.findtext("pubDate") or node.findtext("date"))
        if not title or not link:
            continue
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


def fetch_page_source(source):
    soup = BeautifulSoup(fetch_text(source["url"]), "html.parser")
    items = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        title = clean_text(anchor.get_text(" ", strip=True), 120)
        href = anchor.get("href", "")
        if len(title) < 8:
            continue
        if any(skip in title for skip in ["首页", "客户端", "微博", "微信", "搜索", "English"]):
            continue
        full_url = urljoin(source["base"], href)
        if not full_url.startswith("http"):
            continue
        if not any(domain in full_url for domain in ["news.cn", "xinhuanet.com", "cctv.com", "cctv.cn"]):
            continue
        key = normalize_url(full_url)
        if key in seen:
            continue
        seen.add(key)
        parent_text = clean_text(anchor.find_parent().get_text(" ", strip=True) if anchor.find_parent() else "")
        date = parse_date(parent_text)
        category = classify(title, parent_text, source["category"])
        items.append(NewsItem(source["id"], source["name"], category, title, full_url, date, "", "", []))
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
        score = str(entry.get("hotnum") or entry.get("hot") or entry.get("num") or entry.get("heat") or "")
        url = entry.get("url") or f"https://s.weibo.com/weibo?q={quote(title)}"
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


def fetch_weibo_hot():
    errors = []
    for api in WEIBO_APIS:
        try:
            response = requests.get(api, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            response.raise_for_status()
            payload = response.json()
            items = parse_weibo_payload(payload)
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
            key = f"weibo:{re.sub(r'^\\d+\\.\\s*', '', item.title)}"
        if not key:
            key = f"{item.source_id}:{item.title}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def select_balanced_items(items, limit):
    groups = {}
    order = []
    for item in items:
        key = item.source_id
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)

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


def crawl_all():
    all_items = []
    errors = []
    for source in RSS_SOURCES:
        try:
            all_items.extend(fetch_rss(source))
        except Exception as exc:
            errors.append({"source": source["name"], "message": str(exc)})
    for source in PAGE_SOURCES:
        try:
            all_items.extend(fetch_page_source(source))
        except Exception as exc:
            errors.append({"source": source["name"], "message": str(exc)})

    weibo_items, weibo_error = fetch_weibo_hot()
    all_items.extend(weibo_items)
    if weibo_error:
        errors.append({"source": "微博热搜", "message": weibo_error})

    items = dedupe_items(all_items)
    return select_balanced_items(items, MAX_TOTAL_ITEMS), errors


def html_escape(value):
    return html_lib.escape(str(value or ""), quote=True)


def generate_html(items, errors, crawl_time):
    total = len(items)
    now_str = crawl_time.strftime("%Y-%m-%d %H:%M:%S")
    source_counts = {}
    category_counts = {}
    for item in items:
        source_counts[item.source_name] = source_counts.get(item.source_name, 0) + 1
        category_counts[item.category] = category_counts.get(item.category, 0) + 1

    source_options = ['<option value="all">全部来源</option>']
    source_chips = ""
    for source_name, count in sorted(source_counts.items()):
        source_value = html_escape(source_name)
        source_options.append(f'<option value="{source_value}">{source_value}</option>')
        source_chips += f'<div class="source-chip"><span>{source_value}</span><strong>{count}</strong></div>'

    category_buttons = ""
    for category in CATEGORIES:
        count = total if category == "全部" else category_counts.get(category, 0)
        active = " active" if category == "全部" else ""
        category_buttons += (
            f'<button class="seg-btn{active}" type="button" data-category="{html_escape(category)}">'
            f"{html_escape(category)}<span>{count}</span></button>"
        )

    rows = ""
    for item in items:
        tags = "".join(f'<span class="tag">{html_escape(tag)}</span>' for tag in item.tags if tag)
        if item.hot_score:
            tags += f'<span class="tag hot">热度 {html_escape(item.hot_score)}</span>'
        rows += f"""
        <article class="news-item" data-url="{html_escape(item.url)}" data-title="{html_escape(item.title)}" data-source="{html_escape(item.source_name)}" data-category="{html_escape(item.category)}">
            <button class="icon-btn favorite-btn" type="button" data-action="favorite" aria-label="收藏新闻" title="收藏新闻">
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3.8l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6L7.1 19l.9-5.5-4-3.9 5.5-.8L12 3.8z"/></svg>
            </button>
            <div class="news-main">
                <div class="news-meta">
                    <span>{html_escape(item.source_name)}</span>
                    <span>{html_escape(item.category)}</span>
                    <time>{html_escape(item.date)}</time>
                </div>
                <a class="news-title" href="{html_escape(item.url)}" target="_blank" rel="noopener">{html_escape(item.title)}</a>
                <p>{html_escape(item.summary)}</p>
                <div class="tag-row">{tags}</div>
            </div>
            <button class="state-badge read-state" type="button" data-action="read-toggle">未读</button>
        </article>"""

    error_html = ""
    if errors:
        error_rows = "".join(
            f'<div class="source-error"><strong>{html_escape(err["source"])}</strong><span>{html_escape(err["message"])}</span></div>'
            for err in errors
        )
        error_html = f'<section class="error-panel"><h2>部分来源抓取失败</h2>{error_rows}</section>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国内新闻聚合</title>
<style>
  :root {{
    --bg:#f4f7fb; --bg2:#eaf0f8; --surface:#ffffff; --surface2:#f8fbff; --text:#1f2937;
    --muted:#5f6b7a; --soft:#8b98a8; --primary:#c53030; --primary2:#f97316; --gold:#b7791f;
    --cyan:#0f7595; --green:#047857; --border:#d9e2ee; --border2:#c7d3e2;
    --shadow:0 14px 34px rgba(31,41,55,.11); --radius:12px;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  html {{ color-scheme:light; }}
  body {{
    min-width:320px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
    background:
      radial-gradient(circle at 14% -10%, rgba(197,48,48,.12), transparent 32%),
      radial-gradient(circle at 84% 0%, rgba(15,117,149,.12), transparent 28%),
      linear-gradient(180deg,#fbfdff 0%,#f4f7fb 42%,#eef3f9 100%);
    color:var(--text); line-height:1.6;
  }}
  button,input,select {{ font:inherit; }}
  button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible {{ outline:3px solid rgba(15,117,149,.28); outline-offset:2px; }}
  .topbar {{
    color:var(--text); border-bottom:1px solid rgba(199,211,226,.86);
    background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(241,246,252,.92) 58%,rgba(255,242,232,.84));
    box-shadow:0 16px 42px rgba(31,41,55,.08);
  }}
  .topbar-inner {{ max-width:1240px; margin:0 auto; padding:30px 18px 24px; display:flex; justify-content:space-between; gap:18px; align-items:center; }}
  .brand {{ min-width:0; }}
  .eyebrow {{ font-size:.78rem; color:var(--cyan); letter-spacing:.12em; text-transform:uppercase; font-weight:800; }}
  h1 {{ margin-top:5px; font-size:clamp(1.55rem,3vw,2.45rem); line-height:1.12; letter-spacing:0; }}
  .topbar p {{ margin-top:9px; color:var(--muted); }}
  .meta-card {{ flex:0 0 auto; min-width:210px; text-align:right; border:1px solid var(--border); border-radius:16px; background:#fff; padding:13px 15px; box-shadow:var(--shadow); }}
  .meta-card strong {{ display:block; color:var(--primary); font-size:1.9rem; line-height:1; font-variant-numeric:tabular-nums; }}
  .container {{ max-width:1240px; margin:0 auto; padding:18px 14px 40px; }}
  .source-overview {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; margin-bottom:14px; }}
  .source-chip {{
    min-height:58px; display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 12px;
    background:linear-gradient(180deg,#fff,#f8fbff); border:1px solid var(--border);
    border-radius:var(--radius); box-shadow:0 8px 22px rgba(31,41,55,.07);
  }}
  .source-chip span {{ color:var(--muted); font-size:.82rem; line-height:1.3; }}
  .source-chip strong {{ color:var(--primary); font-size:1.25rem; font-variant-numeric:tabular-nums; }}
  .toolbar {{
    position:sticky; top:0; z-index:20; display:grid; grid-template-columns:minmax(230px,1fr) auto; gap:12px;
    padding:12px; margin-bottom:12px; background:rgba(255,255,255,.94); border:1px solid var(--border);
    border-radius:16px; box-shadow:var(--shadow); backdrop-filter:blur(14px);
  }}
  .filters,.actions {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
  .search-wrap {{ position:relative; flex:1 1 260px; min-width:220px; }}
  .search-wrap span {{ position:absolute; left:13px; top:50%; transform:translateY(-50%); color:var(--soft); }}
  .search-input,.select {{
    min-height:44px; border:1px solid var(--border2); border-radius:10px; background:#fff;
    padding:0 12px; color:var(--text); box-shadow:inset 0 1px 0 rgba(255,255,255,.75);
  }}
  .search-input::placeholder {{ color:#9aa6b5; }}
  .search-input {{ width:100%; padding-left:36px; }}
  .select {{ min-width:160px; }}
  .segment {{ display:flex; gap:3px; min-height:44px; padding:3px; border-radius:12px; border:1px solid var(--border); background:#eef3f9; overflow:auto; }}
  .seg-btn {{ border:0; border-radius:9px; background:transparent; color:var(--muted); cursor:pointer; padding:0 10px; font-weight:700; white-space:nowrap; }}
  .seg-btn span {{ margin-left:5px; color:var(--soft); font-size:.75rem; }}
  .seg-btn.active {{ background:linear-gradient(135deg,var(--primary),var(--primary2)); color:#fff; }}
  .seg-btn.active span {{ color:#fff; opacity:.8; }}
  .btn {{ min-height:44px; border:1px solid var(--border2); border-radius:10px; background:#fff; color:var(--muted); padding:0 14px; cursor:pointer; font-weight:700; }}
  .btn:hover {{ color:var(--text); border-color:#9db2ca; background:#f8fbff; }}
  .btn.primary {{ background:linear-gradient(135deg,var(--primary),var(--primary2)); color:#fff; border-color:transparent; box-shadow:0 10px 24px rgba(228,73,79,.18); }}
  .result-line {{ margin:0 3px 12px; color:var(--muted); font-size:.9rem; }}
  .result-line strong {{ color:var(--primary); }}
  .news-list {{ display:grid; gap:10px; }}
  .news-item {{
    position:relative; display:grid; grid-template-columns:44px minmax(0,1fr) auto; gap:10px; align-items:center;
    padding:12px 14px 12px 4px; border:1px solid var(--border); border-radius:var(--radius);
    background:linear-gradient(180deg,#fff,#fbfdff); box-shadow:0 8px 22px rgba(31,41,55,.08);
  }}
  .news-item::before {{ content:""; position:absolute; left:0; top:10px; bottom:10px; width:3px; border-radius:0 3px 3px 0; background:#b7c5d6; }}
  .news-item.hidden {{ display:none; }}
  .news-item.is-new::before {{ background:linear-gradient(180deg,var(--primary),var(--primary2)); box-shadow:0 0 16px rgba(255,107,53,.32); }}
  .news-item.is-read .news-title {{ color:#7b8796; }}
  .news-item.is-read .news-main p {{ color:#909baa; }}
  .news-item.is-favorite {{ border-color:rgba(183,121,31,.42); background:linear-gradient(90deg,rgba(255,247,214,.85),#fff 34%); }}
  .icon-btn {{ width:44px; height:44px; display:grid; place-items:center; border:0; background:transparent; cursor:pointer; color:var(--soft); }}
  .icon-btn svg {{ width:20px; height:20px; fill:none; stroke:currentColor; stroke-width:1.8; }}
  .news-item.is-favorite .favorite-btn {{ color:var(--gold); }}
  .news-item.is-favorite .favorite-btn svg {{ fill:currentColor; }}
  .news-main {{ min-width:0; }}
  .news-meta {{ display:flex; flex-wrap:wrap; gap:7px; color:var(--soft); font-size:.76rem; }}
  .news-meta span,.news-meta time {{ display:inline-flex; align-items:center; min-height:20px; padding:0 7px; border-radius:999px; background:#eef3f9; border:1px solid rgba(199,211,226,.9); }}
  .news-title {{ display:block; margin-top:5px; color:var(--text); text-decoration:none; font-weight:760; font-size:1rem; line-height:1.45; }}
  .news-title:hover {{ color:var(--cyan); }}
  .news-main p {{ margin-top:4px; color:var(--muted); font-size:.86rem; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .tag-row {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:7px; }}
  .tag {{ display:inline-flex; min-height:22px; align-items:center; border-radius:999px; padding:0 8px; background:#eef3f9; border:1px solid var(--border); color:var(--muted); font-size:.72rem; font-weight:700; }}
  .tag.hot {{ background:#fff1eb; border-color:#fed7c2; color:#c2410c; }}
  .state-badge {{ min-height:30px; border:1px solid var(--border2); border-radius:999px; padding:0 10px; background:#edf7fb; color:var(--cyan); cursor:pointer; font-weight:700; white-space:nowrap; }}
  .news-item.is-read .state-badge {{ color:#7b8796; background:#f1f4f8; }}
  .empty-results {{ display:none; text-align:center; padding:38px 16px; color:var(--muted); border:1px dashed var(--border2); border-radius:var(--radius); background:rgba(255,255,255,.78); }}
  .empty-results.show {{ display:block; }}
  .error-panel {{ margin-bottom:14px; padding:14px; border:1px solid #f7b4b4; border-radius:var(--radius); background:#fff5f5; }}
  .error-panel h2 {{ font-size:.95rem; color:var(--primary); margin-bottom:8px; }}
  .source-error {{ display:grid; gap:2px; color:var(--muted); font-size:.82rem; }}
  .source-error + .source-error {{ margin-top:8px; }}
  .toast {{ position:fixed; left:50%; bottom:24px; transform:translateX(-50%); z-index:999; opacity:0; pointer-events:none; background:#1f2937; color:#fff; padding:11px 20px; border-radius:12px; transition:opacity .2s, transform .2s; box-shadow:0 16px 36px rgba(31,41,55,.28); }}
  .toast.show {{ opacity:1; transform:translateX(-50%) translateY(-4px); }}
  footer {{ text-align:center; padding:22px 0 8px; color:var(--soft); font-size:.78rem; }}
  @media (max-width:760px) {{
    .topbar-inner {{ align-items:flex-start; padding:24px 14px 20px; }}
    .meta-card {{ display:none; }}
    .toolbar {{ grid-template-columns:1fr; }}
    .search-wrap,.select,.btn {{ flex:1 1 100%; min-width:0; }}
    .news-item {{ grid-template-columns:40px minmax(0,1fr); }}
    .state-badge {{ grid-column:2; justify-self:start; }}
  }}
</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="eyebrow">Domestic News Monitor</div>
      <h1>国内新闻聚合</h1>
      <p>新华社/新华网、央视网、中国新闻网、微博热搜聚合。更新于 <span id="updateTime">{html_escape(now_str)}</span></p>
    </div>
    <div class="meta-card"><strong>{total}</strong><span>条新闻</span></div>
  </div>
</header>
<main class="container">
  <section class="source-overview">{source_chips}</section>
  <section class="toolbar">
    <div class="filters">
      <label class="search-wrap"><span>⌕</span><input class="search-input" id="searchInput" type="search" placeholder="搜索标题、摘要、来源"></label>
      <select class="select" id="sourceFilter">{''.join(source_options)}</select>
      <select class="select" id="stateFilter">
        <option value="all">全部状态</option>
        <option value="new">新内容</option>
        <option value="favorite">收藏</option>
        <option value="unread">未读</option>
      </select>
    </div>
    <div class="actions">
      <div class="segment" id="categoryFilter">{category_buttons}</div>
      <button class="btn" type="button" onclick="markAllRead()">全部已读</button>
      <button class="btn primary" type="button" onclick="doRefresh()">刷新抓取</button>
    </div>
  </section>
  <div class="result-line" id="resultLine">当前显示 <strong>{total}</strong> 条新闻</div>
  <div class="empty-results" id="emptyResults">没有匹配的新闻。</div>
  {error_html}
  <section class="news-list">{rows}</section>
  <footer>数据来源于公开网页/RSS/热搜接口；页面状态保存在本机浏览器。</footer>
</main>
<div class="toast" id="toast"></div>
<script>
  var STORAGE_KEYS = {{
    favorites: 'news_item_favorites',
    read: 'news_item_read',
    seen: 'news_item_seen_urls'
  }};
  var activeCategory = '全部';

  function readSet(key) {{
    try {{ return new Set(JSON.parse(localStorage.getItem(key) || '[]')); }}
    catch (err) {{ return new Set(); }}
  }}
  function writeSet(key, set) {{ localStorage.setItem(key, JSON.stringify(Array.from(set))); }}
  function showToast(msg) {{
    var t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show';
    setTimeout(function() {{ t.className = 'toast'; }}, 2600);
  }}
  async function doRefresh() {{
    if (location.protocol === 'file:') {{
      showToast('请从桌面快捷方式打开，刷新按钮才能重新抓取');
      return;
    }}
    showToast('正在重新抓取新闻…');
    try {{
      var response = await fetch('/refresh', {{ method: 'POST', cache: 'no-store' }});
      var data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || '刷新失败');
      showToast('刷新完成，正在更新页面…');
      setTimeout(function() {{ location.reload(); }}, 500);
    }} catch (err) {{
      showToast(err.message || '刷新失败');
    }}
  }}
  function items() {{ return Array.prototype.slice.call(document.querySelectorAll('.news-item')); }}
  function applyItemState(item, favorites, read, seen) {{
    var url = item.dataset.url;
    var isFavorite = favorites.has(url);
    var isRead = read.has(url);
    var isNew = seen.size > 0 && !seen.has(url);
    item.classList.toggle('is-favorite', isFavorite);
    item.classList.toggle('is-read', isRead);
    item.classList.toggle('is-new', isNew);
    var favoriteBtn = item.querySelector('.favorite-btn');
    var readBtn = item.querySelector('.read-state');
    favoriteBtn.setAttribute('aria-pressed', isFavorite ? 'true' : 'false');
    readBtn.textContent = isRead ? '已读' : '未读';
  }}
  function syncState() {{
    var favorites = readSet(STORAGE_KEYS.favorites);
    var read = readSet(STORAGE_KEYS.read);
    var seen = readSet(STORAGE_KEYS.seen);
    var current = new Set();
    items().forEach(function(item) {{
      current.add(item.dataset.url);
      applyItemState(item, favorites, read, seen);
    }});
    current.forEach(function(url) {{ seen.add(url); }});
    writeSet(STORAGE_KEYS.seen, seen);
  }}
  function applyFilters() {{
    var query = (document.getElementById('searchInput').value || '').trim().toLowerCase();
    var source = document.getElementById('sourceFilter').value;
    var state = document.getElementById('stateFilter').value;
    var visibleCount = 0;
    items().forEach(function(item) {{
      var text = ((item.dataset.title || '') + ' ' + (item.dataset.source || '')).toLowerCase();
      var visible = (!query || text.indexOf(query) !== -1)
        && (source === 'all' || item.dataset.source === source)
        && (activeCategory === '全部' || item.dataset.category === activeCategory)
        && (state === 'all'
          || (state === 'new' && item.classList.contains('is-new'))
          || (state === 'favorite' && item.classList.contains('is-favorite'))
          || (state === 'unread' && !item.classList.contains('is-read')));
      item.classList.toggle('hidden', !visible);
      if (visible) visibleCount += 1;
    }});
    document.getElementById('resultLine').innerHTML = '当前显示 <strong>' + visibleCount + '</strong> 条新闻';
    document.getElementById('emptyResults').classList.toggle('show', visibleCount === 0);
  }}
  function toggleRead(item) {{
    var read = readSet(STORAGE_KEYS.read);
    if (read.has(item.dataset.url)) {{ read.delete(item.dataset.url); showToast('已标为未读'); }}
    else {{ read.add(item.dataset.url); showToast('已标为已读'); }}
    writeSet(STORAGE_KEYS.read, read);
    syncState();
    applyFilters();
  }}
  function markAllRead() {{
    var read = readSet(STORAGE_KEYS.read);
    items().forEach(function(item) {{ read.add(item.dataset.url); }});
    writeSet(STORAGE_KEYS.read, read);
    syncState();
    applyFilters();
    showToast('已全部标为已读');
  }}
  document.addEventListener('click', function(event) {{
    var favorite = event.target.closest('[data-action="favorite"]');
    if (favorite) {{
      var item = favorite.closest('.news-item');
      var favorites = readSet(STORAGE_KEYS.favorites);
      if (favorites.has(item.dataset.url)) {{ favorites.delete(item.dataset.url); showToast('已取消收藏'); }}
      else {{ favorites.add(item.dataset.url); showToast('已收藏'); }}
      writeSet(STORAGE_KEYS.favorites, favorites);
      syncState();
      applyFilters();
      return;
    }}
    var readToggle = event.target.closest('[data-action="read-toggle"]');
    if (readToggle) {{ toggleRead(readToggle.closest('.news-item')); return; }}
    var link = event.target.closest('.news-title');
    if (link) {{
      var row = link.closest('.news-item');
      var read = readSet(STORAGE_KEYS.read);
      read.add(row.dataset.url);
      writeSet(STORAGE_KEYS.read, read);
      syncState();
      applyFilters();
    }}
  }});
  document.addEventListener('DOMContentLoaded', function() {{
    syncState();
    applyFilters();
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('sourceFilter').addEventListener('change', applyFilters);
    document.getElementById('stateFilter').addEventListener('change', applyFilters);
    document.querySelectorAll('[data-category]').forEach(function(button) {{
      button.addEventListener('click', function() {{
        document.querySelectorAll('[data-category]').forEach(function(item) {{ item.classList.remove('active'); }});
        button.classList.add('active');
        activeCategory = button.dataset.category;
        applyFilters();
      }});
    }});
  }});
</script>
</body>
</html>"""
    return html


def main():
    print("=" * 50)
    print("国内新闻聚合爬虫")
    print(f"运行时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    items, errors = crawl_all()
    html = generate_html(items, errors, datetime.now(CST))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(html)
    print(f"共 {len(items)} 条新闻 → {OUTPUT_FILE}")
    if errors:
        print(f"部分来源失败: {len(errors)}")
        for err in errors:
            print(f"  [WARN] {err['source']}: {err['message']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
