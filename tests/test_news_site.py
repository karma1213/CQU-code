import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module(filename, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NewsSiteTest(unittest.TestCase):
    def test_rss_summary_strips_embedded_html(self):
        crawler = load_module("news_crawler.py", "news_crawler_rss_summary_test")
        source = {
            "id": "rss",
            "name": "RSS",
            "category": "国内",
            "url": "https://example.test/feed.xml",
        }
        payload = """<rss><channel><item>
          <title>这是一个足够长的新闻标题</title>
          <link>https://example.test/news/1</link>
          <description>&lt;p&gt;正文 &lt;b&gt;摘要&lt;/b&gt;&lt;/p&gt;</description>
          <pubDate>Tue, 04 Aug 2026 22:31:00 +0800</pubDate>
        </item></channel></rss>"""
        with mock.patch.object(crawler, "fetch_text", return_value=payload):
            items = crawler.fetch_rss(source)
        self.assertEqual(items[0].summary, "正文 摘要")

    def test_atom_feed_supports_namespaces_and_iso_dates(self):
        crawler = load_module("news_crawler.py", "news_crawler_atom_test")
        source = {
            "id": "atom",
            "name": "Atom",
            "category": "国内",
            "url": "https://example.test/feed.atom",
        }
        payload = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Campus announcement</title>
            <link href="https://example.test/news/2026/08/07/1.html" />
            <summary>&lt;p&gt;Summary&lt;/p&gt;</summary>
            <updated>2026-08-07T01:30:00Z</updated>
          </entry>
        </feed>"""
        with mock.patch.object(crawler, "fetch_text", return_value=payload):
            items = crawler.fetch_rss(source)
        self.assertEqual(items[0].url, "https://example.test/news/2026/08/07/1.html")
        self.assertEqual(items[0].date, "2026-08-07 09:30")

    def test_parse_date_rejects_navigation_text(self):
        crawler = load_module("news_crawler.py", "news_crawler_date_test")
        self.assertEqual(crawler.parse_date("English Español Français"), "")

    def test_page_parser_skips_language_navigation(self):
        crawler = load_module("news_crawler.py", "news_crawler_language_nav_test")
        source = {
            "id": "xinhua",
            "name": "新华网",
            "category": "国内",
            "url": "https://www.news.cn/",
            "base": "https://www.news.cn/",
        }
        markup = '<nav><a href="https://portuguese.news.cn/index.htm">Português</a></nav>'
        with mock.patch.object(crawler, "fetch_text", return_value=markup):
            self.assertEqual(crawler.fetch_page_source(source), [])

    def test_crawler_generates_required_controls_and_state_keys(self):
        crawler = load_module("news_crawler.py", "news_crawler")
        items = [
            crawler.NewsItem(
                source_id="xinhua",
                source_name="新华网",
                category="政策",
                title="国务院发布重要政策",
                url="https://www.news.cn/politics/example.htm",
                date="2026-06-05",
                summary="政策摘要",
                hot_score="",
                tags=["政策"],
            )
        ]
        html = crawler.generate_html(items, [], crawler.datetime(2026, 6, 5, 8, 30, tzinfo=crawler.CST))
        self.assertIn("国内新闻聚合", html)
        self.assertIn("id=\"searchInput\"", html)
        self.assertIn("id=\"sourceFilter\"", html)
        self.assertIn("id=\"categoryFilter\"", html)
        self.assertIn("news_item_favorites", html)
        self.assertIn("fetch('/refresh'", html)
        self.assertIn("data-action=\"read-toggle\"", html)

    def test_dedupe_prefers_normalized_url_and_title_for_hot_search(self):
        crawler = load_module("news_crawler.py", "news_crawler")
        items = [
            crawler.NewsItem("xinhua", "新华网", "国内", "同一新闻", "https://a.test/news?id=1", "", "", "", []),
            crawler.NewsItem("xinhua", "新华网", "国内", "同一新闻", "https://a.test/news?id=1#top", "", "", "", []),
            crawler.NewsItem("weibo", "微博热搜", "热搜", "同一热搜", "", "", "", "100", []),
            crawler.NewsItem("weibo", "微博热搜", "热搜", "同一热搜", "", "", "", "90", []),
        ]
        result = crawler.dedupe_items(items)
        self.assertEqual(len(result), 2)

    def test_total_cap_keeps_late_sources_like_weibo(self):
        crawler = load_module("news_crawler.py", "news_crawler")
        items = []
        for source_index in range(6):
            for item_index in range(30):
                items.append(
                    crawler.NewsItem(
                        f"source_{source_index}",
                        f"来源{source_index}",
                        "国内",
                        f"新闻{source_index}-{item_index}",
                        f"https://example.com/{source_index}/{item_index}",
                        "",
                        "",
                        "",
                        [],
                    )
                )
        for item_index in range(30):
            items.append(
                crawler.NewsItem(
                    "weibo_hot",
                    "微博热搜",
                    "热搜",
                    f"{item_index + 1}. 热搜{item_index}",
                    "",
                    "",
                    "",
                    str(item_index),
                    [],
                )
            )

        result = crawler.select_balanced_items(items, 140)
        self.assertEqual(len(result), 140)
        self.assertTrue(any(item.source_name == "微博热搜" for item in result))
        self.assertTrue(any(item.category == "热搜" for item in result))

    def test_server_uses_news_crawler_and_port_8766(self):
        server = load_module("news_server.py", "news_server")
        self.assertEqual(server.PORT, 8766)
        self.assertEqual(os.path.basename(server.OUTPUT_FILE), "news.html")
        self.assertTrue(hasattr(server, "NewsHandler"))

    def test_page_parser_rejects_disguised_source_domain(self):
        crawler = load_module("news_crawler.py", "news_crawler_domain_test")
        source = {
            "id": "xinhua",
            "name": "新华网",
            "category": "国内",
            "url": "https://www.news.cn/",
            "base": "https://www.news.cn/",
        }
        markup = '<a href="https://evil.test/article?next=news.cn">这是一个足够长的新闻标题</a>'
        with mock.patch.object(crawler, "fetch_text", return_value=markup):
            self.assertEqual(crawler.fetch_page_source(source), [])

    def test_generate_html_drops_unsafe_url(self):
        crawler = load_module("news_crawler.py", "news_crawler_unsafe_test")
        item = crawler.NewsItem("x", "来源", "国内", "新闻标题", "javascript:alert(1)", "", "", "", [])
        html = crawler.generate_html([item], [], crawler.datetime.now(crawler.CST))
        self.assertNotIn("javascript:", html)
        self.assertIn("<strong>0</strong>", html)

    def test_main_preserves_previous_page_when_all_sources_fail(self):
        crawler = load_module("news_crawler.py", "news_crawler_preserve_test")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "news.html")
            output.write_text("last known good", encoding="utf-8")
            with (
                mock.patch.object(crawler, "OUTPUT_FILE", str(output)),
                mock.patch.object(crawler, "crawl_all", return_value=([], [{"source": "x", "message": "offline"}])),
            ):
                with self.assertRaisesRegex(RuntimeError, "已保留上一版页面"):
                    crawler.main()
            self.assertEqual(output.read_text(encoding="utf-8"), "last known good")

    def test_main_bootstraps_empty_page_without_previous_output(self):
        crawler = load_module("news_crawler.py", "news_crawler_bootstrap_test")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "news.html")
            with (
                mock.patch.object(crawler, "OUTPUT_FILE", str(output)),
                mock.patch.object(crawler, "crawl_all", return_value=([], [])),
            ):
                crawler.main()
            self.assertIn("暂无可用新闻数据", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
