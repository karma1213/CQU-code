#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the CQU notice index desk."""

from __future__ import annotations

import html

import frontend_shell
import search_widget
from crawler_utils import safe_http_url


def _escape(value) -> str:
    return html.escape(str(value or ""), quote=True)


def generate_html(all_results, crawl_time, errors=None):
    errors = list(errors or [])
    normalized = []
    for source, items in all_results:
        safe_items = []
        for date, title, url in items:
            safe_url = safe_http_url(url)
            if safe_url:
                safe_items.append((date, title, safe_url))
        normalized.append((source, safe_items))

    total = sum(len(items) for _, items in normalized)
    updated = crawl_time.strftime("%Y-%m-%d %H:%M:%S")
    source_options = ['<option value="all">全部来源</option>']
    index_buttons = [
        '<button class="source-index-button active" type="button" '
        'data-source-target="all" aria-pressed="true">'
        '<span class="source-index-name">全部通知</span>'
        f'<span class="source-index-count">{total}</span></button>'
    ]
    groups = []

    for source, items in normalized:
        source_id = _escape(source["id"])
        source_name = _escape(source["name"])
        source_options.append(
            f'<option value="{source_id}">{source_name}</option>'
        )
        index_buttons.append(
            '<button class="source-index-button" type="button" '
            f'data-source-target="{source_id}" aria-pressed="false">'
            f'<span class="source-index-name">{source_name}</span>'
            f'<span class="source-index-count">{len(items)}</span></button>'
        )
        rows = []
        for date, title, url in items:
            title_text = _escape(title)
            date_text = _escape(date)
            url_text = _escape(url)
            rows.append(
                f"""
<article class="notice-item" data-action-scope="notice"
  data-url="{url_text}" data-title="{title_text}" data-source="{source_id}"
  data-sname="{source_name}" data-date="{date_text}"
  data-py="{_escape(search_widget.py_attr(title))}"
  data-spy="{_escape(search_widget.py_attr(source['name']))}">
  <time class="item-date" datetime="{date_text}">{date_text}</time>
  <a class="item-link" href="{url_text}" target="_blank" rel="noopener">
    <span class="item-title">{title_text}</span>
    <span class="item-source">{source_name}</span>
  </a>
  <button class="icon-button favorite-button favorite-btn" type="button"
    data-action="favorite" aria-label="收藏通知" aria-pressed="false" title="收藏通知">
    {frontend_shell.icon('star')}
  </button>
  <button class="state-button read-state" type="button" data-action="read-toggle"
    aria-label="标为已读" aria-pressed="false">未读</button>
</article>"""
            )
        group_body = "".join(rows) or '<div class="notice-item-empty">暂无通知</div>'
        groups.append(
            f"""
<section class="notice-group" data-source-group="{source_id}">
  <div class="group-heading"><h2>{source_name}</h2><span class="group-count">{len(items)} 条</span></div>
  <div class="notice-list">{group_body}</div>
</section>"""
        )

    header = frontend_shell.render_header(
        active_page="notices",
        title="CQU 校务索引台",
        subtitle="重庆大学校务通知",
        updated_at=updated,
        total=total,
        unit="条通知",
        icon_file="cqu_notice.ico",
    )
    errors_html = frontend_shell.render_errors(errors)
    empty_html = frontend_shell.render_empty("通知", initially_empty=total == 0)
    search_icon = frontend_shell.icon("search")
    refresh_icon = frontend_shell.icon("refresh")
    check_icon = frontend_shell.icon("check")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>CQU 校务索引台 · 校务通知</title>
