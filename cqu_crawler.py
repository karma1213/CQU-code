#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重庆大学多站点通知公告爬虫
每天自动抓取各学院/部门的最新通知，生成静态 HTML 页面
"""

import requests
import re
import os
import sys
import html as html_lib
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 修复 Windows 终端编码
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ============================================================
# 配置区
# ============================================================
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
MAX_ITEMS_PER_SOURCE = 25
REQUEST_TIMEOUT = 20
CST = timezone(timedelta(hours=8))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

# 注意：土木学院放第一位（置顶），研究生院放最后
SOURCES = [
    {
        "id": "civil",
        "name": "土木工程学院 — 通知公告",
        "url": "https://civil.cqu.edu.cn/xzwb/tzgg.htm",
        "base": "https://civil.cqu.edu.cn/xzwb/",
        "type": "civil",
    },
    {
        "id": "cqu",
        "name": "重庆大学 — 通知公告",
        "url": "https://www.cqu.edu.cn/tzgg.htm",
        "base": "https://www.cqu.edu.cn/",
        "type": "cqu",
    },
    {
        "id": "xgb_xsgl",
        "name": "学工部 — 学生奖励",
        "url": "https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1006",
        "base": "https://xgb.cqu.edu.cn/",
        "type": "xgb",
    },
    {
        "id": "xgb_sizheng",
        "name": "学工部 — 思政教育",
        "url": "https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1005",
        "base": "https://xgb.cqu.edu.cn/",
        "type": "xgb",
    },
    {
        "id": "graduate",
        "name": "研究生院 — 通知公告",
        "url": "https://graduate.cqu.edu.cn/tzgg.htm",
        "base": "https://graduate.cqu.edu.cn/",
        "type": "graduate",
    },
]


def fetch_page(url):
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        r.encoding = "utf-8-sig"
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] 抓取失败: {e}")
        return None


def clean_title(title, max_len=120):
    """清理标题：去多余空格、截断过长标题"""
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > max_len:
        title = title[:max_len] + "…"
    return title


def parse_cqu(soup, base):
    items = []
    for li in soup.find_all("li"):
        a = li.find("a", href=True) if li else None
        if not a:
            continue
        title = a.get_text(strip=True)
        if len(title) < 8:
            continue
        if any(kw in title for kw in ["重大新闻", "校情概", "机构设置", "教育教学",
                                        "科学研究", "招生就业", "人才招聘", "合作交流",
                                        "校园生活", "走进重大", "报告讲座", "科研动",
                                        "通知公告", "全媒矩阵", "休启乡"]):
            continue
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", title)
        if not date_match:
            continue
        date = date_match.group(1)
        clean = re.sub(r"^\d{4}-\d{2}-\d{2}～浏览量：", "", title)
        clean = re.sub(r"^\d{4}-\d{2}-\d{2}", "", clean)
        clean = re.sub(r"^[｜｜\s]*浏览数[：:]\s*", "", clean)
        clean = clean_title(clean)
        full_url = urljoin(base, a["href"])
        items.append((date, clean, full_url))
    return items


def parse_xgb(soup, base):
    items = []
    content_div = soup.find("div", class_=re.compile(r"list-content", re.I))
    if not content_div:
        content_div = soup.find("div", class_=re.compile(r"main", re.I))
    if not content_div:
        return items
    for a in content_div.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]
        if len(title) < 6 or title in ("首页", "更多+", "更多》"):
            continue
        parent = a.find_parent(["li", "div", "p"])
        full_text = parent.get_text(" ", strip=True) if parent else title
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", full_text)
        if not date_match:
            continue
        date = date_match.group(1)
        clean = clean_title(title)
        full_url = urljoin(base, href)
        items.append((date, clean, full_url))
    return items


def parse_graduate(soup, base):
    """研究生院 — 提取并精简标题"""
    items = []
    content_div = soup.find("div", class_=re.compile(r"search-list", re.I))
    if not content_div:
        content_div = soup.find("div", class_=re.compile(r"teacher-center-box-right", re.I))
    if not content_div:
        return items

    for a in content_div.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]
        if len(title) < 8:
            continue

        # 格式: "252026-05转发..." — 前2位=日, 后4位+横线+2位=年月
        date_match = re.match(r"(\d{2})(\d{4}-\d{2})", title)
        if not date_match:
            continue

        day = date_match.group(1)
        year_month = date_match.group(2)
        date = f"{year_month}-{day}"

        # 去掉日期前缀
        raw_title = title[len(date_match.group(0)):].lstrip(" \u200b\u3000")

        # 去掉开头括号类标注：【研创基地·科研创新】、[研创基地·大赛] 等
        raw_title = re.sub(r"^[\[【][^\]】]*[\]】]\s*", "", raw_title)

        # 截断正文开头：标题后紧跟的正文说明文字
        # 先用常见模式拆分
        for sep in [
            "各相关单位", "各学院", "各研究生培养单位",
            "依据", "根据", "现将", "为进一步", "为推进", "为深入",
            "为贯彻", "为鼓励", "为积极", "为做好",
        ]:
            parts = re.split(rf"(?:{re.escape(sep)}[：:（(]?)", raw_title, maxsplit=1)
            if len(parts) > 1 and len(parts[0]) >= 8:
                raw_title = parts[0]
                break

        # 如果标题以"的通知""的公示""的决定"等结尾但后面还有正文，截断
        title_end = re.match(r"^(.+?(?:的通知|的公示|的决定|的启事|的报告|的办法|的公告|的安排|通知))", raw_title)
        if title_end and len(title_end.group(1)) < len(raw_title) * 0.8:
            raw_title = title_end.group(1)

        clean = clean_title(raw_title)

        # 过滤非通知链接
        if not href or href == "#":
            continue
        if href.startswith("http") and "cqu.edu.cn" not in href:
            continue

        full_url = urljoin(base, href)
        items.append((date, clean, full_url))
    return items


def parse_civil(soup, base):
    items = []
    for li in soup.find_all("li"):
        a = li.find("a", href=True) if li else None
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a["href"]
        if len(title) < 6:
            continue
        if href.startswith("http") or "b2025/" in href or href.startswith("#"):
            continue
        date_str = ""
        span = li.find("span")
        if span:
            dm = re.search(r"(\d{4}-\d{2}-\d{2})", span.get_text())
            if dm:
                date_str = dm.group(1)
        if not date_str:
            dm = re.search(r"(\d{4}-\d{2}-\d{2})", title)
            if dm:
                date_str = dm.group(1)
        if not date_str:
            continue
        clean = clean_title(title)
        full_url = urljoin(base, href)
        items.append((date_str, clean, full_url))
    return items


def crawl_source(source):
    print(f"正在抓取: {source['name']}")
    soup = fetch_page(source["url"])
    if soup is None:
        return []
    parser = {"cqu": parse_cqu, "xgb": parse_xgb, "graduate": parse_graduate, "civil": parse_civil}
    p = parser.get(source["type"])
    if not p:
        return []
    items = p(soup, source["base"])
    # 去重
    seen = set()
    unique = []
    for date, title, url in items:
        key = url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            unique.append((date, title, url))
    unique.sort(key=lambda x: x[0], reverse=True)
    return unique[:MAX_ITEMS_PER_SOURCE]


def generate_html_legacy(all_results, crawl_time):
    now_str = crawl_time.strftime("%Y-%m-%d %H:%M:%S")
    total = sum(len(items) for _, items in all_results)

    cards = ""
    for source, items in all_results:
        if not items:
            cards += f"""
            <div class="card">
                <div class="card-header">
                    <span class="card-title">{source['name']}</span>
                    <span class="card-count">0 条</span>
                </div>
                <div class="card-body empty">暂无数据</div>
            </div>"""
            continue
        lis = ""
        for date, title, url in items:
            safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
            lis += f"""
            <a class="item" href="{url}" target="_blank" rel="noopener">
                <time datetime="{date}">{date}</time>
                <span class="item-title">{safe_title}</span>
                <svg class="item-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
            </a>"""
        cards += f"""
        <div class="card" data-source="{source['id']}">
            <div class="card-header">
                <span class="card-title">{source['name']}</span>
                <span class="card-count">{len(items)} 条</span>
            </div>
            <div class="card-body">{lis}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>重庆大学通知公告聚合</title>
