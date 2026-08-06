#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the domestic news index desk."""

from __future__ import annotations

import html

import frontend_shell
import search_widget
from crawler_utils import safe_http_url


DEFAULT_CATEGORIES = ["全部", "主线", "会议", "政策", "国内", "社会", "财经", "国际", "视频", "热搜"]


def _escape(value) -> str:
    return html.escape(str(value or ""), quote=True)


def generate_html(items, errors, crawl_time, categories=None):
    categories = list(categories or DEFAULT_CATEGORIES)
    safe_items = []
    for item in items:
        safe_url = safe_http_url(item.url)
        if safe_url:
            safe_items.append(item._replace(url=safe_url))
    items = safe_items
    total = len(items)
    updated = crawl_time.strftime("%Y-%m-%d %H:%M:%S")

    source_counts = {}
    category_counts = {}
    for item in items:
        source_counts[item.source_name] = source_counts.get(item.source_name, 0) + 1
        category_counts[item.category] = category_counts.get(item.category, 0) + 1

    source_options = ['<option value="all">全部来源</option>']
    index_buttons = [
        '<button class="source-index-button active" type="button" '
        'data-source-target="all" aria-pressed="true">'
        '<span class="source-index-name">全部新闻</span>'
        f'<span class="source-index-count">{total}</span></button>'
    ]
    for source_name, count in sorted(source_counts.items()):
        value = _escape(source_name)
        source_options.append(f'<option value="{value}">{value}</option>')
        index_buttons.append(
            '<button class="source-index-button" type="button" '
            f'data-source-target="{value}" aria-pressed="false">'
            f'<span class="source-index-name">{value}</span>'
            f'<span class="source-index-count">{count}</span></button>'
        )

    category_buttons = []
    for category in categories:
        count = total if category == "全部" else category_counts.get(category, 0)
        active = " active" if category == "全部" else ""
        pressed = "true" if category == "全部" else "false"
        category_buttons.append(
            f'<button class="segment-button category-button{active}" type="button" '
            f'data-category="{_escape(category)}" aria-pressed="{pressed}">'
            f'{_escape(category)}<span>{count}</span></button>'
        )

    rows = []
    for item in items:
        tags = "".join(
            f'<span class="tag">{_escape(tag)}</span>' for tag in item.tags if tag
        )
        if item.hot_score:
            tags += f'<span class="tag hot">热度 {_escape(item.hot_score)}</span>'
        rows.append(
            f"""
<article class="news-item" data-action-scope="news"
  data-url="{_escape(item.url)}" data-title="{_escape(item.title)}"
  data-source="{_escape(item.source_name)}" data-category="{_escape(item.category)}"
  data-date="{_escape(item.date)}" data-py="{_escape(search_widget.py_attr(item.title))}"
  data-spy="{_escape(search_widget.py_attr(item.source_name + ' ' + item.category))}">
  <button class="icon-button favorite-button favorite-btn" type="button"
    data-action="favorite" aria-label="收藏新闻" aria-pressed="false" title="收藏新闻">
    {frontend_shell.icon('star')}
  </button>
  <div class="news-main">
    <div class="news-meta"><span>{_escape(item.source_name)}</span><span>{_escape(item.category)}</span><time>{_escape(item.date)}</time></div>
    <a class="news-title" href="{_escape(item.url)}" target="_blank" rel="noopener">{_escape(item.title)}</a>
    <p class="news-summary">{_escape(item.summary)}</p>
    <div class="tag-row">{tags}</div>
  </div>
  <button class="state-button read-state" type="button" data-action="read-toggle"
    aria-label="标为已读" aria-pressed="false">未读</button>
</article>"""
        )

    header = frontend_shell.render_header(
        active_page="news",
        title="CQU 校务索引台",
        subtitle="国内新闻聚合信息流",
        updated_at=updated,
        total=total,
        unit="条新闻",
        icon_file="news_site.ico",
    )
    errors_html = frontend_shell.render_errors(errors)
    empty_html = frontend_shell.render_empty("新闻", initially_empty=total == 0)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>CQU 校务索引台 · 国内新闻</title>