<link rel="icon" href="cqu_notice.ico">
<style>
{frontend_shell.DESIGN_CSS}
{search_widget.SEARCH_CSS}
.notice-item-empty {{ padding:18px 8px; border-bottom:1px solid var(--steel); color:var(--muted); background:var(--surface); }}
</style>
</head>
<body data-page="notices" data-refresh-label="通知">
{header}
<main class="workspace-main">
  <section class="control-band" aria-label="通知筛选与操作">
    <div class="control-primary">
      <label class="search-field" aria-label="搜索通知">{search_icon}
        <input class="search-input" id="searchInput" type="search"
          placeholder="搜索标题、来源、日期或拼音" autocomplete="off">
      </label>
      <select class="filter-select" id="sourceFilter" aria-label="按来源筛选">
        {''.join(source_options)}
      </select>
    </div>
    <div class="control-secondary">
      <div class="segment-control" id="statusFilter" aria-label="按状态筛选">
        <button class="segment-button seg-btn active" type="button" data-filter="all" aria-pressed="true">全部</button>
        <button class="segment-button seg-btn" type="button" data-filter="new" aria-pressed="false">新通知</button>
        <button class="segment-button seg-btn" type="button" data-filter="favorite" aria-pressed="false">收藏</button>
        <button class="segment-button seg-btn" type="button" data-filter="unread" aria-pressed="false">未读</button>
      </div>
      <button class="command-button" type="button" id="markAllReadButton" onclick="markAllRead()">{check_icon}全部已读</button>
      <button class="command-button primary" id="refreshButton" type="button" onclick="doRefresh()">{refresh_icon}<span>刷新</span></button>
    </div>
  </section>
  <div class="workspace-grid">
    <aside class="index-spine" aria-label="通知来源索引">
      <h2>来源索引</h2>
      <div class="source-index">{''.join(index_buttons)}</div>
      <p class="index-state" id="indexState">当前查看全部来源</p>
    </aside>
    <div class="content-column">
      <p class="result-line" id="resultLine" aria-live="polite">当前显示 <strong>{total}</strong> 条通知</p>
{errors_html}
{empty_html}
      <div id="noticeGroups">{''.join(groups)}</div>
    </div>
  </div>
  <footer class="page-footer">通知来自重庆大学公开页面；收藏与已读状态仅保存在本机。</footer>
