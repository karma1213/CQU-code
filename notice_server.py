#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local server for the CQU notice page.

The static page cannot start Python from a browser button, so this tiny local
server provides a same-origin /refresh endpoint that reruns the crawler.
"""

import json
import os
import sys
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import cqu_crawler


HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8765"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "index.html")
_refresh_lock = threading.Lock()


class NoticeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/refresh":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        with _refresh_lock:
            try:
                cqu_crawler.main()
                self._send_json({"ok": True, "message": "刷新完成"})
            except Exception as exc:
                self._send_json(
                    {"ok": False, "message": f"刷新失败: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )

    def _send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def ensure_initial_page():
    if not os.path.exists(OUTPUT_FILE):
        cqu_crawler.main()


def main():
    os.chdir(BASE_DIR)
    ensure_initial_page()
    server = ThreadingHTTPServer((HOST, PORT), NoticeHandler)
    print(f"Serving CQU notices at http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        if "address already in use" in str(exc).lower() or getattr(exc, "winerror", None) == 10048:
            sys.exit(0)
        raise
