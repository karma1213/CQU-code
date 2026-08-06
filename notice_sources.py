#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notice source definitions and HTML parsers for CQU public sites."""

from __future__ import annotations

import re

from crawler_utils import safe_http_url


MAX_ITEMS_PER_SOURCE = 25

# The order is user-facing: Civil Engineering is pinned first and Graduate
# School stays last.
SOURCES = [
    {
        "id": "civil",
        "name": "土木工程学院 — 通知公告",
        "url": "https://civil.cqu.edu.cn/xzwb/tzgg.htm",
        "base": "https://civil.cqu.edu.cn/xzwb/",
        "type": "civil",
    },
    {
        "id": "civil_gsgg",
        "name": "土木工程学院 — 公示公告",
        "url": "https://civil.cqu.edu.cn/xzwb/tzgg/gsgg.htm",
        "base": "https://civil.cqu.edu.cn/xzwb/",
        "type": "civil",
    },
    {
        "id": "cqu",
        "name": "重庆大学 — 通知公告",
        "url": "https://www.cqu.edu.cn/tzgg.htm",
        "base": "https://www.cqu.edu.cn/",
        "type": "cqu",
    },
    {
        "id": "xgb_xsgl",
        "name": "学工部 — 学生奖励",
        "url": "https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1006",
        "base": "https://xgb.cqu.edu.cn/",
        "type": "xgb",
    },
    {
        "id": "xgb_sizheng",
        "name": "学工部 — 学生事务",
        "url": "https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1005",
        "base": "https://xgb.cqu.edu.cn/",
        "type": "xgb",
    },
    {
        "id": "graduate",
        "name": "研究生院 — 通知公告",
        "url": "https://graduate.cqu.edu.cn/tzgg.htm",
        "base": "https://graduate.cqu.edu.cn/",
        "type": "graduate",
    },
]


def clean_title(title, max_len=120):
    """Normalize whitespace and cap unusually long source titles."""
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > max_len:
        title = title[:max_len] + "…"
    return title


def parse_cqu(soup, base):
    items = []
    excluded = [
        "重大新闻", "校情概", "机构设置", "教育教学", "科学研究", "招生就业",
        "人才招聘", "合作交流", "校园生活", "走进重大", "报告讲座", "科研动",
        "通知公告", "全媒矩阵", "休启乡",
    ]
    for li in soup.find_all("li"):
        anchor = li.find("a", href=True) if li else None
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        if len(title) < 8 or any(keyword in title for keyword in excluded):
            continue
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", title)
        if not date_match:
            continue
        date = date_match.group(1)
        clean = re.sub(r"^\d{4}-\d{2}-\d{2}～浏览量：", "", title)
        clean = re.sub(r"^\d{4}-\d{2}-\d{2}", "", clean)
        clean = re.sub(r"^[｜｜\s]*浏览数[：:]\s*", "", clean)
        full_url = safe_http_url(anchor["href"], base)
        if full_url:
            items.append((date, clean_title(clean), full_url))
    return items


def parse_xgb(soup, base):
    items = []
    content = soup.find("div", class_=re.compile(r"list-content", re.I))
    if not content:
        content = soup.find("div", class_=re.compile(r"main", re.I))
    if not content:
        return items
    for anchor in content.find_all("a", href=True):
        title = anchor.get_text(strip=True)
        if len(title) < 6 or title in ("首页", "更多+", "更多》"):
            continue
        parent = anchor.find_parent(["li", "div", "p"])
        full_text = parent.get_text(" ", strip=True) if parent else title
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", full_text)
        if not date_match:
            continue
        full_url = safe_http_url(anchor["href"], base)
        if full_url:
            items.append((date_match.group(1), clean_title(title), full_url))
    return items


def parse_graduate(soup, base):
    items = []
    content = soup.find("div", class_=re.compile(r"search-list", re.I))
    if not content:
        content = soup.find(
            "div", class_=re.compile(r"teacher-center-box-right", re.I)
        )
    if not content:
        return items

    for anchor in content.find_all("a", href=True):
        title = anchor.get_text(strip=True)
        href = anchor["href"]
        if len(title) < 8:
            continue
        date_match = re.match(r"(\d{2})(\d{4}-\d{2})", title)
        if not date_match:
            continue
        date = f"{date_match.group(2)}-{date_match.group(1)}"
        raw_title = title[len(date_match.group(0)):].lstrip(" \u200b\u3000")
        raw_title = re.sub(r"^[\[【][^\]】]*[\]】]\s*", "", raw_title)
        for separator in [
            "各相关单位", "各学院", "各研究生培养单位", "依据", "根据", "现将",
            "为进一步", "为推进", "为深入", "为贯彻", "为鼓励", "为积极", "为做好",
        ]:
            parts = re.split(
                rf"(?:{re.escape(separator)}[：:（(]?)", raw_title, maxsplit=1
            )
            if len(parts) > 1 and len(parts[0]) >= 8:
                raw_title = parts[0]
                break
        title_end = re.match(
            r"^(.+?(?:的通知|的公示|的决定|的启事|的报告|的办法|的公告|的安排|通知))",
            raw_title,
        )
        if title_end and len(title_end.group(1)) < len(raw_title) * 0.8:
            raw_title = title_end.group(1)
        if not href or href == "#":
            continue
        full_url = safe_http_url(href, base, allowed_hosts=("cqu.edu.cn",))
        if full_url:
            items.append((date, clean_title(raw_title), full_url))
    return items


def parse_civil(soup, base):
    items = []
    for li in soup.find_all("li"):
        anchor = li.find("a", href=True) if li else None
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        href = anchor["href"]
        if len(title) < 6 or "b2025/" in href or href.startswith("#"):
            continue
        date = ""
        span = li.find("span")
        if span:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", span.get_text())
            if match:
                date = match.group(1)
        if not date:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
            if match:
                date = match.group(1)
        if not date:
            continue
        full_url = safe_http_url(href, base, allowed_hosts=("cqu.edu.cn",))
        if full_url:
            items.append((date, clean_title(title), full_url))
    return items


def parse_source(source, soup):
    """Parse, deduplicate, sort and cap one already-fetched source document."""
    parser = {
        "cqu": parse_cqu,
        "xgb": parse_xgb,
        "graduate": parse_graduate,
        "civil": parse_civil,
    }.get(source["type"])
    if not parser:
        raise ValueError(f"未知来源类型: {source['type']}")
    seen = set()
    unique = []
    for date, title, url in parser(soup, source["base"]):
        key = url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            unique.append((date, title, url))
    unique.sort(key=lambda item: item[0], reverse=True)
    return unique[:MAX_ITEMS_PER_SOURCE]
