# -*- coding: utf-8 -*-
"""仓库卫生检查：写死路径 + Windows 脚本编码。

这两类问题都真实发生过：
- 启动器写死了 D:\\Program Files\\cherry\\DS Agent 和某台机器的 python.exe；
- .vbs 存成无 BOM 的 UTF-8 且含中文，WSH 按 ANSI 码页解析直接语法报错。
"""

import os
import re
import unittest
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 生成产物与二进制不参与检查
SKIP_NAMES = {"index.html", "news.html", "finish-log.txt", "finish-search-refactor.bat"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "tools"}
SKIP_EXT = {".ico", ".pyc", ".zip", ".png", ".jpg", ".log", ".tmp"}

# 机器/安装位置相关的写死路径
FORBIDDEN = [
    (re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\", re.I), "hardcoded user profile path"),
    (re.compile(r"DS Agent", re.I), "stale install folder 'DS Agent'"),
    (re.compile(r"codex-runtimes", re.I), "hardcoded codex runtime python"),
    (re.compile(r"[A-Za-z]:\\New task", re.I), "hardcoded 'C:\\New task' path"),
]


def repo_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_NAMES or os.path.splitext(name)[1].lower() in SKIP_EXT:
                continue
            yield os.path.join(dirpath, name)


class NoHardcodedPathsTest(unittest.TestCase):
    def test_repo_files_skips_gitignored_runtime_artifacts(self):
        walked = [
            (
                ROOT,
                [],
                [
                    "app.py",
                    "notice-server.log",
                    "notice-server.err.log",
                    "notice-server.out.log",
                    "refresh.tmp",
                ],
            )
        ]
        with mock.patch("os.walk", return_value=walked):
            files = [os.path.basename(path) for path in repo_files()]
        self.assertEqual(files, ["app.py"])

    def test_no_machine_specific_paths(self):
        problems = []
        for path in repo_files():
            rel = os.path.relpath(path, ROOT)
            if rel.startswith("tests" + os.sep):
                continue  # 本文件自身含样例字符串
            try:
                text = Path(path).read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            for pattern, label in FORBIDDEN:
                for m in pattern.finditer(text):
                    line = text[: m.start()].count("\n") + 1
                    problems.append(f"{rel}:{line} {label} -> {m.group(0)!r}")
        self.assertEqual(problems, [], "\n" + "\n".join(problems))


class WindowsScriptEncodingTest(unittest.TestCase):
    """WSH/cmd/PowerShell 5.1 对无 BOM 的 UTF-8 都按系统 ANSI 码页解码。"""

    def _scripts(self, ext):
        return [p for p in repo_files() if p.lower().endswith(ext)]

    def test_vbs_is_pure_ascii(self):
        for path in self._scripts(".vbs"):
            raw = Path(path).read_bytes()
            bad = [(i, b) for i, b in enumerate(raw) if b > 0x7F]
            self.assertEqual(
                bad, [],
                f"{os.path.relpath(path, ROOT)} contains non-ASCII bytes; "
                f"WSH parses .vbs with the ANSI codepage and will fail",
            )

    def test_bat_is_pure_ascii_without_bom(self):
        # cmd.exe 按当前码页逐行读取批处理文件，`chcp 65001` 与文件内非 ASCII 字节
        # 混用会造成字节偏移错乱。约定：.bat 只写 ASCII，中文提示交给 Python 输出。
        for path in self._scripts(".bat"):
            raw = Path(path).read_bytes()
            rel = os.path.relpath(path, ROOT)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), f"{rel}: .bat must not start with a BOM")
            bad = [(i, b) for i, b in enumerate(raw) if b > 0x7F]
            self.assertEqual(
                bad, [],
                f"{rel}: contains non-ASCII bytes; keep .bat pure ASCII and print "
                f"localized text from Python instead",
            )

    def test_ps1_with_non_ascii_has_utf8_bom(self):
        for path in self._scripts(".ps1"):
            raw = Path(path).read_bytes()
            rel = os.path.relpath(path, ROOT)
            if any(b > 0x7F for b in raw):
                self.assertTrue(
                    raw.startswith(b"\xef\xbb\xbf"),
                    f"{rel}: non-ASCII .ps1 needs a UTF-8 BOM for Windows PowerShell 5.1",
                )

    def test_windows_scripts_use_crlf(self):
        for ext in (".bat", ".vbs", ".ps1"):
            for path in self._scripts(ext):
                raw = Path(path).read_bytes()
                rel = os.path.relpath(path, ROOT)
                self.assertEqual(
                    raw.count(b"\r\n"), raw.count(b"\n"),
                    f"{rel}: must use CRLF line endings",
                )


