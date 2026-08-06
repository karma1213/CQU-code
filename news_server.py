#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local HTTP server for the domestic news aggregation site."""

import os
import sys
import threading

import news_crawler
from site_server import StaticRefreshHandler, environment_port, serve


HOST = os.environ.get("NEWS_HOST", os.environ.get("HOST", "127.0.0.1"))
PORT = environment_port(("NEWS_PORT", "PORT"), 8766)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "news.html")
_refresh_lock = threading.Lock()


class NewsHandler(StaticRefreshHandler):
    directory = BASE_DIR
    page_name = "news.html"
    icon_name = "news_site.ico"
    site_label = "domestic news"
    refresh_callback = staticmethod(news_crawler.main)
    refresh_lock = _refresh_lock


def ensure_initial_page():
    if not os.path.exists(OUTPUT_FILE):
        news_crawler.main()


def main():
    ensure_initial_page()
    serve(HOST, PORT, NewsHandler, "domestic news")


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        if "address already in use" in str(exc).lower() or getattr(exc, "winerror", None) == 10048:
            sys.exit(0)
        raise
