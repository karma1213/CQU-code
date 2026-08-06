#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared offline-first shell for the notice and news index pages."""

from __future__ import annotations

import html


DESIGN_CSS = r"""
:root {
  --cqu-crimson:#8b1e27;
  --cqu-crimson-dark:#68151c;
  --ink:#20262d;
  --cool-paper:#f3f5f6;
  --surface:#ffffff;
  --steel:#d5dce1;
  --steel-dark:#aeb9c1;
  --academic-blue:#315e6d;
  --muted:#66717a;
  --success:#2f6b4f;
  --warning:#8a5a12;
  --focus:#176b87;
  --display-font:"STZhongsong","Songti SC","Noto Serif CJK SC",serif;
  --body-font:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  --data-font:"Bahnschrift","Segoe UI",sans-serif;
}
* { box-sizing:border-box; }
html { color-scheme:light; background:var(--cool-paper); }
body {
  min-width:320px;
  margin:0;
  color:var(--ink);
  background:var(--cool-paper);
  font-family:var(--body-font);
  font-size:15px;
  line-height:1.55;
}
button,input,select { font:inherit; }
button,a,select,input { -webkit-tap-highlight-color:transparent; }
a { color:inherit; }
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible {
  outline:3px solid color-mix(in srgb,var(--focus) 55%,transparent);
  outline-offset:2px;
}
.workspace-header {
  position:relative;
  z-index:30;
  border-top:4px solid var(--cqu-crimson);
  border-bottom:1px solid var(--steel);
  background:var(--surface);
}
.workspace-header-inner {
  width:min(1380px,calc(100% - 40px));
  min-height:70px;
  margin:0 auto;
  display:grid;
  grid-template-columns:minmax(260px,1fr) auto auto;
  align-items:center;
  gap:22px;
}
.brand-lockup { min-width:0; display:flex; align-items:center; gap:12px; }
.brand-lockup img { width:38px; height:38px; flex:0 0 auto; }
.brand-copy { min-width:0; }
.brand-copy h1 {
  margin:0;
  overflow-wrap:anywhere;
  font-family:var(--display-font);
  font-size:1.28rem;
  font-weight:700;
  line-height:1.2;
}
.brand-copy p { margin:3px 0 0; color:var(--muted); font-size:.78rem; }
.page-switch {
  display:flex;
  align-items:center;
  border:1px solid var(--steel);
  border-radius:6px;
  overflow:hidden;
  background:var(--cool-paper);
}
.page-switch a {
  min-height:36px;
  display:inline-flex;
  align-items:center;
  padding:0 13px;
  color:var(--muted);
  text-decoration:none;
  font-weight:650;
  white-space:nowrap;
}
.page-switch a + a { border-left:1px solid var(--steel); }
.page-switch a[aria-current="page"] { color:#fff; background:var(--cqu-crimson); }
.header-meta { text-align:right; color:var(--muted); font-size:.75rem; }
.header-meta strong {
  display:block;
  color:var(--ink);
  font-family:var(--data-font);
  font-size:.94rem;
  font-weight:650;
}
.workspace-main { width:min(1380px,calc(100% - 40px)); margin:0 auto; padding:16px 0 28px; }
.control-band {
  position:sticky;
  top:0;
  z-index:20;
  display:grid;
  grid-template-columns:minmax(260px,1fr) minmax(0,auto);
  gap:12px;
  align-items:center;
  padding:10px 0 12px;
  border-bottom:1px solid var(--steel);
  background:color-mix(in srgb,var(--cool-paper) 94%,transparent);
  backdrop-filter:blur(8px);
}
.control-primary,.control-secondary { display:flex; align-items:center; gap:8px; min-width:0; }
.control-secondary { justify-content:flex-end; }
.search-field { position:relative; flex:1 1 320px; min-width:180px; }
.search-field > svg {
  position:absolute;
  left:11px;
  top:50%;
  width:18px;
  height:18px;
  color:var(--muted);
  transform:translateY(-50%);
  pointer-events:none;
}
.search-input,.filter-select {
  width:100%;
  min-height:40px;
  border:1px solid var(--steel-dark);
  border-radius:6px;
  color:var(--ink);
  background:var(--surface);
}
.search-input { padding:0 12px 0 38px; }
.filter-select { width:auto; min-width:144px; padding:0 32px 0 10px; }
.command-button,.icon-button,.state-button,.segment-button {
  min-height:38px;
  border:1px solid var(--steel-dark);
  border-radius:6px;
  color:var(--ink);
  background:var(--surface);
  cursor:pointer;
  transition:background-color .16s,color .16s,border-color .16s,transform .16s;
}
.command-button {
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:7px;
  padding:0 12px;
  white-space:nowrap;
  font-weight:650;
}
.command-button.primary { border-color:var(--cqu-crimson); color:#fff; background:var(--cqu-crimson); }
.command-button:hover,.icon-button:hover,.state-button:hover,.segment-button:hover { border-color:var(--academic-blue); }
.command-button.primary:hover { background:var(--cqu-crimson-dark); }
.command-button:disabled { cursor:wait; opacity:.62; }
.command-button svg,.icon-button svg { width:18px; height:18px; }
.segment-control {
  display:flex;
  min-height:40px;
  padding:2px;
  gap:2px;
  overflow-x:auto;
  border:1px solid var(--steel);
  border-radius:6px;
  background:#e9edef;
}
.segment-button { border-color:transparent; padding:0 10px; color:var(--muted); background:transparent; white-space:nowrap; }
.segment-button.active { color:#fff; border-color:var(--academic-blue); background:var(--academic-blue); }
.segment-button span { margin-left:4px; font-family:var(--data-font); font-size:.74rem; }
.workspace-grid {
  display:grid;
  grid-template-columns:220px minmax(0,1fr);
  gap:24px;
  align-items:start;
  padding-top:16px;
}
.index-spine {
  position:sticky;
  top:78px;
  min-width:0;
  padding:4px 18px 8px 0;
  border-right:2px solid var(--steel);
}
.index-spine h2 {
  margin:0 0 9px;
  color:var(--muted);
  font-family:var(--display-font);
  font-size:.94rem;
}
.source-index { display:grid; gap:2px; }
.source-index-button {
  position:relative;
  width:100%;
  min-height:42px;
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  align-items:center;
  gap:8px;
  padding:5px 7px 5px 13px;
  border:0;
  color:var(--muted);
  background:transparent;
  text-align:left;
  cursor:pointer;
}
.source-index-button::before {
  content:"";
  position:absolute;
  left:-1px;
  top:7px;
  bottom:7px;
  width:3px;
  background:transparent;
}
.source-index-button:hover,.source-index-button.active { color:var(--ink); background:#e9edef; }
.source-index-button.active::before { background:var(--cqu-crimson); }
.source-index-name { min-width:0; overflow-wrap:anywhere; font-size:.82rem; line-height:1.3; }
.source-index-count { color:var(--academic-blue); font-family:var(--data-font); font-size:.88rem; }
.index-state { margin:12px 7px 0; color:var(--muted); font-size:.74rem; }
.content-column { min-width:0; }
.result-line { min-height:30px; margin:0; color:var(--muted); font-size:.84rem; }
.result-line strong { color:var(--cqu-crimson); font-family:var(--data-font); }
.source-errors {
  margin:0 0 14px;
  border:1px solid #d8b9ac;
  border-left:4px solid var(--warning);
  border-radius:4px;
  background:#fffaf4;
}
.source-errors summary {
  min-height:40px;
  display:flex;
  align-items:center;
  gap:8px;
  padding:7px 10px;
  color:#68440e;
  cursor:pointer;
  font-weight:650;
}
.source-error-list { margin:0; padding:0 12px 10px 32px; color:var(--muted); font-size:.8rem; }
.source-error-heading { margin:0; padding:2px 12px 5px; color:var(--ink); font-size:.8rem; font-weight:650; }
.source-error-list li + li { margin-top:7px; }
.source-error-name { display:block; color:var(--ink); font-weight:650; }
.source-error-message { overflow-wrap:anywhere; }
.notice-group,.news-feed { min-width:0; }
.notice-group { padding:13px 0 7px; border-top:1px solid var(--steel); }
.notice-group:first-of-type { border-top:2px solid var(--ink); }
.group-heading {
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:12px;
  margin:0 0 4px;
}
.group-heading h2 { margin:0; font-family:var(--display-font); font-size:1rem; }
.group-heading span { color:var(--muted); font-family:var(--data-font); font-size:.78rem; }
.notice-list,.news-list { display:grid; }
.notice-item,.news-item {
  position:relative;
  min-width:0;
  border-bottom:1px solid var(--steel);
  background:var(--surface);
}
.notice-item { display:grid; grid-template-columns:104px minmax(0,1fr) auto auto; align-items:center; gap:12px; padding:10px 8px; }
.news-item { display:grid; grid-template-columns:34px minmax(0,1fr) auto; align-items:start; gap:10px; padding:13px 8px; }
.notice-item.hidden,.news-item.hidden,.notice-group.hidden { display:none; }
.notice-item.is-new,.news-item.is-new { box-shadow:inset 3px 0 var(--cqu-crimson); }
.notice-item.is-favorite,.news-item.is-favorite { background:#fffbea; }
.notice-item.is-read .item-title,.news-item.is-read .news-title { color:#75808a; }
.item-date { color:var(--muted); font-family:var(--data-font); font-size:.78rem; white-space:nowrap; }
.item-link,.news-title { min-width:0; color:var(--ink); text-decoration:none; }
.item-title,.news-title { overflow-wrap:anywhere; font-weight:650; }
.item-link:hover .item-title,.news-title:hover { color:var(--academic-blue); text-decoration:underline; text-underline-offset:3px; }
.item-source,.news-meta { color:var(--muted); font-size:.74rem; }
.icon-button { width:34px; min-height:34px; display:grid; place-items:center; padding:0; color:var(--muted); border-color:transparent; background:transparent; }
.icon-button svg { fill:none; stroke:currentColor; stroke-width:1.8; }
.is-favorite .favorite-button { color:var(--warning); }
.is-favorite .favorite-button svg { fill:currentColor; }
.state-button { min-height:30px; padding:0 8px; color:var(--academic-blue); font-size:.75rem; white-space:nowrap; }
.news-main { min-width:0; }
.news-meta { display:flex; flex-wrap:wrap; gap:5px 10px; margin-bottom:3px; }
.news-title { display:block; font-family:var(--display-font); font-size:1rem; line-height:1.45; }
.news-summary { margin:4px 0 0; color:var(--muted); font-size:.84rem; }
.tag-row { display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }
.tag { padding:1px 6px; border:1px solid var(--steel); border-radius:4px; color:var(--muted); font-size:.7rem; }
.tag.hot { color:var(--cqu-crimson); border-color:#d7a7aa; }
.empty-results {
  display:none;
  padding:28px 16px;
  border-top:2px solid var(--ink);
  border-bottom:1px solid var(--steel);
  color:var(--muted);
  background:var(--surface);
  text-align:center;
}
.empty-results.show,.empty-results[data-empty="true"] { display:block; }
.empty-results strong { display:block; margin-bottom:4px; color:var(--ink); font-family:var(--display-font); font-size:1rem; }
.empty-actions { display:flex; justify-content:center; flex-wrap:wrap; gap:8px; margin-top:13px; }
.toast {
  position:fixed;
  left:50%;
  bottom:20px;
  z-index:100;
  max-width:min(460px,calc(100% - 28px));
  padding:9px 14px;
  border-radius:6px;
  color:#fff;
  background:var(--ink);
  opacity:0;
  pointer-events:none;
  transform:translate(-50%,8px);
  transition:opacity .16s,transform .16s;
}
.toast.show { opacity:1; transform:translate(-50%,0); }
.page-footer { padding:20px 0 2px; color:var(--muted); font-size:.74rem; text-align:center; }
@media (max-width:1120px) {
  body[data-page="news"] .control-band { grid-template-columns:1fr; }
  body[data-page="news"] .control-secondary { justify-content:flex-start; overflow-x:auto; }
  body[data-page="news"] .index-spine { position:relative; top:auto; }
}
@media (max-width:980px) {
  .workspace-header-inner { grid-template-columns:minmax(230px,1fr) auto; }
  .header-meta { display:none; }
  .control-band { grid-template-columns:1fr; }
  .control-secondary { justify-content:flex-start; overflow-x:auto; }
  .workspace-grid { grid-template-columns:180px minmax(0,1fr); gap:18px; }
  .index-spine { position:relative; top:auto; }
  .notice-item { grid-template-columns:86px minmax(0,1fr) auto; }
  .notice-item .state-button { grid-column:2; justify-self:start; }
}
@media (max-width:700px) {
  .workspace-header-inner,.workspace-main { width:min(100% - 24px,1380px); }
  .workspace-header-inner { min-height:64px; grid-template-columns:1fr; gap:8px; padding:9px 0; }
  .brand-lockup img { width:32px; height:32px; }
  .brand-copy h1 { font-size:1.08rem; }
  .brand-copy p { display:none; }
  .page-switch { width:100%; }
  .page-switch a { flex:1 1 50%; justify-content:center; min-height:34px; }
  .workspace-main { padding-top:8px; }
  .control-band { position:relative; top:auto; padding-top:0; }
  .control-primary { flex-wrap:wrap; }
  .search-field { flex-basis:100%; }
  .filter-select { flex:1 1 130px; min-width:0; }
  .control-secondary { width:100%; padding-bottom:2px; }
  body[data-page="notices"] .control-secondary { flex-wrap:wrap; overflow:visible; }
  body[data-page="notices"] #statusFilter { flex:1 0 100%; width:100%; overflow:visible; }
  body[data-page="notices"] #statusFilter .segment-button { flex:1 1 25%; padding-inline:4px; }
  .workspace-grid { grid-template-columns:1fr; gap:12px; padding-top:10px; }
  .index-spine { position:relative; top:auto; padding:0 0 9px; border-right:0; border-bottom:2px solid var(--steel); overflow:hidden; }
  .index-spine h2 { margin-bottom:5px; }
  .source-index { display:flex; gap:4px; overflow-x:auto; padding-bottom:2px; }
  .source-index-button { flex:0 0 145px; min-height:38px; padding:4px 7px 4px 10px; background:var(--surface); }
  .source-index-button::before { left:0; top:5px; bottom:5px; }
  .index-state { display:none; }
  .notice-item { grid-template-columns:72px minmax(0,1fr) 32px; gap:7px; padding:10px 5px; }
  .notice-item .state-button { grid-column:2; }
  .item-source { display:none; }
  .news-item { grid-template-columns:30px minmax(0,1fr); padding:11px 4px; }
  .news-item > .state-button { grid-column:2; justify-self:start; }
  .news-summary { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
}
@media (prefers-reduced-motion:reduce) {
  *,*::before,*::after { scroll-behavior:auto !important; transition-duration:.01ms !important; animation-duration:.01ms !important; animation-iteration-count:1 !important; }
}
"""