<link rel="icon" href="news_site.ico">
<style>
{frontend_shell.DESIGN_CSS}
{search_widget.SEARCH_CSS}
</style>
</head>
<body data-page="news" data-refresh-label="新闻">
{header}
<main class="workspace-main">
  <section class="control-band" aria-label="新闻筛选与操作">
    <div class="control-primary">
      <label class="search-field" aria-label="搜索新闻">{frontend_shell.icon('search')}
        <input class="search-input" id="searchInput" type="search"
          placeholder="搜索标题、摘要、来源或拼音" autocomplete="off">
      </label>
      <select class="filter-select" id="sourceFilter" aria-label="按来源筛选">{''.join(source_options)}</select>
      <select class="filter-select" id="stateFilter" aria-label="按状态筛选">
        <option value="all">全部状态</option><option value="new">新内容</option>
        <option value="favorite">收藏</option><option value="unread">未读</option>
      </select>
    </div>
    <div class="control-secondary">
      <div class="segment-control" id="categoryFilter" aria-label="按分类筛选">{''.join(category_buttons)}</div>
      <button class="command-button" type="button" onclick="markAllRead()">{frontend_shell.icon('check')}全部已读</button>
      <button class="command-button primary" id="refreshButton" type="button" onclick="doRefresh()">{frontend_shell.icon('refresh')}<span>刷新</span></button>
    </div>
  </section>
  <div class="workspace-grid">
    <aside class="index-spine" aria-label="新闻来源索引">
      <h2>来源索引</h2>
      <div class="source-index">{''.join(index_buttons)}</div>
      <p class="index-state" id="indexState">当前查看全部来源</p>
    </aside>
    <div class="content-column">
      <p class="result-line" id="resultLine" aria-live="polite">当前显示 <strong>{total}</strong> 条新闻</p>
{errors_html}
{empty_html}
      <section class="news-feed"><div class="news-list">{''.join(rows)}</div></section>
    </div>
  </div>
  <footer class="page-footer">新闻来自公开网页、RSS 与热搜接口；页面状态仅保存在本机。</footer>
