import ast
import unittest
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

import cqu_crawler
import frontend_shell
import news_crawler
import search_widget


class FrontendShellTest(unittest.TestCase):
    def test_shared_design_tokens_are_specific_to_cqu_index_desk(self):
        css = frontend_shell.DESIGN_CSS
        self.assertIn("--cqu-crimson:#8b1e27", css.lower())
        self.assertIn("--ink:#20262d", css.lower())
        self.assertIn("--cool-paper:#f3f5f6", css.lower())
        self.assertIn("--academic-blue:#315e6d", css.lower())
        self.assertIn("STZhongsong", css)
        self.assertIn("Bahnschrift", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn("linear-gradient", css)
        self.assertNotIn("radial-gradient", css)

    def test_search_styles_do_not_override_shared_shell_controls(self):
        self.assertIn("mark.hl", search_widget.SEARCH_CSS)
        self.assertNotIn(".empty-actions", search_widget.SEARCH_CSS)
        self.assertNotIn("border-radius:9px", search_widget.SEARCH_CSS)

    def test_news_controls_stack_before_status_filter_is_squeezed_out(self):
        css = frontend_shell.DESIGN_CSS
        self.assertIn("@media (max-width:1120px)", css)
        self.assertIn(
            'body[data-page="news"] .control-band { grid-template-columns:1fr; }',
            css,
        )
        self.assertIn(
            'body[data-page="news"] .control-secondary { justify-content:flex-start; overflow-x:auto; }',
            css,
        )

    def test_index_spine_moves_below_multi_row_toolbars(self):
        css = frontend_shell.DESIGN_CSS
        news_rules = css.split("@media (max-width:1120px)", 1)[1].split(
            "@media (max-width:980px)", 1
        )[0]
        notice_rules = css.split("@media (max-width:980px)", 1)[1].split(
            "@media (max-width:700px)", 1
        )[0]
        self.assertIn(
            'body[data-page="news"] .index-spine { position:relative; top:auto; }',
            news_rules,
        )
        self.assertIn(
            ".index-spine { position:relative; top:auto; }",
            notice_rules,
        )

    def test_mobile_notice_status_filters_use_a_full_width_row(self):
        css = frontend_shell.DESIGN_CSS
        self.assertIn(
            'body[data-page="notices"] .control-secondary { flex-wrap:wrap; overflow:visible; }',
            css,
        )
        self.assertIn(
            'body[data-page="notices"] #statusFilter { flex:1 0 100%; width:100%; overflow:visible; }',
            css,
        )
        self.assertIn(
            'body[data-page="notices"] #statusFilter .segment-button { flex:1 1 25%; padding-inline:4px; }',
            css,
        )

    def test_error_summary_is_collapsed_and_hides_details_by_default(self):
        markup = frontend_shell.render_errors(
            [
                {
                    "source": "来源<x>",
                    "message": "HTTP 412 https://internal.test/very/long/path & blocked",
                }
            ]
        )
        soup = BeautifulSoup(markup, "html.parser")
        details = soup.select_one("details.source-errors")
        self.assertIsNotNone(details)
        self.assertFalse(details.has_attr("open"))
        self.assertEqual(details.summary.get_text(" ", strip=True), "1 个来源暂时不可用")
        self.assertNotIn("internal.test", details.summary.get_text())
        self.assertIn("来源<x>", details.get_text(" ", strip=True))
        self.assertNotIn("<x>", str(details.select_one(".source-error-name")))

    def test_crawlers_do_not_embed_renderer_implementations(self):
        root = Path(__file__).resolve().parent.parent
        for filename in ("cqu_crawler.py", "news_crawler.py"):
            with self.subTest(filename=filename):
                tree = ast.parse((root / filename).read_text(encoding="utf-8"))
                functions = {
                    node.name for node in tree.body if isinstance(node, ast.FunctionDef)
                }
                self.assertNotIn("generate_html", functions)
                self.assertNotIn("generate_html_legacy", functions)
        news_tree = ast.parse((root / "news_crawler.py").read_text(encoding="utf-8"))
        self.assertNotIn(
            "html_escape",
            {
                node.name
                for node in news_tree.body
                if isinstance(node, ast.FunctionDef)
            },
        )


class GeneratedPageShellTest(unittest.TestCase):
    def _notice_html(self, errors=None, items=True):
        source = {"id": "graduate", "name": "研究生院 — 通知公告"}
        rows = [
            ("2026-08-01", "研究生国家奖学金评选通知", "https://graduate.cqu.edu.cn/info/1.htm")
        ] if items else []
        return cqu_crawler.generate_html(
            [(source, rows)],
            datetime(2026, 8, 1, 8, 0),
            errors or [],
        )

    def _news_html(self, errors=None, items=True):
        rows = [
            news_crawler.NewsItem(
                "xinhua",
                "新华网",
                "政策",
                "国务院发布重要政策",
                "https://www.news.cn/politics/example.htm",
                "2026-08-01",
                "政策摘要",
                "",
                ["政策"],
            )
        ] if items else []
        return news_crawler.generate_html(
            rows,
            errors or [],
            news_crawler.datetime(2026, 8, 1, 8, 0, tzinfo=news_crawler.CST),
        )

    def _assert_shared_shell(self, html, active_page):
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup.body.get("data-page"), active_page)
        nav = soup.select_one('nav[aria-label="页面切换"]')
        self.assertIsNotNone(nav)
        self.assertEqual(len(nav.select("[data-page-target]")), 2)
        self.assertIsNotNone(nav.select_one('[data-page-target="notices"][data-service-port="8765"]'))
        self.assertIsNotNone(nav.select_one('[data-page-target="news"][data-service-port="8766"]'))
        self.assertIsNotNone(nav.select_one('[aria-current="page"]'))
        self.assertIsNotNone(soup.select_one(".index-spine [data-source-target]"))
        self.assertIsNotNone(soup.select_one("#searchInput"))
        self.assertIsNotNone(soup.select_one("#sourceFilter"))
        self.assertIsNotNone(soup.select_one("#refreshButton"))
        self.assertIn("location.protocol === 'file:'", html)
        self.assertIn("prefers-reduced-motion", html)
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("radial-gradient", html)

    def test_notice_page_uses_shared_shell_and_preserves_dom_contracts(self):
        html = self._notice_html()
        self._assert_shared_shell(html, "notices")
        soup = BeautifulSoup(html, "html.parser")
        self.assertIsNotNone(soup.select_one('.notice-item[data-action-scope="notice"]'))
        self.assertIsNotNone(soup.select_one('[data-action="favorite"]'))
        self.assertIsNotNone(soup.select_one('[data-action="read-toggle"]'))
        self.assertIn("cqu_notice_favorites", html)
        self.assertIn("cqu_notice_read", html)
        self.assertIn("cqu_notice_seen_urls", html)
        self.assertIn("CquSearch.install", html)
        status_buttons = soup.select("[data-filter]")
        self.assertTrue(status_buttons)
        self.assertTrue(all(button.has_attr("aria-pressed") for button in status_buttons))
        self.assertIn("newUrls", html)
        self.assertIn("hadSeen", html)

    def test_news_page_uses_shared_shell_and_preserves_dom_contracts(self):
        html = self._news_html()
        self._assert_shared_shell(html, "news")
        soup = BeautifulSoup(html, "html.parser")
        self.assertIsNotNone(soup.select_one("#categoryFilter"))
        self.assertIsNotNone(soup.select_one("#stateFilter"))
        self.assertIsNotNone(soup.select_one('.news-item[data-action-scope="news"]'))
        self.assertIn("news_item_favorites", html)
        self.assertIn("news_item_read", html)
        self.assertIn("news_item_seen_urls", html)
        self.assertIn("CquSearch.install", html)
        category_buttons = soup.select("button[data-category]")
        self.assertTrue(category_buttons)
        self.assertTrue(all(button.has_attr("aria-pressed") for button in category_buttons))
        self.assertIn("newUrls", html)
        self.assertIn("hadSeen", html)

    def test_both_pages_use_collapsed_error_details(self):
        error = [{"source": "上游站点", "message": "HTTP 412 https://example.test/path"}]
        for html in (self._notice_html(error), self._news_html(error)):
            soup = BeautifulSoup(html, "html.parser")
            details = soup.select_one("details.source-errors")
            self.assertIsNotNone(details)
            self.assertFalse(details.has_attr("open"))
            self.assertIn("1 个来源暂时不可用", details.summary.get_text(" ", strip=True))

    def test_local_storage_write_failures_do_not_break_page_scripts(self):
        for html in (self._notice_html(), self._news_html()):
            start = html.index("function writeSet")
            end = html.index("function showToast", start)
            write_set = html[start:end]
            self.assertIn("localStorage.setItem", write_set)
            self.assertIn("try", write_set)
            self.assertIn("catch", write_set)

    def test_empty_states_offer_clear_and_refresh_actions(self):
        for html in (self._notice_html(items=False), self._news_html(items=False)):
            soup = BeautifulSoup(html, "html.parser")
            empty = soup.select_one("#emptyResults")
            self.assertIsNotNone(empty.select_one('[data-action="clear-filters"]'))
            self.assertIsNotNone(empty.select_one('[data-action="refresh"]'))


if __name__ == "__main__":
    unittest.main()