_ICON_PATHS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "refresh": '<path d="M20 12a8 8 0 0 1-14.9 4M4 12A8 8 0 0 1 18.9 8"/><path d="M20 4v4h-4M4 20v-4h4"/>',
    "star": '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9Z"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5Z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5Z"/>',
}


def icon(name: str, class_name: str = "") -> str:
    path = _ICON_PATHS[name]
    class_attr = f' class="{html.escape(class_name, quote=True)}"' if class_name else ""
    return (
        f'<svg{class_attr} aria-hidden="true" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-linecap="round" '
        f'stroke-linejoin="round">{path}</svg>'
    )


def render_header(
    *,
    active_page: str,
    title: str,
    subtitle: str,
    updated_at: str,
    total: int,
    unit: str,
    icon_file: str,
) -> str:
    notice_current = ' aria-current="page"' if active_page == "notices" else ""
    news_current = ' aria-current="page"' if active_page == "news" else ""
    return f"""
<header class="workspace-header">
  <div class="workspace-header-inner">
    <div class="brand-lockup">
      <img src="{html.escape(icon_file, quote=True)}" alt="" width="38" height="38">
      <div class="brand-copy">
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(subtitle)}</p>
      </div>
    </div>
    <nav class="page-switch" aria-label="页面切换">
      <a href="index.html" data-page-target="notices" data-service-port="8765"{notice_current}>校务通知</a>
      <a href="news.html" data-page-target="news" data-service-port="8766"{news_current}>国内新闻</a>
    </nav>
    <div class="header-meta"><strong>共 {total} {html.escape(unit)}</strong><span>更新于 {html.escape(updated_at)}</span></div>
  </div>
</header>"""