<style>
  :root {{
    --bg: #f0f2f5;
    --surface: #ffffff;
    --text: #1f2937;
    --text2: #6b7280;
    --text3: #9ca3af;
    --primary: #b91c1c;
    --primary-light: #fef2f2;
    --primary-hover: #dc2626;
    --border: #e5e7eb;
    --radius: 16px;
    --shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.06);
    --shadow-lg: 0 4px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", "Helvetica Neue", sans-serif;
    background: var(--bg); color: var(--text); line-height:1.6;
  }}
  .topbar {{
    background: linear-gradient(135deg, #b91c1c 0%, #dc2626 50%, #ef4444 100%);
    color:#fff; padding:28px 20px 22px; text-align:center;
  }}
  .topbar h1 {{ font-size:1.5rem; font-weight:700; letter-spacing:0.5px; }}
  .topbar p {{ font-size:0.82rem; opacity:.85; margin-top:2px; }}
  .topbar .meta {{ font-size:0.75rem; opacity:.65; margin-top:8px; }}
  .container {{ max-width:960px; margin:0 auto; padding:16px 12px 32px; }}
  .toolbar {{
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom:16px; gap:8px; flex-wrap:wrap;
  }}
  .toolbar-left {{ font-size:0.82rem; color:var(--text2); }}
  .toolbar-left strong {{ color:var(--text); }}
  .btn-group {{ display:flex; gap:6px; }}
  .btn {{
    display:inline-flex; align-items:center; gap:5px;
    padding:7px 16px; border-radius:10px; font-size:0.8rem;
    border:none; cursor:pointer; text-decoration:none;
    transition:all .15s; font-weight:500;
  }}
  .btn-primary {{
    background:var(--primary); color:#fff;
  }}
  .btn-primary:hover {{ background:var(--primary-hover); transform:translateY(-1px); }}
  .btn-outline {{
    background:var(--surface); color:var(--text2); border:1px solid var(--border);
  }}
  .btn-outline:hover {{ border-color:var(--primary); color:var(--primary); }}
  .card {{
    background:var(--surface); border-radius:var(--radius);
    box-shadow:var(--shadow); margin-bottom:14px; overflow:hidden;
    transition:box-shadow .2s;
  }}
  .card:hover {{ box-shadow:var(--shadow-lg); }}
  .card-header {{
    display:flex; justify-content:space-between; align-items:center;
    padding:14px 20px; border-bottom:1px solid var(--border);
  }}
  .card-title {{ font-size:0.92rem; font-weight:600; }}
  .card-count {{
    font-size:0.72rem; color:var(--text2);
    background:var(--bg); padding:2px 10px; border-radius:12px;
  }}
  .card-body {{ padding:4px 0; }}
  .card-body.empty {{ padding:36px 20px; text-align:center; color:var(--text3); font-size:0.85rem; }}
  .item {{
    display:flex; align-items:center; gap:12px;
    padding:10px 20px; text-decoration:none; color:var(--text);
    border-bottom:1px solid var(--border); transition:background .12s;
  }}
  .item:last-child {{ border-bottom:none; }}
  .item:hover {{ background:var(--primary-light); }}
  .item:visited .item-title {{ color:#9ca3af; }}
  .item:visited time {{ opacity:.6; }}
  .item time {{
    flex-shrink:0; font-size:0.74rem; color:var(--text2);
    background:var(--bg); padding:2px 8px; border-radius:6px;
    white-space:nowrap; min-width:78px; text-align:center;
    font-feature-settings:"tnum";
  }}
  .item-title {{
    flex:1; font-size:0.88rem; line-height:1.5;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
    overflow:hidden;
  }}
  .item-arrow {{
    flex-shrink:0; color:var(--text3); opacity:0;
    transition:opacity .12s, transform .12s;
  }}
  .item:hover .item-arrow {{ opacity:1; transform:translateX(3px); }}
  .toast {{
    position:fixed; bottom:24px; left:50%; transform:translateX(-50%);
    background:#1f2937; color:#fff; padding:10px 24px; border-radius:12px;
    font-size:0.82rem; opacity:0; transition:all .3s;
    pointer-events:none; z-index:999;
  }}
  .toast.show {{ opacity:1; }}
  @media (max-width:640px) {{
    .container {{ padding:10px 8px; }}
    .card-header {{ padding:12px 14px; }}
    .item {{ padding:8px 14px; gap:8px; }}
    .item time {{ min-width:68px; font-size:0.7rem; }}
    .item-title {{ font-size:0.84rem; }}
    .topbar {{ padding:20px 16px 16px; }}
    .topbar h1 {{ font-size:1.2rem; }}
    .toolbar {{ flex-direction:column; align-items:stretch; }}
    .btn-group {{ justify-content:flex-end; }}
  }}
</style>
</head>
<body>
<div class="topbar">
  <h1>🏫 重庆大学通知公告</h1>
  <p>自动聚合 · 每日更新</p>
  <div class="meta" id="updateMeta">更新于 {now_str} · 共 {total} 条通知</div>
</div>
<div class="container">
  <div class="toolbar">
    <div class="toolbar-left">共 <strong>{total}</strong> 条通知</div>
    <div class="btn-group">
      <button class="btn btn-primary" onclick="doRefresh()">⟳ 刷新页面</button>
      <a class="btn btn-outline" href="#" onclick="scrollToTop()">↑ 回到顶部</a>
    </div>
  </div>
  {cards}
  <div style="text-align:center;padding:20px 0 8px;font-size:0.74rem;color:var(--text3);">
    <p>数据来源：重庆大学各官方网站 · 自动抓取仅供参考</p>
    <p style="margin-top:2px;">如需重新抓取数据，请双击桌面「重大通知刷新」快捷方式</p>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
  function showToast(msg) {{
    var t = document.getElementById('toast');
    t.textContent = msg; t.className = 'toast show';
    setTimeout(function(){{ t.className = 'toast'; }}, 2500);
  }}
  function scrollToTop() {{
    window.scrollTo({{ top:0, behavior:'smooth' }}); return false;
  }}
  async function doRefresh() {{
    if (location.protocol === 'file:') {{
      showToast('请用桌面快捷方式打开，页面刷新按钮才能重新抓取数据');
      return;
    }}
    showToast('正在重新抓取通知…');
    try {{
      var response = await fetch('/refresh', {{ method: 'POST', cache: 'no-store' }});
      var data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || '刷新失败');
      showToast('刷新完成，正在更新页面…');
      setTimeout(function(){{ location.reload(); }}, 500);
    }} catch (err) {{
      showToast(err.message || '刷新失败，请稍后重试');
    }}
  }}
  // 显示相对时间
  (function() {{
    var meta = document.getElementById('updateMeta');
    if (!meta) return;
    var m = meta.textContent.match(/(\\d{{4}})-(\\d{{2}})-(\\d{{2}}) (\\d{{2}}):(\\d{{2}}):(\\d{{2}})/);
    if (!m) return;
    var updated = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]);
    var diff = Math.floor((Date.now() - updated) / 60000);
    var rel = '';
    if (diff < 1) rel = '刚刚更新';
    else if (diff < 60) rel = diff + ' 分钟前更新';
    else if (diff < 1440) rel = Math.floor(diff/60) + ' 小时前更新';
    else rel = Math.floor(diff/1440) + ' 天前更新';
    meta.textContent = '更新于 ' + m[1]+'-'+m[2]+'-'+m[3]+' '+m[4]+':'+m[5]+' (' + rel + ') · 共 ' + meta.textContent.match(/共 (\\d+)/)[1] + ' 条通知';
  }})();
