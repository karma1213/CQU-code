import tempfile
import unittest
from pathlib import Path

import requests

from crawler_utils import decode_response, safe_http_url, write_text_atomic


class CrawlerUtilsTest(unittest.TestCase):
    def response(self, content, status=200, encoding=None):
        response = requests.Response()
        response.status_code = status
        response._content = content
        response.encoding = encoding
        response.url = "https://example.test/source"
        return response

    def test_decode_response_honors_meta_charset(self):
        raw = '<meta charset="gb18030"><p>重庆大学</p>'.encode("gb18030")
        self.assertIn("重庆大学", decode_response(self.response(raw, encoding="ISO-8859-1")))

    def test_decode_response_raises_for_http_error(self):
        with self.assertRaises(requests.HTTPError):
            decode_response(self.response(b"error", status=503))

    def test_safe_http_url_rejects_unsafe_and_disguised_hosts(self):
        self.assertEqual(safe_http_url("javascript:alert(1)"), "")
        self.assertEqual(
            safe_http_url("https://evil.test/?next=news.cn", allowed_hosts=("news.cn",)),
            "",
        )
        self.assertEqual(
            safe_http_url("/politics/1", "https://www.news.cn/", allowed_hosts=("news.cn",)),
            "https://www.news.cn/politics/1",
        )

    def test_write_text_atomic_replaces_content_and_cleans_temp_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "page.html")
            target.write_text("old", encoding="utf-8")
            write_text_atomic(target, "新内容")
            self.assertEqual(target.read_text(encoding="utf-8"), "新内容")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
