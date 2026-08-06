#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取诊断：定位「0 条」到底卡在哪一步。

对每个来源依次检查：网络可达 -> HTTP 状态 -> 编码 -> 解析器命中数，
并把原始 HTML 存到 diag/ 目录，便于离线修复解析规则。

用法：python diagnose_sources.py [--browser]     （或双击 diagnose.bat）
"""

import argparse
import io
import os
import re
import sys
import traceback
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import cqu_crawler
from crawler_utils import decode_response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIAG_DIR = os.path.join(BASE_DIR, "diag")
REPORT = os.path.join(DIAG_DIR, "report.txt")

lines = []


def configure_stdout():
    """Use UTF-8 for the CLI without changing stdout when imported.

    Test runners and embedding hosts often replace ``sys.stdout`` with a
    StringIO-like object that has no ``buffer`` attribute.  Configuration is
    therefore explicit and guarded instead of running during module import.
    """
    stream = getattr(sys.stdout, "buffer", None)
    if stream is None:
        return
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    if encoding == "utf8":
        return
    sys.stdout = io.TextIOWrapper(stream, encoding="utf-8", errors="replace")


def log(msg=""):
    print(msg)
    lines.append(msg)


def sniff_encoding(resp):
    """返回 (声明编码, 猜测编码, meta 里写的编码)。"""
    declared = resp.encoding
    guessed = resp.apparent_encoding
    meta = ""
    head = resp.content[:2048]
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', head, re.I)
    if m:
        meta = m.group(1).decode("ascii", "replace")
    return declared, guessed, meta


def decode_best(resp):
    """按 meta -> apparent -> utf-8 的顺序找出能读通的解码结果。"""
    candidates = []
    head = resp.content[:2048]
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', head, re.I)
    if m:
        candidates.append(m.group(1).decode("ascii", "replace"))
    if resp.apparent_encoding:
        candidates.append(resp.apparent_encoding)
    candidates += ["utf-8", "gb18030"]
    for enc in candidates:
        try:
            text = resp.content.decode(enc, errors="strict")
            return enc, text
        except (UnicodeDecodeError, LookupError):
            continue
    return "utf-8/replace", resp.content.decode("utf-8", errors="replace")


def han_ratio(text):
    sample = text[:20000]
    if not sample:
        return 0.0
    han = sum(1 for c in sample if "一" <= c <= "鿿")
    return han / len(sample)


def run_production_probe():
    """Run the same two-phase HTTP/browser pipeline used by the notice service."""
    log("")
    log("=" * 68)
    log("生产链路检查（HTTP 200 直取；仅 HTTP 412 进入一个浏览器批次）")
    log("=" * 68)
    results, errors, metrics = cqu_crawler.crawl_sources()
    for metric in metrics:
        log(
            "  {source_id}: status={status} items={item_count} http={http_status} "
            "browser={browser_used} retry={retry_count} duration_ms={duration_ms}".format(
                **metric
            )
        )
        if metric["error"]:
            log(f"    error: {metric['error']}")
    log(f"生产链路结果: {sum(len(items) for _, items in results)} 条，错误来源 {len(errors)} 个")


def main(argv=None):
    parser = argparse.ArgumentParser(description="诊断 CQU 通知来源和 WAF 浏览器回退")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="额外运行与服务相同的 HTTP 412 浏览器批次",
    )
    args = parser.parse_args(argv)
    os.makedirs(DIAG_DIR, exist_ok=True)
    log("=" * 68)
    log(f"CQU 抓取诊断  {datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"requests {requests.__version__}  python {sys.version.split()[0]}")
    log("=" * 68)

    parsers = {
        "cqu": cqu_crawler.parse_cqu,
        "xgb": cqu_crawler.parse_xgb,
        "graduate": cqu_crawler.parse_graduate,
        "civil": cqu_crawler.parse_civil,
    }

    total_ok = 0
    session = requests.Session()
    for source in cqu_crawler.SOURCES:
        log("")
        log("-" * 68)
        log(f"[{source['id']}] {source['name']}")
        log(f"  URL: {source['url']}")

        try:
            resp = session.get(
                source["url"],
                timeout=cqu_crawler.REQUEST_TIMEOUT,
                headers=cqu_crawler.HEADERS,
            )
        except Exception as exc:
            log(f"  [X] 网络请求失败: {type(exc).__name__}: {exc}")
            log("      -> 检查网络/代理/DNS；校园站点有时只在国内网络可达")
            continue

        log(f"  HTTP {resp.status_code}  {len(resp.content)} bytes")
        if resp.status_code != 200:
            log(f"  [X] 状态码非 200，页面内容不可信")
            log(f"      final url: {resp.url}")

        declared, guessed, meta = sniff_encoding(resp)
        enc, text = decode_best(resp)
        ratio = han_ratio(text)
        log(f"  编码: header={declared} meta={meta or '-'} 猜测={guessed} -> 采用 {enc}")
        log(f"  中文字符占比: {ratio:.1%}  {'(正常)' if ratio > 0.05 else '(偏低，可能是乱码或空页)'}")

        raw_path = os.path.join(DIAG_DIR, f"{source['id']}.html")
        with open(raw_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        log(f"  原始页面已保存: diag/{source['id']}.html")

        # 对比生产解码与诊断候选解码，便于发现响应头或 meta 声明异常。
        try:
            soup_current = BeautifulSoup(decode_response(resp), "html.parser")
        except requests.RequestException as exc:
            log(f"  [X] 生产解码拒绝该响应: {exc}")
            continue
        soup_fixed = BeautifulSoup(text, "html.parser")

        parser = parsers.get(source["type"])
        for label, soup in (("生产解码", soup_current), ("诊断候选解码", soup_fixed)):
            try:
                got = parser(soup, source["base"])
            except Exception:
                log(f"  解析[{label}]: 抛异常")
                log("    " + traceback.format_exc().replace("\n", "\n    "))
                continue
            log(f"  解析[{label}]: {len(got)} 条")
            for row in got[:3]:
                log(f"      {row[0]}  {row[1][:40]}")

        # 结构探针：页面里到底有没有可用的列表
        n_dates = len(re.findall(r"\d{4}-\d{2}-\d{2}", text))
        log("  结构: <li>={} <a href>={} 日期形串={}".format(
            len(soup_fixed.find_all("li")),
            len(soup_fixed.find_all("a", href=True)),
            n_dates,
        ))
        divs = [d.get("class") for d in soup_fixed.find_all("div", class_=True)][:40]
        flat = sorted({c for cls in divs if cls for c in cls})
        log(f"  div class 样本: {', '.join(flat[:18]) or '(无)'}")

        if parser(soup_fixed, source["base"]):
            total_ok += 1

    session.close()

    log("")
    log("=" * 68)
    log(f"可正常解析的来源: {total_ok}/{len(cqu_crawler.SOURCES)}")
    if args.browser:
        run_production_probe()
    else:
        log("如需验证 WAF 浏览器回退，请运行 python diagnose_sources.py --browser。")
    log("=" * 68)

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"\n报告已写入: {REPORT}")


if __name__ == "__main__":
    configure_stdout()
    main()