class WindowsPythonLauncherContractTest(unittest.TestCase):
    def test_py_launcher_keeps_executable_and_arguments_separate(self):
        text = Path(ROOT, "_env.bat").read_text(encoding="ascii")

        self.assertNotIn('set "PY=py -3"', text)
        self.assertRegex(text, r'(?im)^\s*set "PY=py"\s*$')
        self.assertRegex(text, r'(?im)^\s*set "PY_ARGS=-3"\s*$')

    def test_python_entrypoints_pass_launcher_arguments_unquoted(self):
        expected_targets = {
            "refresh_and_open.bat": "cqu_crawler.py",
            "run_crawler.bat": "cqu_crawler.py",
            "diagnose.bat": "diagnose_sources.py",
        }

        for name, target in expected_targets.items():
            with self.subTest(name=name):
                text = Path(ROOT, name).read_text(encoding="ascii")
                self.assertIn(
                    f'"%PY%" %PY_ARGS% "%ROOT%\\{target}"',
                    text,
                )


class VbsSyntaxSanityTest(unittest.TestCase):
    def test_quotes_balanced_and_if_blocks_closed(self):
        for path in [p for p in repo_files() if p.lower().endswith(".vbs")]:
            rel = os.path.relpath(path, ROOT)
            text = Path(path).read_text(encoding="ascii")
            depth = 0
            for n, line in enumerate(text.splitlines(), 1):
                if line.strip().startswith("'"):
                    continue
                code = line.split("'")[0] if line.count('"') % 2 == 0 else line
                self.assertEqual(
                    code.count('"') % 2, 0,
                    f"{rel}:{n} odd number of quotes -> unterminated string",
                )
                s = code.strip()
                if re.match(r"^If\b.*\bThen\s*$", s, re.I):
                    depth += 1
                elif re.match(r"^End\s+If\b", s, re.I):
                    depth -= 1
                self.assertGreaterEqual(depth, 0, f"{rel}:{n} 'End If' without 'If'")
            self.assertEqual(depth, 0, f"{rel}: unclosed If block(s)")


class DesktopLauncherTest(unittest.TestCase):
    def test_each_page_launcher_starts_both_local_services(self):
        for name in ("open_notice_site.vbs", "open_news_site.vbs"):
            with self.subTest(name=name):
                text = Path(ROOT, name).read_text(encoding="ascii")
                self.assertIn('fso.BuildPath(baseDir, "notice_server.py")', text)
                self.assertIn('fso.BuildPath(baseDir, "news_server.py")', text)
                self.assertIn("shell.Run noticeCommand, 0, False", text)
                self.assertIn("shell.Run newsCommand, 0, False", text)


class StopScriptTest(unittest.TestCase):
    def test_stop_script_targets_only_the_two_site_servers(self):
        text = Path(ROOT, "stop_sites.bat").read_text(encoding="ascii")
        self.assertIn("notice_server\\.py", text)
        self.assertIn("news_server\\.py", text)
        self.assertIn("taskkill.exe", text)
        self.assertIn("/T /F", text)
        self.assertNotIn("/IM python.exe", text.lower())


if __name__ == "__main__":
    unittest.main()