def render_errors(errors) -> str:
    if not errors:
        return ""
    rows = "".join(
        "<li>"
        f'<span class="source-error-name">{html.escape(str(error.get("source", "未知来源")))}</span>'
        f'<span class="source-error-message">{html.escape(str(error.get("message", "未知错误")))}</span>'
        "</li>"
        for error in errors
    )
    return (
        '<details class="source-errors" id="sourceErrors">'
        f"<summary>{len(errors)} 个来源暂时不可用</summary>"
        '<p class="source-error-heading">部分来源抓取失败</p>'
        f'<ul class="source-error-list">{rows}</ul>'
        "</details>"
    )


def render_empty(noun: str, *, initially_empty: bool = False) -> str:
    flag = ' data-empty="true"' if initially_empty else ""
    return f"""
<section class="empty-results" id="emptyResults"{flag} aria-live="polite">
  <strong>没有可显示的{html.escape(noun)}</strong>
  <span>当前搜索或筛选条件没有结果。</span>
  <div class="empty-actions">
    <button class="command-button" type="button" data-action="clear-filters">清空筛选</button>
    <button class="command-button primary" type="button" data-action="refresh">{icon('refresh')}重新刷新</button>
  </div>
</section>"""


COMMON_JS = r"""
(function () {
  'use strict';
  function configurePageLinks() {
    document.querySelectorAll('[data-page-target][data-service-port]').forEach(function(link) {
      if (location.protocol === 'file:') {
        link.href = link.dataset.pageTarget === 'notices' ? 'index.html' : 'news.html';
      } else {
        link.href = location.protocol + '//' + location.hostname + ':' + link.dataset.servicePort + '/';
      }
    });
  }
  function sourceFilter() { return document.getElementById('sourceFilter'); }
  function syncSourceIndex() {
    var select = sourceFilter();
    if (!select) return;
    document.querySelectorAll('[data-source-target]').forEach(function(button) {
      button.classList.toggle('active', button.dataset.sourceTarget === select.value);
      button.setAttribute('aria-pressed', button.dataset.sourceTarget === select.value ? 'true' : 'false');
    });
  }
  document.addEventListener('click', function(event) {
    var source = event.target.closest('[data-source-target]');
    if (source) {
      var select = sourceFilter();
      if (select) {
        select.value = source.dataset.sourceTarget;
        select.dispatchEvent(new Event('change', { bubbles:true }));
        syncSourceIndex();
      }
      return;
    }
    var action = event.target.closest('[data-action]');
    if (!action) return;
    if (action.dataset.action === 'clear-filters' && window.CquSearch) CquSearch.reset();
    if (action.dataset.action === 'refresh' && typeof window.doRefresh === 'function') window.doRefresh();
  });
  document.addEventListener('DOMContentLoaded', function() {
    configurePageLinks();
    syncSourceIndex();
    var select = sourceFilter();
    if (select) select.addEventListener('change', syncSourceIndex);
  });
  window.CquShell = { syncSourceIndex:syncSourceIndex };
})();
"""
