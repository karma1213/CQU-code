import ast
import unittest
from pathlib import Path

import cqu_crawler
import notice_sources


ROOT = Path(__file__).resolve().parent.parent


class NoticeSourcesTest(unittest.TestCase):
    def test_civil_public_notice_source_is_configured(self):
        source = next(
            source for source in notice_sources.SOURCES if source["id"] == "civil_gsgg"
        )
        self.assertEqual(source["name"], "土木工程学院 — 公示公告")
        self.assertEqual(
            source["url"], "https://civil.cqu.edu.cn/xzwb/tzgg/gsgg.htm"
        )
        self.assertEqual(source["base"], "https://civil.cqu.edu.cn/xzwb/")
        self.assertEqual(source["type"], "civil")

    def test_crawler_reexports_source_contract_from_dedicated_module(self):
        self.assertIs(cqu_crawler.SOURCES, notice_sources.SOURCES)
        self.assertIs(cqu_crawler.parse_source, notice_sources.parse_source)
        self.assertIs(cqu_crawler.parse_civil, notice_sources.parse_civil)
        self.assertIs(cqu_crawler.parse_cqu, notice_sources.parse_cqu)
        self.assertIs(cqu_crawler.parse_xgb, notice_sources.parse_xgb)
        self.assertIs(cqu_crawler.parse_graduate, notice_sources.parse_graduate)

    def test_crawler_does_not_define_source_configuration_or_parsers(self):
        tree = ast.parse((ROOT / "cqu_crawler.py").read_text(encoding="utf-8"))
        function_names = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        assigned_names = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertNotIn("SOURCES", assigned_names)
        self.assertTrue(
            {"clean_title", "parse_civil", "parse_cqu", "parse_xgb", "parse_graduate", "parse_source"}
            .isdisjoint(function_names)
        )


if __name__ == "__main__":
    unittest.main()