</main>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script>{search_widget.SEARCH_JS}</script>
<script>{frontend_shell.COMMON_JS}</script>
<script>
(function() {{
  'use strict';
  var STORAGE_KEYS={{favorites:'news_item_favorites',read:'news_item_read',seen:'news_item_seen_urls'}};
  var activeCategory='全部';
  var hadSeen=false,newUrls=new Set();
  function readSet(key) {{ try {{ return new Set(JSON.parse(localStorage.getItem(key)||'[]')); }} catch(error) {{ return new Set(); }} }}
  function writeSet(key,set) {{ try {{ localStorage.setItem(key,JSON.stringify(Array.from(set))); }} catch(error) {{}} }}
  function showToast(message) {{ var toast=document.getElementById('toast'); toast.textContent=message; toast.className='toast show'; setTimeout(function(){{toast.className='toast';}},2200); }}
  window.doRefresh=async function() {{
    if(location.protocol==='file:') {{ showToast('请从本地服务打开后刷新'); return; }}
    var button=document.getElementById('refreshButton'); button.disabled=true; button.setAttribute('aria-busy','true'); showToast('正在刷新新闻');
    try {{
      var response=await fetch('/refresh',{{method:'POST',cache:'no-store'}}), data=await response.json();
      if(!response.ok||!data.ok) throw new Error(data.message||'刷新失败');
      showToast('刷新完成'); setTimeout(function(){{location.reload();}},350);
    }} catch(error) {{ showToast(error.message||'刷新失败'); }}
    finally {{ button.disabled=false; button.removeAttribute('aria-busy'); }}
  }};
  function items() {{ return Array.prototype.slice.call(document.querySelectorAll('.news-item')); }}
  function syncItem(item,favorites,read) {{
    var url=item.dataset.url, favorite=favorites.has(url), isRead=read.has(url), isNew=newUrls.has(url);
    item.classList.toggle('is-favorite',favorite); item.classList.toggle('is-read',isRead); item.classList.toggle('is-new',isNew);
    var favoriteButton=item.querySelector('[data-action="favorite"]'), readButton=item.querySelector('[data-action="read-toggle"]');
    favoriteButton.setAttribute('aria-pressed',favorite?'true':'false'); favoriteButton.setAttribute('aria-label',favorite?'取消收藏新闻':'收藏新闻'); favoriteButton.title=favorite?'取消收藏新闻':'收藏新闻';
    readButton.textContent=isRead?'已读':'未读'; readButton.setAttribute('aria-pressed',isRead?'true':'false'); readButton.setAttribute('aria-label',isRead?'标为未读':'标为已读');
  }}
  function syncState() {{
    var favorites=readSet(STORAGE_KEYS.favorites),read=readSet(STORAGE_KEYS.read);
    items().forEach(function(item){{syncItem(item,favorites,read);}});
  }}
  function initializeNewState() {{
    var seen=readSet(STORAGE_KEYS.seen); hadSeen=seen.size>0;
    items().forEach(function(item){{if(hadSeen&&!seen.has(item.dataset.url))newUrls.add(item.dataset.url);}});
    items().forEach(function(item){{seen.add(item.dataset.url);}}); writeSet(STORAGE_KEYS.seen,seen);
  }}
  function syncCategoryButtons() {{
    document.querySelectorAll('[data-category]').forEach(function(button){{var active=button.dataset.category===activeCategory;button.classList.toggle('active',active);button.setAttribute('aria-pressed',active?'true':'false');}});
  }}
  function applyFilters() {{ CquSearch.apply(); }}
  function afterSearch(visible,query) {{
    var line='当前显示 <strong>'+visible+'</strong> 条新闻'; if(query) line+='（搜索：'+query.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'）';
    document.getElementById('resultLine').innerHTML=line; document.getElementById('emptyResults').classList.toggle('show',visible===0);
    var select=document.getElementById('sourceFilter'); document.getElementById('indexState').textContent='当前查看 '+select.options[select.selectedIndex].text;
  }}
  function toggleRead(item) {{ var read=readSet(STORAGE_KEYS.read),url=item.dataset.url; if(read.has(url)){{read.delete(url);showToast('已标为未读');}}else{{read.add(url);showToast('已标为已读');}} writeSet(STORAGE_KEYS.read,read);syncState();applyFilters(); }}
  window.markAllRead=function() {{ var read=readSet(STORAGE_KEYS.read);items().forEach(function(item){{read.add(item.dataset.url);}});writeSet(STORAGE_KEYS.read,read);syncState();applyFilters();showToast('当前新闻已全部标为已读'); }};
  document.addEventListener('click',function(event){{
    var favoriteButton=event.target.closest('[data-action="favorite"]');
    if(favoriteButton){{var item=favoriteButton.closest('.news-item'),favorites=readSet(STORAGE_KEYS.favorites),url=item.dataset.url;if(favorites.has(url)){{favorites.delete(url);showToast('已取消收藏');}}else{{favorites.add(url);showToast('已收藏');}}writeSet(STORAGE_KEYS.favorites,favorites);syncState();applyFilters();return;}}
    var readButton=event.target.closest('[data-action="read-toggle"]');if(readButton){{toggleRead(readButton.closest('.news-item'));return;}}
    var link=event.target.closest('.news-title');if(link){{var read=readSet(STORAGE_KEYS.read);read.add(link.closest('.news-item').dataset.url);writeSet(STORAGE_KEYS.read,read);}}
  }});
  document.addEventListener('DOMContentLoaded',function(){{
    CquSearch.install({{
      input:'#searchInput',items:items,
      text:function(item){{var summary=item.querySelector('.news-summary');return (item.dataset.title||'')+' '+(item.dataset.source||'')+' '+(item.dataset.category||'')+' '+(item.dataset.date||'')+' '+(summary?summary.textContent:'');}},
      pass:function(item){{var source=document.getElementById('sourceFilter').value,state=document.getElementById('stateFilter').value;return (source==='all'||item.dataset.source===source)&&(activeCategory==='全部'||item.dataset.category===activeCategory)&&(state==='all'||(state==='new'&&item.classList.contains('is-new'))||(state==='favorite'&&item.classList.contains('is-favorite'))||(state==='unread'&&!item.classList.contains('is-read')));}},
      hl:[{{el:function(item){{return item.querySelector('.news-title');}},py:true}},{{el:function(item){{return item.querySelector('.news-summary');}},text:function(item){{var p=item.querySelector('.news-summary');return p?(p.dataset.raw||(p.dataset.raw=p.textContent)):'';}},py:false}}],
      after:afterSearch,
      onReset:function(){{document.getElementById('sourceFilter').value='all';document.getElementById('stateFilter').value='all';activeCategory='全部';syncCategoryButtons();if(window.CquShell)CquShell.syncSourceIndex();}}
    }});
    document.getElementById('sourceFilter').addEventListener('change',applyFilters);document.getElementById('stateFilter').addEventListener('change',applyFilters);
    document.querySelectorAll('[data-category]').forEach(function(button){{button.addEventListener('click',function(){{activeCategory=button.dataset.category;syncCategoryButtons();applyFilters();}});}});
    initializeNewState();
    syncState();
    applyFilters();
  }});
}})();
</script>
</body>
</html>"""
