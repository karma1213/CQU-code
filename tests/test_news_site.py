import importlib.util
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module(filename, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NewsSiteTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
