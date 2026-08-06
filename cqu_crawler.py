#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch CQU notice sources and generate the local notice page."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

import browser_fetch
import notice_renderer
from crawler_utils import decode_response, write_text_atomic
from notice_sources import (
    MAX_ITEMS_PER_SOURCE,
    SOURCES,
    clean_title,
    parse_civil,
    parse_cqu,
    parse_graduate,
    parse_source,
    parse_xgb,
)


try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
REQUEST_TIMEOUT = 20
CST = timezone(timedelta(hours=8))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}


class WafRequired(RuntimeError):
    """Signal that an HTTP source must be fetched by the browser batch."""

    def __init__(self, url):
        super().__init__(f"HTTP 412 Precondition Failed: {url}")
        self.url = url


def _request_soup(url, http_session):
    try:
        response = http_session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 412:
            raise WafRequired(url) from exc
        raise
    try:
        decoded = decode_response(response)
    except requests.HTTPError as exc:
        failed = exc.response or response
        if failed.status_code == 412:
            raise WafRequired(url) from exc
        raise
    return BeautifulSoup(decoded, "html.parser"), response.status_code


def fetch_page(url):
    """Compatibility wrapper that fetches one URL with browser fallback."""
    try:
        soup, _ = _request_soup(url, requests)
        return soup
    except WafRequired as exc:
        if not browser_fetch.enabled():
            raise RuntimeError(
                f"HTTP 412 Precondition Failed（浏览器回退已禁用）: {url}"
            ) from exc
        try:
            rendered = browser_fetch.fetch_html(
                url, [source["url"] for source in SOURCES]
            )
        except browser_fetch.BrowserFetchError as browser_exc:
            raise RuntimeError(
                f"HTTP 412 Precondition Failed，浏览器回退失败: {browser_exc}"
            ) from browser_exc
        return BeautifulSoup(rendered, "html.parser")


def crawl_source(source):
    """Compatibility wrapper for callers that still crawl one source."""
    print(f"正在抓取: {source['name']}")
    return parse_source(source, fetch_page(source["url"]))


def _retry_count(session):
    value = getattr(session, "retry_count", 0)
    return value if isinstance(value, int) else 0


def _new_metric(source):
    return {
        "source_id": source["id"],
        "source": source["name"],
        "status": "pending",
        "item_count": 0,
        "duration_ms": 0,
        "error": "",
        "browser_used": False,
        "retry_count": 0,
        "http_status": None,
    }


def crawl_sources(sources=None, http_session=None):
    """Fetch all sources in an HTTP phase followed by one browser batch."""
    sources = list(SOURCES if sources is None else sources)
    result_items = {source["id"]: [] for source in sources}
    metrics = {source["id"]: _new_metric(source) for source in sources}
    errors = []
    blocked = []
    owns_http_session = http_session is None
    client = http_session or requests.Session()

    try:
        for source in sources:
            started = time.monotonic()
            print(f"正在抓取: {source['name']}")
            metric = metrics[source["id"]]
            try:
                soup, status_code = _request_soup(source["url"], client)
                metric["http_status"] = status_code
                items = parse_source(source, soup)
            except WafRequired:
                metric["http_status"] = 412
                metric["status"] = "waf_required"
                metric["browser_used"] = True
                blocked.append((source, started))
                continue
            except Exception as exc:
                metric["status"] = "error"
                metric["error"] = str(exc)
                metric["duration_ms"] = round((time.monotonic() - started) * 1000)
                errors.append({"source": source["name"], "message": str(exc)})
                print(f"  [WARN] HTTP 抓取失败: {exc}")
                continue

            result_items[source["id"]] = items
            metric["status"] = "ok" if items else "empty"
            metric["item_count"] = len(items)
            metric["duration_ms"] = round((time.monotonic() - started) * 1000)
            print(f"  [OK] HTTP {status_code}, {len(items)} 条")

        if blocked:
            _fetch_blocked_sources(blocked, result_items, metrics, errors)
    finally:
        if owns_http_session:
            client.close()

    all_results = [(source, result_items[source["id"]]) for source in sources]
    return all_results, errors, [metrics[source["id"]] for source in sources]


def _fetch_blocked_sources(blocked, result_items, metrics, errors):
    blocked_urls = [source["url"] for source, _ in blocked]
    if not browser_fetch.enabled():
        message = "浏览器回退已通过 CQU_BROWSER_FETCH=0 禁用"
        for source, started in blocked:
            metric = metrics[source["id"]]
            metric["status"] = "error"
            metric["error"] = message
            metric["duration_ms"] = round((time.monotonic() - started) * 1000)
            errors.append({"source": source["name"], "message": message})
        return

    body_completed = False
    try:
        with browser_fetch.BrowserSession(blocked_urls) as browser:
            for source, started in blocked:
                metric = metrics[source["id"]]
                retry_before = _retry_count(browser)
                try:
                    rendered = browser.fetch(source["url"])
                    items = parse_source(
                        source, BeautifulSoup(rendered, "html.parser")
                    )
                except Exception as exc:
                    metric["status"] = "error"
                    metric["error"] = str(exc)
                    errors.append({"source": source["name"], "message": str(exc)})
                    print(f"  [WARN] 浏览器抓取失败: {exc}")
                else:
                    result_items[source["id"]] = items
                    metric["status"] = "ok" if items else "empty"
                    metric["item_count"] = len(items)
                    print(f"  [OK] 浏览器, {len(items)} 条")
                finally:
                    metric["retry_count"] = max(
                        0, _retry_count(browser) - retry_before
                    )
                    metric["duration_ms"] = round(
                        (time.monotonic() - started) * 1000
                    )
            body_completed = True
    except browser_fetch.BrowserFetchError as exc:
        if body_completed:
            raise
        for source, started in blocked:
            metric = metrics[source["id"]]
            if metric["status"] not in {"waf_required", "pending"}:
                continue
            metric["status"] = "error"
            metric["error"] = str(exc)
            metric["duration_ms"] = round((time.monotonic() - started) * 1000)
            errors.append({"source": source["name"], "message": str(exc)})


generate_html = notice_renderer.generate_html


def main():
    print("=" * 50)
    print("重庆大学通知公告爬虫")
    print(f"运行时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    all_results, errors, metrics = crawl_sources(SOURCES)
    total = sum(len(items) for _, items in all_results)
    for metric in metrics:
        print(
            "  [SOURCE] "
            f"{metric['source_id']} status={metric['status']} "
            f"items={metric['item_count']} duration_ms={metric['duration_ms']} "
            f"browser={metric['browser_used']} retry={metric['retry_count']}"
        )

    if total == 0:
        detail = f"，失败来源 {len(errors)}/{len(SOURCES)}" if errors else ""
        if os.path.exists(OUTPUT_FILE):
            raise RuntimeError(f"未抓取到任何通知{detail}；已保留上一版页面")
        initial_errors = errors or [
            {"source": "全部来源", "message": "暂无可用通知数据"}
        ]
        write_text_atomic(
            OUTPUT_FILE, generate_html([], datetime.now(CST), initial_errors)
        )
        print(f"未抓取到通知，已生成空状态页面 → {OUTPUT_FILE}")
        return

    write_text_atomic(
        OUTPUT_FILE, generate_html(all_results, datetime.now(CST), errors)
    )
    print(f"\n{'=' * 50}")
    print(f"共 {total} 条通知 → {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