</main>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script>{search_widget.SEARCH_JS}</script>
<script>{frontend_shell.COMMON_JS}</script>
<script>
(function() {{
  'use strict';
  var STORAGE_KEYS = {{
    favorites:'cqu_notice_favorites',
    read:'cqu_notice_read',
    seen:'cqu_notice_seen_urls'
  }};
  var activeStatus = 'all';
  var hadSeen=false,newUrls=new Set();
  function readSet(key) {{
    try {{ return new Set(JSON.parse(localStorage.getItem(key) || '[]')); }}
    catch (error) {{ return new Set(); }}
  }}
  function writeSet(key,set) {{
    try {{ localStorage.setItem(key,JSON.stringify(Array.from(set))); }}
    catch (error) {{}}
  }}
  function showToast(message) {{
    var toast=document.getElementById('toast');
    toast.textContent=message; toast.className='toast show';
    setTimeout(function(){{ toast.className='toast'; }},2200);
  }}
  window.doRefresh = async function() {{
    if (location.protocol === 'file:') {{ showToast('请从本地服务打开后刷新'); return; }}
    var button=document.getElementById('refreshButton');
    button.disabled=true; button.setAttribute('aria-busy','true'); showToast('正在刷新通知');
    try {{
      var response=await fetch('/refresh',{{method:'POST',cache:'no-store'}});
      var data=await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || '刷新失败');
      showToast('刷新完成'); setTimeout(function(){{ location.reload(); }},350);
    }} catch (error) {{ showToast(error.message || '刷新失败'); }}
    finally {{ button.disabled=false; button.removeAttribute('aria-busy'); }}
  }};
  function items() {{ return Array.prototype.slice.call(document.querySelectorAll('.notice-item')); }}
  function syncItem(item,favorites,read) {{
    var url=item.dataset.url;
    var favorite=favorites.has(url), isRead=read.has(url), isNew=newUrls.has(url);
    item.classList.toggle('is-favorite',favorite);
    item.classList.toggle('is-read',isRead);
    item.classList.toggle('is-new',isNew);
    var favoriteButton=item.querySelector('[data-action="favorite"]');
    var readButton=item.querySelector('[data-action="read-toggle"]');
    favoriteButton.setAttribute('aria-pressed',favorite?'true':'false');
    favoriteButton.setAttribute('aria-label',favorite?'取消收藏通知':'收藏通知');
    favoriteButton.title=favorite?'取消收藏通知':'收藏通知';
    readButton.textContent=isRead?'已读':'未读';
    readButton.setAttribute('aria-pressed',isRead?'true':'false');
    readButton.setAttribute('aria-label',isRead?'标为未读':'标为已读');
  }}
  function syncState() {{
    var favorites=readSet(STORAGE_KEYS.favorites), read=readSet(STORAGE_KEYS.read);
    items().forEach(function(item){{ syncItem(item,favorites,read); }});
  }}
  function initializeNewState() {{
    var seen=readSet(STORAGE_KEYS.seen); hadSeen=seen.size>0;
    items().forEach(function(item){{ if(hadSeen&&!seen.has(item.dataset.url)) newUrls.add(item.dataset.url); }});
    items().forEach(function(item){{ seen.add(item.dataset.url); }}); writeSet(STORAGE_KEYS.seen,seen);
  }}
  function syncStatusButtons() {{
    document.querySelectorAll('[data-filter]').forEach(function(button){{var active=button.dataset.filter===activeStatus;button.classList.toggle('active',active);button.setAttribute('aria-pressed',active?'true':'false');}});
  }}
  function applyFilters() {{ CquSearch.apply(); }}
  function afterSearch(visible,query) {{
    document.querySelectorAll('.notice-group').forEach(function(group){{
      var shown=group.querySelectorAll('.notice-item:not(.hidden)').length;
      group.classList.toggle('hidden',shown===0);
      var count=group.querySelector('.group-count'); if(count) count.textContent=shown+' 条';
    }});
    var line='当前显示 <strong>'+visible+'</strong> 条通知';
    if(query) line+='（搜索：'+query.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'）';
    document.getElementById('resultLine').innerHTML=line;
    document.getElementById('emptyResults').classList.toggle('show',visible===0);
    var select=document.getElementById('sourceFilter');
    document.getElementById('indexState').textContent='当前查看 '+select.options[select.selectedIndex].text;
  }}
  function toggleRead(item) {{
    var read=readSet(STORAGE_KEYS.read), url=item.dataset.url;
    if(read.has(url)) {{ read.delete(url); showToast('已标为未读'); }}
    else {{ read.add(url); showToast('已标为已读'); }}
    writeSet(STORAGE_KEYS.read,read); syncState(); applyFilters();
  }}
  window.markAllRead=function() {{
    var read=readSet(STORAGE_KEYS.read); items().forEach(function(item){{ read.add(item.dataset.url); }});
    writeSet(STORAGE_KEYS.read,read); syncState(); applyFilters(); showToast('当前通知已全部标为已读');
  }};
  document.addEventListener('click',function(event){{
    var favoriteButton=event.target.closest('[data-action="favorite"]');
    if(favoriteButton) {{
      var item=favoriteButton.closest('.notice-item'), favorites=readSet(STORAGE_KEYS.favorites), url=item.dataset.url;
      if(favorites.has(url)) {{ favorites.delete(url); showToast('已取消收藏'); }}
      else {{ favorites.add(url); showToast('已收藏'); }}
      writeSet(STORAGE_KEYS.favorites,favorites); syncState(); applyFilters(); return;
    }}
    var readButton=event.target.closest('[data-action="read-toggle"]');
    if(readButton) {{ toggleRead(readButton.closest('.notice-item')); return; }}
    var link=event.target.closest('.item-link');
    if(link) {{ var read=readSet(STORAGE_KEYS.read); read.add(link.closest('.notice-item').dataset.url); writeSet(STORAGE_KEYS.read,read); }}
  }});
  document.addEventListener('DOMContentLoaded',function(){{
    CquSearch.install({{
      input:'#searchInput', items:items,
      text:function(item){{ return (item.dataset.title||'')+' '+(item.dataset.sname||'')+' '+(item.dataset.date||''); }},
      pass:function(item){{
        var source=document.getElementById('sourceFilter').value;
        return (source==='all'||item.dataset.source===source) &&
          (activeStatus==='all'||(activeStatus==='new'&&item.classList.contains('is-new'))||
           (activeStatus==='favorite'&&item.classList.contains('is-favorite'))||
           (activeStatus==='unread'&&!item.classList.contains('is-read')));
      }},
      hl:[{{el:function(item){{return item.querySelector('.item-title');}},py:true}}],
      after:afterSearch,
      onReset:function(){{
        document.getElementById('sourceFilter').value='all'; activeStatus='all';
        syncStatusButtons();
        if(window.CquShell) CquShell.syncSourceIndex();
      }}
    }});
    document.getElementById('sourceFilter').addEventListener('change',applyFilters);
    document.querySelectorAll('[data-filter]').forEach(function(button){{
      button.addEventListener('click',function(){{
        activeStatus=button.dataset.filter; syncStatusButtons(); applyFilters();
      }});
    }});
    initializeNewState();
    syncState();
    applyFilters();
  }});
}})();
</script>
</body>
</html>"""