</script>
</body>
</html>"""
    return html


def generate_html(all_results, crawl_time):
    now_str = crawl_time.strftime("%Y-%m-%d %H:%M:%S")
    total = sum(len(items) for _, items in all_results)

    cards = ""
    source_chips = ""
    source_options = ['<option value="all">全部来源</option>']

    for source, items in all_results:
        source_id = html_lib.escape(source["id"], quote=True)
        source_name = html_lib.escape(source["name"], quote=True)
        source_options.append(f'<option value="{source_id}">{source_name}</option>')
        source_chips += f"""
        <div class="source-chip" data-source="{source_id}">
            <span>{source_name}</span>
            <strong>{len(items)}</strong>
        </div>"""

        if not items:
            cards += f"""
        <section class="card" data-source="{source_id}">
            <div class="card-header">
                <div>
                    <h2 class="card-title">{source_name}</h2>
                    <p class="card-subtitle">暂无可展示通知</p>
                </div>
                <div class="card-count" data-total="0">0 条</div>
            </div>
            <div class="card-body empty">暂无数据</div>
        </section>"""
            continue

        notice_rows = ""
        for date, title, url in items:
            safe_title = html_lib.escape(title, quote=True)
            safe_url = html_lib.escape(url, quote=True)
            safe_date = html_lib.escape(date, quote=True)
            notice_rows += f"""
            <article class="notice-item" data-url="{safe_url}" data-title="{safe_title}" data-source="{source_id}" data-date="{safe_date}">
                <button class="icon-btn favorite-btn" type="button" aria-label="收藏通知" title="收藏通知" data-action="favorite">
                    <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3.8l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6L7.1 19l.9-5.5-4-3.9 5.5-.8L12 3.8z"/></svg>
                </button>
                <a class="item-link" href="{safe_url}" target="_blank" rel="noopener" data-url="{safe_url}" data-title="{safe_title}" data-source="{source_id}" data-date="{safe_date}">
                    <time datetime="{safe_date}">{safe_date}</time>
                    <span class="item-title">{safe_title}</span>
                    <span class="state-badge read-state" role="button" tabindex="0" data-action="read-toggle" aria-label="切换已读状态">未读</span>
                    <span class="state-badge new-state">新</span>
                    <svg class="item-arrow" aria-hidden="true" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
                </a>
            </article>"""

        cards += f"""
        <section class="card" data-source="{source_id}">
            <div class="card-header">
                <div>
                    <h2 class="card-title">{source_name}</h2>
                    <p class="card-subtitle">已收录 {len(items)} 条通知</p>
                </div>
                <div class="card-count" data-total="{len(items)}">{len(items)} 条</div>
            </div>
            <div class="card-body">{notice_rows}
            </div>
        </section>"""

    source_options_html = "\n".join(source_options)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>重庆大学通知公告聚合</title>
<style>
  :root {{
    --bg: #f6f3ee;
    --bg-soft: #fbfaf7;
    --surface: #ffffff;
    --surface-2: #fff8f3;
    --text: #1f2328;
    --text2: #5f6672;
    --text3: #8a919d;
    --primary: #981b1e;
    --primary-2: #c3262d;
    --primary-hover: #7f1518;
    --primary-soft: #fff1f0;
    --gold: #b8892f;
    --gold-soft: #fff6df;
    --border: #e7ddd3;
    --border-strong: #d6c8ba;
    --radius: 12px;
    --shadow: 0 8px 24px rgba(58, 45, 37, 0.08);
    --shadow-lg: 0 16px 36px rgba(58, 45, 37, 0.13);
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", "Helvetica Neue", sans-serif;
    min-width:320px; color:var(--text); line-height:1.6;
    background:linear-gradient(180deg, rgba(152,27,30,0.08), transparent 260px), var(--bg);
  }}
  a {{ color:inherit; }}
  button, input, select {{ font:inherit; }}
  button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible {{
    outline:3px solid rgba(184,137,47,.35); outline-offset:2px;
  }}
  .topbar {{
    color:#fff; border-bottom:4px solid var(--gold);
    background:
      linear-gradient(135deg, rgba(77,12,14,.96), rgba(152,27,30,.96) 48%, rgba(195,38,45,.96)),
      radial-gradient(circle at 20% 0%, rgba(255,255,255,.25), transparent 34%);
  }}
  .topbar-inner {{ max-width:1180px; margin:0 auto; padding:30px 18px 24px; }}
  .brand-row {{ display:flex; align-items:center; justify-content:space-between; gap:18px; }}
  .brand-mark {{
    width:48px; height:48px; border:1px solid rgba(255,255,255,.34); border-radius:50%;
    display:grid; place-items:center; flex:0 0 auto; background:rgba(255,255,255,.12);
    font-weight:800; letter-spacing:.03em;
  }}
  .brand-copy {{ flex:1; min-width:0; }}
  .eyebrow {{ font-size:.78rem; opacity:.78; letter-spacing:.08em; text-transform:uppercase; }}
  h1 {{ font-size:clamp(1.45rem, 3vw, 2.35rem); line-height:1.15; margin-top:4px; font-weight:800; }}
  .topbar p {{ font-size:.95rem; opacity:.86; margin-top:8px; }}
  .topbar .meta {{ font-size:.78rem; opacity:.78; margin-top:14px; }}
  .meta-card {{
    min-width:210px; border:1px solid rgba(255,255,255,.25); border-radius:14px;
    background:rgba(255,255,255,.1); padding:12px 14px; text-align:right;
  }}
  .meta-card strong {{ display:block; font-size:1.65rem; line-height:1; }}
  .meta-card span {{ display:block; margin-top:6px; font-size:.78rem; opacity:.8; }}
  .container {{ max-width:1180px; margin:0 auto; padding:18px 14px 36px; }}
  .source-overview {{
    display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));
    gap:10px; margin:-2px 0 14px;
  }}
  .source-chip {{
    min-height:60px; background:rgba(255,255,255,.82); border:1px solid var(--border);
    border-radius:var(--radius); padding:10px 12px; box-shadow:0 4px 14px rgba(58,45,37,.05);
    display:flex; align-items:center; justify-content:space-between; gap:10px;
  }}
  .source-chip span {{ color:var(--text2); font-size:.78rem; line-height:1.35; }}
  .source-chip strong {{ color:var(--primary); font-size:1.25rem; font-variant-numeric:tabular-nums; }}
  .toolbar {{
    position:sticky; top:0; z-index:20; display:grid; grid-template-columns:minmax(220px, 1fr) auto;
    gap:12px; align-items:center; margin-bottom:14px; padding:12px;
    border:1px solid var(--border); border-radius:16px; background:rgba(255,255,255,.92);
    box-shadow:var(--shadow); backdrop-filter:blur(12px);
  }}
  .filters {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; min-width:0; }}
  .search-wrap {{ position:relative; flex:1 1 260px; min-width:210px; }}
  .search-wrap svg {{
    position:absolute; left:12px; top:50%; transform:translateY(-50%);
    width:18px; height:18px; color:var(--text3);
  }}
  .search-input, .source-select {{
    width:100%; min-height:44px; border:1px solid var(--border-strong); border-radius:10px;
    background:#fff; color:var(--text); padding:0 12px; transition:border-color .16s, box-shadow .16s;
  }}
  .search-input {{ padding-left:38px; }}
  .search-input::placeholder {{ color:var(--text3); }}
  .source-select {{ flex:0 0 190px; cursor:pointer; }}
  .search-input:focus, .source-select:focus {{
    border-color:var(--primary); box-shadow:0 0 0 4px rgba(152,27,30,.08);
  }}
  .toolbar-actions {{ display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:wrap; }}
  .segment {{
    display:flex; min-height:44px; padding:3px; gap:2px; border:1px solid var(--border);
    border-radius:12px; background:var(--bg-soft);
  }}
  .seg-btn {{
    border:0; background:transparent; color:var(--text2); border-radius:9px; padding:0 12px;
    min-width:52px; cursor:pointer; font-weight:600; transition:background .16s, color .16s;
  }}
  .seg-btn.active {{ background:var(--primary); color:#fff; }}
  .btn {{
    display:inline-flex; align-items:center; justify-content:center; gap:7px;
    min-height:44px; padding:0 14px; border-radius:10px; font-size:.86rem;
    border:1px solid transparent; cursor:pointer; text-decoration:none;
    transition:background .15s, color .15s, border-color .15s, transform .15s; font-weight:650;
  }}
  .btn svg {{ width:17px; height:17px; stroke:currentColor; fill:none; stroke-width:2; }}
  .btn-primary {{ background:var(--primary); color:#fff; }}
  .btn-primary:hover {{ background:var(--primary-hover); transform:translateY(-1px); }}
  .btn-outline {{ background:var(--surface); color:var(--text2); border-color:var(--border-strong); }}
  .btn-outline:hover {{ border-color:var(--primary); color:var(--primary); background:var(--primary-soft); }}
  .result-line {{ margin:0 2px 12px; color:var(--text2); font-size:.88rem; }}
  .result-line strong {{ color:var(--primary); font-variant-numeric:tabular-nums; }}
  .card {{
    background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow);
    margin-bottom:14px; overflow:hidden; border:1px solid var(--border);
    transition:box-shadow .2s, transform .2s;
  }}
  .card:hover {{ box-shadow:var(--shadow-lg); transform:translateY(-1px); }}
  .card.hidden, .notice-item.hidden {{ display:none; }}
  .card-header {{
    display:flex; justify-content:space-between; align-items:center; gap:12px;
    padding:14px 18px; border-bottom:1px solid var(--border);
    background:linear-gradient(90deg, var(--surface-2), #fff);
  }}
  .card-title {{ font-size:1rem; font-weight:750; color:var(--text); }}
  .card-subtitle {{ margin-top:1px; color:var(--text3); font-size:.78rem; }}
  .card-count {{
    flex:0 0 auto; font-size:.78rem; color:var(--primary); font-weight:700;
    background:var(--primary-soft); padding:4px 10px; border-radius:999px; border:1px solid rgba(152,27,30,.12);
  }}
  .card-body {{ padding:0; }}
  .card-body.empty {{ padding:36px 20px; text-align:center; color:var(--text3); font-size:.9rem; }}
  .notice-item {{
    display:grid; grid-template-columns:44px minmax(0, 1fr); align-items:center;
    min-height:58px; border-bottom:1px solid var(--border); transition:background .14s;
  }}
  .notice-item:last-child {{ border-bottom:none; }}
  .notice-item:hover {{ background:var(--primary-soft); }}
  .notice-item.is-read .item-title {{ color:#7d8490; }}
  .notice-item.is-read time {{ opacity:.7; }}
  .notice-item.is-favorite {{ background:linear-gradient(90deg, var(--gold-soft), #fff 42%); }}
  .notice-item.is-new {{ box-shadow:inset 4px 0 0 var(--primary-2); }}
  .icon-btn {{
    width:44px; height:44px; border:0; background:transparent; cursor:pointer;
    display:grid; place-items:center; color:var(--text3); transition:color .15s, transform .15s;
  }}
  .icon-btn svg {{ width:20px; height:20px; fill:none; stroke:currentColor; stroke-width:1.8; }}
  .icon-btn:hover {{ color:var(--gold); transform:scale(1.06); }}
  .notice-item.is-favorite .favorite-btn {{ color:var(--gold); }}
  .notice-item.is-favorite .favorite-btn svg {{ fill:currentColor; }}
  .item-link {{
    min-width:0; min-height:58px; display:grid; grid-template-columns:96px minmax(0, 1fr) auto auto 20px;
    align-items:center; gap:10px; padding:8px 14px 8px 0; text-decoration:none; color:var(--text);
  }}
  .item-link time {{
    font-size:.78rem; color:var(--text2); background:var(--bg-soft); padding:4px 8px;
    border-radius:8px; white-space:nowrap; text-align:center; font-feature-settings:"tnum";
  }}
  .item-title {{
    min-width:0; font-size:.92rem; line-height:1.45;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
  }}
  .state-badge {{
    display:inline-flex; align-items:center; justify-content:center; min-height:24px;
    padding:0 8px; border-radius:999px; font-size:.72rem; font-weight:700; white-space:nowrap;
  }}
  .read-state {{ color:#48606f; background:#edf4f7; cursor:pointer; user-select:none; }}
  .read-state:hover {{ color:var(--primary); background:var(--primary-soft); }}
  .notice-item.is-read .read-state {{ color:#7d8490; background:#f1f2f4; }}
  .new-state {{ display:none; color:#fff; background:var(--primary-2); }}
  .notice-item.is-new .new-state {{ display:inline-flex; }}
  .item-arrow {{
    width:18px; height:18px; fill:none; stroke:currentColor; stroke-width:2;
    color:var(--text3); opacity:.55; transition:opacity .12s, transform .12s;
  }}
  .notice-item:hover .item-arrow {{ opacity:1; transform:translateX(3px); }}
  .empty-results {{
    display:none; text-align:center; padding:42px 16px; border:1px dashed var(--border-strong);
    border-radius:var(--radius); color:var(--text2); background:rgba(255,255,255,.66);
  }}
  .empty-results.show {{ display:block; }}
  .toast {{
    position:fixed; bottom:24px; left:50%; transform:translateX(-50%);
    background:#1f2328; color:#fff; padding:11px 22px; border-radius:12px;
    font-size:.88rem; opacity:0; transition:opacity .24s, transform .24s;
    pointer-events:none; z-index:999;
  }}
  .toast.show {{ opacity:1; transform:translateX(-50%) translateY(-4px); }}
  footer {{ text-align:center; padding:20px 0 8px; font-size:.78rem; color:var(--text3); }}
  footer p + p {{ margin-top:2px; }}
  @media (max-width:900px) {{
    .brand-row {{ align-items:flex-start; }}
    .meta-card {{ display:none; }}
    .toolbar {{ grid-template-columns:1fr; }}
    .toolbar-actions {{ justify-content:flex-start; }}
  }}
  @media (max-width:640px) {{
    .topbar-inner {{ padding:22px 14px 18px; }}
    .brand-mark {{ width:40px; height:40px; font-size:.9rem; }}
    .container {{ padding:12px 10px 28px; }}
    .source-overview {{ grid-template-columns:1fr 1fr; }}
    .filters, .toolbar-actions {{ width:100%; }}
    .search-wrap, .source-select {{ flex:1 1 100%; min-width:0; }}
    .segment {{ width:100%; overflow:auto; }}
    .seg-btn {{ flex:1 0 auto; }}
    .btn {{ flex:1 1 auto; }}
    .card-header {{ padding:12px 14px; align-items:flex-start; }}
    .notice-item {{ grid-template-columns:42px minmax(0, 1fr); min-height:74px; }}
    .icon-btn {{ width:42px; height:52px; }}
    .item-link {{
      grid-template-columns:minmax(0, 1fr) auto auto;
      grid-template-areas:"title title title" "date read arrow";
      gap:6px 8px; min-height:74px; padding:9px 10px 9px 0;
    }}
    .item-link time {{ grid-area:date; width:max-content; font-size:.72rem; }}
    .item-title {{ grid-area:title; font-size:.9rem; -webkit-line-clamp:3; }}
    .read-state {{ grid-area:read; }}
    .new-state {{ grid-area:read; transform:translateX(42px); }}
    .item-arrow {{ grid-area:arrow; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{ scroll-behavior:auto !important; transition:none !important; }}
  }}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-inner">
    <div class="brand-row">
      <div class="brand-mark" aria-hidden="true">CQU</div>
      <div class="brand-copy">
        <div class="eyebrow">Chongqing University Notice Hub</div>
        <h1>重庆大学通知公告聚合</h1>
        <p>聚合校内多站点通知，支持收藏、已读与新增追踪。</p>
        <div class="meta" id="updateMeta">更新于 {now_str} · 共 {total} 条通知</div>
      </div>
      <div class="meta-card" aria-label="通知总数">
        <strong>{total}</strong>
        <span>条通知已收录</span>
      </div>
    </div>
  </div>
</div>
<div class="container">
  <div class="source-overview" aria-label="来源概览">
    {source_chips}
  </div>
  <div class="toolbar">
    <div class="filters">
      <label class="search-wrap" aria-label="搜索通知">
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M10.5 18a7.5 7.5 0 1 1 5.3-2.2L21 21" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <input class="search-input" id="searchInput" type="search" placeholder="搜索标题关键词">
      </label>
      <select class="source-select" id="sourceFilter" aria-label="按来源筛选">
        {source_options_html}
      </select>
    </div>
    <div class="toolbar-actions">
      <div class="segment" role="tablist" aria-label="通知状态筛选">
        <button class="seg-btn active" type="button" data-filter="all">全部</button>
        <button class="seg-btn" type="button" data-filter="new">新通知</button>
        <button class="seg-btn" type="button" data-filter="favorite">收藏</button>
        <button class="seg-btn" type="button" data-filter="unread">未读</button>
      </div>
      <button class="btn btn-outline" type="button" onclick="markAllRead()">
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>
        全部已读
      </button>
      <button class="btn btn-primary" type="button" onclick="doRefresh()">
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 1-15.6 6.1M3 12A9 9 0 0 1 18.6 5.9M18 2v5h-5M6 22v-5h5"/></svg>
        刷新
      </button>
      <a class="btn btn-outline" href="#" onclick="scrollToTop()">
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m18 15-6-6-6 6"/></svg>
        顶部
      </a>
    </div>
  </div>
  <div class="result-line" id="resultLine">当前显示 <strong>{total}</strong> 条通知</div>
  <div class="empty-results" id="emptyResults">没有匹配的通知，换个关键词或筛选条件试试。</div>
  {cards}
  <footer>
    <p>数据来源：重庆大学各官方网站 · 自动抓取仅供参考</p>
    <p>如需重新抓取数据，请双击桌面「重大通知刷新」快捷方式</p>
  </footer>
</div>
<div class="toast" id="toast"></div>
<script>
  var STORAGE_KEYS = {{
    favorites: 'cqu_notice_favorites',
    read: 'cqu_notice_read',
    seen: 'cqu_notice_seen_urls'
  }};
  var activeStatus = 'all';

  function readSet(key) {{
    try {{
      var raw = localStorage.getItem(key);
      return new Set(raw ? JSON.parse(raw) : []);
    }} catch (err) {{
      return new Set();
    }}
  }}

  function writeSet(key, set) {{
    localStorage.setItem(key, JSON.stringify(Array.from(set)));
  }}

  function showToast(msg) {{
    var t = document.getElementById('toast');
    t.textContent = msg; t.className = 'toast show';
    setTimeout(function(){{ t.className = 'toast'; }}, 2500);
  }}

  function scrollToTop() {{
    window.scrollTo({{ top:0, behavior:'smooth' }});
    return false;
  }}

  async function doRefresh() {{
    if (location.protocol === 'file:') {{
      showToast('请用桌面快捷方式打开，页面刷新按钮才能重新抓取数据');
      return;
    }}
    showToast('正在重新抓取通知…');
    try {{
      var response = await fetch('/refresh', {{ method: 'POST', cache: 'no-store' }});
      var data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || '刷新失败');
      showToast('刷新完成，正在更新页面…');
      setTimeout(function(){{ location.reload(); }}, 500);
    }} catch (err) {{
      showToast(err.message || '刷新失败，请稍后重试');
    }}
  }}

  function getItems() {{
    return Array.prototype.slice.call(document.querySelectorAll('.notice-item'));
  }}

  function applyItemState(item, favorites, read, seen) {{
    var url = item.dataset.url;
    var isFavorite = favorites.has(url);
    var isRead = read.has(url);
    var isNew = seen.size > 0 && !seen.has(url);
    item.classList.toggle('is-favorite', isFavorite);
    item.classList.toggle('is-read', isRead);
    item.classList.toggle('is-new', isNew);
    var favoriteBtn = item.querySelector('.favorite-btn');
    var readState = item.querySelector('.read-state');
    if (favoriteBtn) {{
      favoriteBtn.setAttribute('aria-pressed', isFavorite ? 'true' : 'false');
      favoriteBtn.setAttribute('aria-label', isFavorite ? '取消收藏通知' : '收藏通知');
      favoriteBtn.title = isFavorite ? '取消收藏通知' : '收藏通知';
    }}
    if (readState) readState.textContent = isRead ? '已读' : '未读';
  }}

  function syncState() {{
    var favorites = readSet(STORAGE_KEYS.favorites);
    var read = readSet(STORAGE_KEYS.read);
    var seen = readSet(STORAGE_KEYS.seen);
    var currentUrls = new Set();
    getItems().forEach(function(item) {{
      currentUrls.add(item.dataset.url);
      applyItemState(item, favorites, read, seen);
    }});
    currentUrls.forEach(function(url) {{ seen.add(url); }});
    writeSet(STORAGE_KEYS.seen, seen);
  }}

  function applyFilters() {{
    var query = (document.getElementById('searchInput').value || '').trim().toLowerCase();
    var source = document.getElementById('sourceFilter').value;
    var visibleCount = 0;
    document.querySelectorAll('.card').forEach(function(card) {{
      var cardVisible = false;
      var cardVisibleCount = 0;
      card.querySelectorAll('.notice-item').forEach(function(item) {{
        var matchesText = !query || (item.dataset.title || '').toLowerCase().indexOf(query) !== -1;
        var matchesSource = source === 'all' || item.dataset.source === source;
        var matchesStatus =
          activeStatus === 'all' ||
          (activeStatus === 'new' && item.classList.contains('is-new')) ||
          (activeStatus === 'favorite' && item.classList.contains('is-favorite')) ||
          (activeStatus === 'unread' && !item.classList.contains('is-read'));
        var visible = matchesText && matchesSource && matchesStatus;
        item.classList.toggle('hidden', !visible);
        if (visible) {{
          visibleCount += 1;
          cardVisibleCount += 1;
          cardVisible = true;
        }}
      }});
      var hasItems = card.querySelector('.notice-item') !== null;
      card.classList.toggle('hidden', hasItems && !cardVisible);
      var count = card.querySelector('.card-count');
      if (count && hasItems) count.textContent = cardVisibleCount + ' 条';
    }});
    document.getElementById('resultLine').innerHTML = '当前显示 <strong>' + visibleCount + '</strong> 条通知';
    document.getElementById('emptyResults').classList.toggle('show', visibleCount === 0);
  }}

  function markAllRead() {{
    var read = readSet(STORAGE_KEYS.read);
    getItems().forEach(function(item) {{ read.add(item.dataset.url); }});
    writeSet(STORAGE_KEYS.read, read);
    syncState();
    applyFilters();
    showToast('已将当前页面通知标为已读');
  }}

  function toggleReadState(item) {{
    var read = readSet(STORAGE_KEYS.read);
    var url = item.dataset.url;
    if (read.has(url)) {{
      read.delete(url);
      showToast('已标为未读');
    }} else {{
      read.add(url);
      showToast('已标为已读');
    }}
    writeSet(STORAGE_KEYS.read, read);
    syncState();
    applyFilters();
  }}

  document.addEventListener('click', function(event) {{
    var favoriteBtn = event.target.closest('[data-action="favorite"]');
    if (favoriteBtn) {{
      event.preventDefault();
      event.stopPropagation();
      var item = favoriteBtn.closest('.notice-item');
      var favorites = readSet(STORAGE_KEYS.favorites);
      if (favorites.has(item.dataset.url)) {{
        favorites.delete(item.dataset.url);
        showToast('已取消收藏');
      }} else {{
        favorites.add(item.dataset.url);
        showToast('已收藏');
      }}
      writeSet(STORAGE_KEYS.favorites, favorites);
      syncState();
      applyFilters();
      return;
    }}
    var readToggle = event.target.closest('[data-action="read-toggle"]');
    if (readToggle) {{
      event.preventDefault();
      event.stopPropagation();
      var readItem = readToggle.closest('.notice-item');
      if (readItem) toggleReadState(readItem);
      return;
    }}
    var link = event.target.closest('.item-link');
    if (link) {{
      var row = link.closest('.notice-item');
      if (row) {{
        var read = readSet(STORAGE_KEYS.read);
        read.add(row.dataset.url);
        writeSet(STORAGE_KEYS.read, read);
        syncState();
        applyFilters();
      }}
    }}
  }});

  document.addEventListener('keydown', function(event) {{
    var readToggle = event.target.closest('[data-action="read-toggle"]');
    if (!readToggle || (event.key !== 'Enter' && event.key !== ' ')) return;
    event.preventDefault();
    var item = readToggle.closest('.notice-item');
    if (item) toggleReadState(item);
  }});

  document.addEventListener('DOMContentLoaded', function() {{
    syncState();
    applyFilters();
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('sourceFilter').addEventListener('change', applyFilters);
    document.querySelectorAll('.seg-btn').forEach(function(btn) {{
      btn.addEventListener('click', function() {{
        document.querySelectorAll('.seg-btn').forEach(function(item) {{ item.classList.remove('active'); }});
        btn.classList.add('active');
        activeStatus = btn.dataset.filter;
        applyFilters();
      }});
    }});
  }});

  (function() {{
    var meta = document.getElementById('updateMeta');
    if (!meta) return;
    var m = meta.textContent.match(/(\\d{{4}})-(\\d{{2}})-(\\d{{2}}) (\\d{{2}}):(\\d{{2}}):(\\d{{2}})/);
    if (!m) return;
    var updated = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]);
    var diff = Math.floor((Date.now() - updated) / 60000);
    var rel = '';
    if (diff < 1) rel = '刚刚更新';
    else if (diff < 60) rel = diff + ' 分钟前更新';
    else if (diff < 1440) rel = Math.floor(diff/60) + ' 小时前更新';
    else rel = Math.floor(diff/1440) + ' 天前更新';
    meta.textContent = '更新于 ' + m[1]+'-'+m[2]+'-'+m[3]+' '+m[4]+':'+m[5]+' (' + rel + ') · 共 ' + meta.textContent.match(/共 (\\d+)/)[1] + ' 条通知';
  }})();
</script>
</body>
</html>"""
    return html


def main():
    print("=" * 50)
    print("重庆大学通知公告爬虫")
    print(f"运行时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    all_results = []
    total = 0
    for source in SOURCES:
        items = crawl_source(source)
        all_results.append((source, items))
        total += len(items)
        print(f"  [OK] {len(items)} 条")

    crawl_time = datetime.now(CST)
    html = generate_html(all_results, crawl_time)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{'=' * 50}")
    print(f"共 {total} 条通知 → {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
