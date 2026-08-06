import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

from site_server import StaticRefreshHandler


class SiteServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        Path(self.temp_dir.name, "index.html").write_text("<h1>test page</h1>", encoding="utf-8")
        self.refreshes = []
        refreshes = self.refreshes

        class Handler(StaticRefreshHandler):
            directory = self.temp_dir.name
            page_name = "index.html"
            site_label = "test"
            refresh_lock = threading.Lock()
            refresh_cooldown = 0
            refresh_callback = staticmethod(lambda: refreshes.append("done"))

        self.handler = Handler
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_server)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET"):
        return urlopen(Request(self.base_url + path, method=method), timeout=3)

    def test_serves_page_health_and_security_headers(self):
        with self.request("/?from=test") as response:
            self.assertIn(b"test page", response.read())
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        with self.request("/healthz") as response:
            self.assertEqual(json.load(response), {"ok": True, "site": "test"})

    def test_does_not_expose_other_repository_files(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/README.md")
        self.assertEqual(caught.exception.code, 404)

    def test_refresh_runs_once_and_busy_request_returns_conflict(self):
        with self.request("/refresh", method="POST") as response:
            self.assertTrue(json.load(response)["ok"])
        self.assertEqual(self.refreshes, ["done"])

        self.handler.refresh_lock.acquire()
        try:
            with self.assertRaises(HTTPError) as caught:
                self.request("/refresh", method="POST")
            self.assertEqual(caught.exception.code, 409)
            self.assertIn("正在进行", json.load(caught.exception)["message"])
        finally:
            self.handler.refresh_lock.release()

    def test_refresh_error_is_generic(self):
        def fail():
            raise RuntimeError("secret detail")

        self.handler.refresh_callback = staticmethod(fail)
        with mock.patch("site_server.LOGGER.exception"):
            with self.assertRaises(HTTPError) as caught:
                self.request("/refresh", method="POST")
        self.assertEqual(caught.exception.code, 500)
        body = json.load(caught.exception)
        self.assertNotIn("secret detail", body["message"])

    def test_refresh_is_rate_limited(self):
        self.handler.refresh_cooldown = 60
        with self.request("/refresh", method="POST"):
            pass
        with self.assertRaises(HTTPError) as caught:
            self.request("/refresh", method="POST")
        self.assertEqual(caught.exception.code, 429)
        self.assertGreater(int(caught.exception.headers["Retry-After"]), 0)

    def test_send_json_ignores_connection_reset_during_headers(self):
        handler = object.__new__(StaticRefreshHandler)
        handler.command = "GET"
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock(side_effect=ConnectionResetError("client disconnected"))
        handler.wfile = mock.Mock()

        handler._send_json({"ok": True})

        handler.wfile.write.assert_not_called()

    def test_send_json_ignores_broken_pipe_during_body(self):
        handler = object.__new__(StaticRefreshHandler)
        handler.command = "GET"
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock()
        handler.wfile = mock.Mock()
        handler.wfile.write.side_effect = BrokenPipeError("client disconnected")

        handler._send_json({"ok": True})

        handler.wfile.write.assert_called_once()

    def test_static_get_ignores_client_disconnect(self):
        handler = object.__new__(StaticRefreshHandler)
        handler.path = "/"
        with mock.patch(
            "site_server.SimpleHTTPRequestHandler.do_GET",
            side_effect=BrokenPipeError("client disconnected"),
        ):
            try:
                handler.do_GET()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
                self.fail(f"client disconnect escaped static handler: {exc}")


if __name__ == "__main__":
    unittest.main()
