import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bs4 import BeautifulSoup

import cqu_crawler


class CquCrawlerTest(unittest.TestCase):
    def test_fetch_page_uses_browser_for_waf_412(self):
        response = cqu_crawler.requests.Response()
        response.status_code = 412
        response.url = "https://civil.cqu.edu.cn/xzwb/tzgg.htm"
        error = cqu_crawler.requests.HTTPError(response=response)
        rendered = "<html><body><h1>通知公告</h1></body></html>"
        with (
            mock.patch.object(cqu_crawler.requests, "get", side_effect=error),
            mock.patch.object(cqu_crawler.browser_fetch, "enabled", return_value=True),
            mock.patch.object(cqu_crawler.browser_fetch, "fetch_html", return_value=rendered) as fetch,
        ):
            soup = cqu_crawler.fetch_page(response.url)
        self.assertEqual(soup.h1.get_text(), "通知公告")
        fetch.assert_called_once_with(
            response.url,
            [source["url"] for source in cqu_crawler.SOURCES],
        )

    def test_crawl_sources_batches_only_http_412_sources(self):
        sources = [
            {"id": "blocked_a", "name": "A", "type": "civil", "url": "https://a.test", "base": "https://a.test/"},
            {"id": "direct", "name": "B", "type": "cqu", "url": "https://b.test", "base": "https://b.test/"},
            {"id": "blocked_c", "name": "C", "type": "xgb", "url": "https://c.test", "base": "https://c.test/"},
        ]

        def response(status, url, body=b"<html><body>direct</body></html>"):
            value = cqu_crawler.requests.Response()
            value.status_code = status
            value.url = url
            value._content = body
            value.encoding = "utf-8"
            return value

        http = mock.Mock()
        http.get.side_effect = [
            response(412, sources[0]["url"]),
            response(200, sources[1]["url"]),
            response(412, sources[2]["url"]),
        ]
        browser = mock.MagicMock()
        browser.__enter__.return_value.fetch.side_effect = [
            "<html><body>A rendered</body></html>",
            "<html><body>C rendered</body></html>",
        ]

        def parsed(source, soup):
            return [("2026-08-01", source["id"], source["url"] + "/item")]

        with (
            mock.patch.object(cqu_crawler.browser_fetch, "BrowserSession", return_value=browser) as session_class,
            mock.patch.object(cqu_crawler, "parse_source", side_effect=parsed),
        ):
            results, errors, metrics = cqu_crawler.crawl_sources(sources, http_session=http)

        self.assertEqual(errors, [])
        self.assertEqual([source["id"] for source, _ in results], ["blocked_a", "direct", "blocked_c"])
        session_class.assert_called_once_with(["https://a.test", "https://c.test"])
        self.assertEqual(
            [call.args[0] for call in browser.__enter__.return_value.fetch.call_args_list],
            ["https://a.test", "https://c.test"],
        )
        metric_by_id = {metric["source_id"]: metric for metric in metrics}
        self.assertFalse(metric_by_id["direct"]["browser_used"])
        self.assertEqual(metric_by_id["direct"]["http_status"], 200)
        self.assertTrue(metric_by_id["blocked_a"]["browser_used"])
        self.assertEqual(metric_by_id["blocked_a"]["http_status"], 412)

    def test_crawl_sources_continues_after_one_browser_source_fails(self):
        sources = [
            {"id": "a", "name": "A", "type": "civil", "url": "https://a.test", "base": "https://a.test/"},
            {"id": "b", "name": "B", "type": "xgb", "url": "https://b.test", "base": "https://b.test/"},
        ]
        responses = []
        for source in sources:
            value = cqu_crawler.requests.Response()
            value.status_code = 412
            value.url = source["url"]
            value._content = b"blocked"
            responses.append(value)
        http = mock.Mock()
        http.get.side_effect = responses
        browser = mock.MagicMock()
        browser.__enter__.return_value.fetch.side_effect = [
            "<html><body>A rendered</body></html>",
            cqu_crawler.browser_fetch.BrowserFetchError("B still blocked"),
        ]
        browser.__enter__.return_value.retry_count = 1

        with (
            mock.patch.object(cqu_crawler.browser_fetch, "BrowserSession", return_value=browser),
            mock.patch.object(
                cqu_crawler,
                "parse_source",
                return_value=[("2026-08-01", "A title", "https://a.test/item")],
            ),
        ):
            results, errors, metrics = cqu_crawler.crawl_sources(sources, http_session=http)

        self.assertEqual(len(results[0][1]), 1)
        self.assertEqual(results[1][1], [])
        self.assertEqual(errors[0]["source"], "B")
        self.assertIn("still blocked", errors[0]["message"])
        self.assertEqual({metric["source_id"] for metric in metrics}, {"a", "b"})

    def test_crawl_sources_propagates_browser_session_cleanup_failure(self):
        source = {
            "id": "blocked",
            "name": "Blocked",
            "type": "civil",
            "url": "https://blocked.test",
            "base": "https://blocked.test/",
        }
        response = cqu_crawler.requests.Response()
        response.status_code = 412
        response.url = source["url"]
        response._content = b"blocked"
        http = mock.Mock()
        http.get.return_value = response
        browser = mock.MagicMock()
        browser.__enter__.return_value.fetch.return_value = (
            "<html><body>rendered</body></html>"
        )
        browser.__exit__.side_effect = cqu_crawler.browser_fetch.BrowserFetchError(
            "ChromeDriver cleanup failed"
        )

        with (
            mock.patch.object(
                cqu_crawler.browser_fetch, "BrowserSession", return_value=browser
            ),
            mock.patch.object(
                cqu_crawler,
                "parse_source",
                return_value=[
                    ("2026-08-01", "Rendered item", "https://blocked.test/item")
                ],
            ),
        ):
            with self.assertRaisesRegex(
                cqu_crawler.browser_fetch.BrowserFetchError,
                "ChromeDriver cleanup failed",
            ):
                cqu_crawler.crawl_sources([source], http_session=http)

    def test_fetch_page_reports_412_when_browser_fallback_disabled(self):
        response = cqu_crawler.requests.Response()
        response.status_code = 412
        response.url = "https://civil.cqu.edu.cn/xzwb/tzgg.htm"
        error = cqu_crawler.requests.HTTPError(response=response)
        with (
            mock.patch.object(cqu_crawler.requests, "get", side_effect=error),
            mock.patch.object(cqu_crawler.browser_fetch, "enabled", return_value=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "HTTP 412"):
                cqu_crawler.fetch_page(response.url)

    def test_parser_rejects_unsafe_urls(self):
        soup = BeautifulSoup(
            '<div class="list-content"><p>2026-08-01 '
            '<a href="javascript:alert(1)">研究生奖学金评选通知</a></p></div>',
            "html.parser",
        )
        self.assertEqual(cqu_crawler.parse_xgb(soup, "https://xgb.cqu.edu.cn/"), [])

    def test_civil_parser_accepts_absolute_official_url(self):
        soup = BeautifulSoup(
            '<li><a href="https://civil.cqu.edu.cn/info/1.htm">学院教学工作通知</a>'
            '<span>2026-08-01</span></li>',
            "html.parser",
        )
        result = cqu_crawler.parse_civil(soup, "https://civil.cqu.edu.cn/")
        self.assertEqual(result[0][2], "https://civil.cqu.edu.cn/info/1.htm")

    def test_generate_html_drops_unsafe_urls(self):
        source = {"id": "test", "name": "测试来源"}
        html = cqu_crawler.generate_html(
            [(source, [("2026-08-01", "安全标题内容", "javascript:alert(1)")])],
            cqu_crawler.datetime(2026, 8, 1, 8, 0),
        )
        self.assertNotIn("javascript:", html)
        self.assertIn("共 0 条通知", html)

    def test_generate_html_displays_source_errors_safely(self):
        html = cqu_crawler.generate_html(
            [],
            cqu_crawler.datetime(2026, 8, 1, 8, 0),
            [{"source": "来源<x>", "message": "HTTP 412 & blocked"}],
        )
        self.assertIn("部分来源抓取失败", html)
        self.assertIn("来源&lt;x&gt;", html)
        self.assertIn("HTTP 412 &amp; blocked", html)

    def test_main_preserves_previous_page_when_all_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "index.html")
            output.write_text("last known good", encoding="utf-8")
            source = {"id": "x", "name": "测试", "type": "x", "url": "https://x.test"}
            with (
                mock.patch.object(cqu_crawler, "OUTPUT_FILE", str(output)),
                mock.patch.object(cqu_crawler, "SOURCES", [source]),
                mock.patch.object(
                    cqu_crawler,
                    "crawl_sources",
                    return_value=(
                        [(source, [])],
                        [{"source": "测试", "message": "offline"}],
                        [],
                    ),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "已保留上一版页面"):
                    cqu_crawler.main()
            self.assertEqual(output.read_text(encoding="utf-8"), "last known good")

    def test_main_bootstraps_empty_page_without_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "index.html")
            source = {"id": "x", "name": "测试", "type": "x", "url": "https://x.test"}
            with (
                mock.patch.object(cqu_crawler, "OUTPUT_FILE", str(output)),
                mock.patch.object(cqu_crawler, "SOURCES", [source]),
                mock.patch.object(
                    cqu_crawler,
                    "crawl_sources",
                    return_value=(
                        [(source, [])],
                        [],
                        [],
                    ),
                ),
            ):
                cqu_crawler.main()
            self.assertIn("暂无可用通知数据", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
