#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restricted static-page server with a serialized refresh endpoint."""

import json
import logging
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


LOGGER = logging.getLogger(__name__)
CLIENT_DISCONNECT_ERRORS = (
    BrokenPipeError,
    ConnectionResetError,
    ConnectionAbortedError,
)


def environment_port(names, default):
    """Read the first configured TCP port and validate its range."""
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        try:
            port = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
        if not 1 <= port <= 65535:
            raise ValueError(f"{name} must be between 1 and 65535, got {port}")
        return port
    return default


class StaticRefreshHandler(SimpleHTTPRequestHandler):
    directory = os.getcwd()
    page_name = "index.html"
    icon_name = None
    site_label = "site"
    refresh_callback = None
    refresh_lock = None
    refresh_cooldown = 30
    last_refresh_at = 0.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.directory, **kwargs)

    def log_message(self, format, *args):
        return

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'none'",
        )
        super().end_headers()

    def _static_path(self):
        path = urlsplit(self.path).path
        if path in {"", "/", f"/{self.page_name}"}:
            return f"/{self.page_name}"
        if self.icon_name and path in {"/favicon.ico", f"/{self.icon_name}"}:
            return f"/{self.icon_name}"
        return None

    def do_GET(self):
        self._ignore_client_disconnect(self._do_GET)

    def _do_GET(self):
        if urlsplit(self.path).path == "/healthz":
            self._send_json({"ok": True, "site": self.site_label})
            return
        static_path = self._static_path()
        if static_path is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.path = static_path
        super().do_GET()

    def do_HEAD(self):
        self._ignore_client_disconnect(self._do_HEAD)

    def _do_HEAD(self):
        static_path = self._static_path()
        if static_path is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.path = static_path
        super().do_HEAD()

    def do_POST(self):
        self._ignore_client_disconnect(self._do_POST)

    def _do_POST(self):
        if urlsplit(self.path).path != "/refresh":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        if self.refresh_callback is None or self.refresh_lock is None:
            self._send_json(
                {"ok": False, "message": "刷新服务未配置"},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        if not self.refresh_lock.acquire(blocking=False):
            self._send_json(
                {"ok": False, "message": "刷新正在进行，请稍后再试"},
                HTTPStatus.CONFLICT,
            )
            return
        try:
            elapsed = time.monotonic() - self.__class__.last_refresh_at
            if elapsed < self.refresh_cooldown:
                retry_after = max(1, int(self.refresh_cooldown - elapsed) + 1)
                self._send_json(
                    {"ok": False, "message": f"刷新过于频繁，请在 {retry_after} 秒后重试"},
                    HTTPStatus.TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(retry_after)},
                )
                return
            try:
                self.refresh_callback()
            except Exception:
                LOGGER.exception("Refresh failed for %s", self.site_label)
                self._send_json(
                    {"ok": False, "message": "刷新失败，请查看服务端日志"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            else:
                self._send_json({"ok": True, "message": "刷新完成"})
            finally:
                self.__class__.last_refresh_at = time.monotonic()
        finally:
            self.refresh_lock.release()

    def _send_json(self, data, status=HTTPStatus.OK, headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        except CLIENT_DISCONNECT_ERRORS:
            return

    @staticmethod
    def _ignore_client_disconnect(callback):
        try:
            callback()
        except CLIENT_DISCONNECT_ERRORS:
            return


def serve(host, port, handler_class, label):
    """Run a threaded HTTP server until interrupted."""
    with ThreadingHTTPServer((host, port), handler_class) as server:
        server.daemon_threads = True
        print(f"Serving {label} at http://{host}:{port}/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
