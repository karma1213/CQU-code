import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pinyin_table
import search_widget


class PinyinTableTest(unittest.TestCase):
    def test_table_readings_are_wellformed(self):
        for char, readings in pinyin_table.TABLE.items():
            self.assertEqual(len(char), 1)
            self.assertTrue(readings, char)
            for r in readings:
                self.assertRegex(r, r"^[a-z]{1,6}$", f"{char}:{r}")

    def test_phrase_entries_align(self):
        for word, sylls in pinyin_table.PHRASES.items():
            self.assertEqual(len(word), len(sylls), word)


class SearchWidgetTest(unittest.TestCase):
    def test_alignment_one_syllable_per_char(self):
        for text in ["重庆大学2026年奖学金", "AI · Python 培训", "", "abc"]:
            self.assertEqual(len(search_widget.syllables(text)), len(text))

    def test_phrase_correction(self):
        attr = search_widget.py_attr("重庆大学")
        self.assertEqual(attr.split(" ")[0], "chong")
        attr2 = search_widget.py_attr("重大事故")
        self.assertEqual(attr2.split(" ")[0].split("|")[0], "zhong")

    def test_polyphone_alternatives(self):
        sylls = search_widget.syllables("行")
        self.assertIn("xing", sylls[0])
        self.assertIn("hang", sylls[0])

    def test_attr_is_attribute_safe(self):
        attr = search_widget.py_attr('恶意"标题<与>符号&')
        self.assertRegex(attr, r"^[a-z0-9|~ ]+$")

    def test_non_han_kept_or_masked(self):
        self.assertEqual(search_widget.py_attr("a1？"), "a 1 ~")


class TemplateIntegrationTest(unittest.TestCase):
    def test_notice_page_contains_search_engine(self):
        import cqu_crawler

        source = {"id": "test", "name": "研究生院"}
        results = [(source, [("2026-07-01", "研究生国家奖学金评选", "https://x.test/1")])]
        from datetime import datetime

        html = cqu_crawler.generate_html(results, datetime(2026, 7, 1, 8, 0, 0))
        self.assertIn("window.CquSearch", html)
        self.assertIn("data-py=", html)
        self.assertIn("data-spy=", html)
        self.assertIn("data-sname=", html)
        self.assertIn("mark.hl", html)
        self.assertIn("CquSearch.install", html)

    def test_news_page_contains_search_engine(self):
        import news_crawler

        items = [
            news_crawler.NewsItem(
                "x", "新华网", "国内", "银行降息新闻", "https://x.test/2",
                "2026-07-01", "摘要内容", "", ["宏观"],
            )
        ]
        html = news_crawler.generate_html(
            items, [], news_crawler.datetime(2026, 7, 1, 8, 0, tzinfo=news_crawler.CST)
        )
        self.assertIn("window.CquSearch", html)
        self.assertIn("data-py=", html)
        self.assertIn("data-spy=", html)
        self.assertIn("CquSearch.install", html)
        # 银行 词组修正
        self.assertIn("yin hang", html)


if __name__ == "__main__":
    unittest.main()
