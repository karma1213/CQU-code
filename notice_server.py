#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local server for the CQU notice page.

The static page cannot start Python from a browser button, so this tiny local
server provides a same-origin /refresh endpoint that reruns the crawler.
"""

import os
import sys
import threading

import cqu_crawler
from site_server import StaticRefreshHandler, environment_port, serve


HOST = os.environ.get("HOST", "127.0.0.1")
PORT = environment_port(("PORT",), 8765)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "index.html")
_refresh_lock = threading.Lock()


class NoticeHandler(StaticRefreshHandler):
    directory = BASE_DIR
    page_name = "index.html"
    icon_name = "cqu_notice.ico"
    site_label = "CQU notices"
    refresh_callback = staticmethod(cqu_crawler.main)
    refresh_lock = _refresh_lock


def ensure_initial_page():
    if not os.path.exists(OUTPUT_FILE):
        cqu_crawler.main()


def main():
    ensure_initial_page()
    serve(HOST, PORT, NoticeHandler, "CQU notices")


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        if "address already in use" in str(exc).lower() or getattr(exc, "winerror", None) == 10048:
            sys.exit(0)
        raise
