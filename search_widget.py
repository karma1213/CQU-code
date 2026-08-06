#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享搜索组件：cqu_crawler 与 news_crawler 共用。

职责：
1. 生成期把标题转成逐字拼音（data-py 属性），前端零依赖即可拼音搜索。
   - 优先使用 pypinyin（若已安装），带词组级多音字修正；
   - 未安装时回退到内置 pinyin_table（含常用词组修正表）。
2. 提供统一的前端搜索引擎 SEARCH_JS（多关键词 AND、拼音全拼/首字母、
   命中高亮、来源与日期匹配）与配套样式 SEARCH_CSS。

data-py 格式：每个字一个音节，空格分隔；多音字用 | 列出备选读音，
默认读音在前；非汉字字符若为 a-z0-9 则原样保留，否则记为 ~。
例：重庆大学2026 -> "chong|zhong qing da xue 2 0 2 6"
"""

import re

try:
    from pypinyin import pinyin as _pypinyin, Style as _Style

    _HAS_PYPINYIN = True
except Exception:  # pragma: no cover - 环境相关
    _HAS_PYPINYIN = False

from pinyin_table import TABLE as _TABLE, PHRASES as _PHRASES

_HAN_RE = re.compile(r"[㐀-鿿]")
_SAFE_RE = re.compile(r"[a-z0-9]")

_MAX_ALTS = 3
_PHRASE_MAX_LEN = max((len(p) for p in _PHRASES), default=2)


def _clean_syllable(s):
    s = (s or "").lower().replace("ü", "v").replace("u:", "v")
    return re.sub(r"[^a-z]", "", s)


def _fallback_syllables(chars):
    """内置表路径：先词组贪心匹配，再逐字查表。返回与 chars 对齐的列表。"""
    n = len(chars)
    out = [None] * n
    i = 0
    while i < n:
        matched = False
        if _HAN_RE.match(chars[i]):
            for size in range(min(_PHRASE_MAX_LEN, n - i), 1, -1):
                word = "".join(chars[i : i + size])
                if word in _PHRASES:
                    for k, syl in enumerate(_PHRASES[word]):
                        out[i + k] = [syl]
                    i += size
                    matched = True
                    break
        if matched:
            continue
        ch = chars[i]
        if ch in _TABLE:
            out[i] = list(_TABLE[ch])[:_MAX_ALTS]
        else:
            low = ch.lower()
            out[i] = [low if _SAFE_RE.fullmatch(low) else "~"]
        i += 1
    return out


def _pypinyin_syllables(chars):
    """pypinyin 路径。任何对齐异常都回退内置表，保证健壮。"""
    text = "".join(chars)
    try:
        rows = _pypinyin(
            text,
            style=_Style.NORMAL,
            heteronym=True,
            errors=lambda nohan: [[c] for c in nohan],
        )
        if len(rows) != len(chars):
            return _fallback_syllables(chars)
        out = []
        for ch, row in zip(chars, rows):
            if _HAN_RE.match(ch):
                seen, alts = set(), []
                for r in row:
                    syl = _clean_syllable(r)
                    if syl and syl not in seen:
                        seen.add(syl)
                        alts.append(syl)
                    if len(alts) >= _MAX_ALTS:
                        break
                out.append(alts or ["~"])
            else:
                low = ch.lower()
                out.append([low if _SAFE_RE.fullmatch(low) else "~"])
        return out
    except Exception:
        return _fallback_syllables(chars)


def syllables(text):
    """返回逐字拼音备选列表，与 text 的（按码点）字符一一对齐。"""
    chars = list(text)
    if _HAS_PYPINYIN:
        return _pypinyin_syllables(chars)
    return _fallback_syllables(chars)


def py_attr(text):
    """生成 data-py 属性值。只含 [a-z0-9|~ ]，无需额外转义。"""
    return " ".join("|".join(alts) for alts in syllables(text))


SEARCH_CSS = """
  mark.hl { background:rgba(255,205,84,.55); color:inherit; border-radius:3px; padding:0 1px; }
  .search-hint { font-size:.74rem; opacity:.72; margin-top:4px; }
"""

# 页面无关的搜索引擎。页面通过 CquSearch.install(cfg) 注入差异点：
#   cfg.items()            -> 条目元素数组
#   cfg.text(item)         -> 参与纯文本匹配的字符串（标题/来源/日期/摘要…）
#   cfg.pass(item)         -> 非关键词过滤（来源下拉、状态、分类…）
#   cfg.hl                 -> [{el(item), text(item), py:bool}] 高亮目标
#   cfg.after(n, q)        -> 计数行 / 空态 / 卡片分组等收尾
#   cfg.onReset()          -> “重置筛选”时恢复页面控件
SEARCH_JS = r"""
window.CquSearch = (function () {
  'use strict';
  var cfg = null;
  var inputEl = null;

  function norm(s) {
    return (s || '').toLowerCase().replace(/ü/g, 'v').replace(/\s+/g, ' ').trim();
  }
  function tokenize(q) {
    return norm(q).split(' ').filter(Boolean);
  }

  function pyKeys(attr, alignLen) {
    // attr -> [{full, init, offs|null}]；alignLen 不匹配时返回 []（放弃对齐高亮）
    if (!attr) return [];
    var parts = attr.split(' ');
    var aligned = alignLen === undefined || parts.length === alignLen;
    if (alignLen !== undefined && !aligned) return [];
    var sylls = parts.map(function (p) { return p.split('|'); });
    var keys = [];
    function addKey(overrideIndex, overrideValue) {
      var full = '', init = '', offs = alignLen === undefined ? null : [];
      for (var j = 0; j < sylls.length; j++) {
        var syl = j === overrideIndex ? sylls[j][overrideValue] : sylls[j][0];
        if (offs) for (var k = 0; k < syl.length; k++) offs.push(j);
        full += syl;
        init += syl.charAt(0);
      }
      keys.push({ full: full, init: init, offs: offs });
    }
    addKey(-1, 0);
    // 每个多音字分别建立备选索引，避免不同位置的备选读音被错误地绑定在一起。
    for (var i = 0; i < sylls.length && keys.length < 24; i++) {
      for (var v = 1; v < sylls[i].length && keys.length < 24; v++) addKey(i, v);
    }
    return keys;
  }

  function buildEntry(item) {
    var title = item.dataset.title || '';
    var chars = Array.from(title);
    var entry = { text: ' ' + norm(cfg.text(item)) + ' ', chars: chars, keys: [] };
    entry.keys = pyKeys(item.dataset.py || '', chars.length)
      .concat(pyKeys(item.dataset.spy || ''));
    return entry;
  }
  function entryOf(item) {
    if (!item._cqs) item._cqs = buildEntry(item);
    return item._cqs;
  }

  function tokenRanges(entry, tok) {
    // 返回 null=未命中；[]=命中但不在标题上（来源/日期等）；[[a,b),...]=标题命中范围
    var ranges = [];
    var found = false;
    var lowerTitle = entry.chars.join('').toLowerCase();
    var idx = lowerTitle.indexOf(tok);
    while (idx !== -1) {
      ranges.push([idx, idx + tok.length]);
      idx = lowerTitle.indexOf(tok, idx + 1);
    }
    for (var k = 0; k < entry.keys.length; k++) {
      var key = entry.keys[k];
      if (!key.offs) {
        if (key.full.indexOf(tok) !== -1 || key.init.indexOf(tok) !== -1) found = true;
        continue;
      }
      var p = key.full.indexOf(tok);
      while (p !== -1) {
        ranges.push([key.offs[p], key.offs[p + tok.length - 1] + 1]);
        p = key.full.indexOf(tok, p + 1);
      }
      p = key.init.indexOf(tok);
      while (p !== -1) {
        ranges.push([p, p + tok.length]);
        p = key.init.indexOf(tok, p + 1);
      }
    }
    if (ranges.length) return ranges;
    if (found || entry.text.indexOf(tok) !== -1) return [];
    return null;
  }

  function mergeRanges(ranges) {
    ranges.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    var out = [];
    for (var i = 0; i < ranges.length; i++) {
      var r = ranges[i];
      if (out.length && r[0] <= out[out.length - 1][1]) {
        if (r[1] > out[out.length - 1][1]) out[out.length - 1][1] = r[1];
      } else out.push([r[0], r[1]]);
    }
    return out;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function paintRanges(el, chars, ranges) {
    if (!el) return;
    if (!ranges.length) { el.textContent = chars.join(''); return; }
    var html = '', pos = 0;
    for (var i = 0; i < ranges.length; i++) {
      html += escapeHtml(chars.slice(pos, ranges[i][0]).join(''));
      html += '<mark class="hl">' + escapeHtml(chars.slice(ranges[i][0], ranges[i][1]).join('')) + '</mark>';
      pos = ranges[i][1];
    }
    html += escapeHtml(chars.slice(pos).join(''));
    el.innerHTML = html;
  }

  function plainRanges(text, tokens) {
    var lower = text.toLowerCase(), out = [];
    for (var t = 0; t < tokens.length; t++) {
      var idx = lower.indexOf(tokens[t]);
      while (idx !== -1) {
        out.push([idx, idx + tokens[t].length]);
        idx = lower.indexOf(tokens[t], idx + 1);
      }
    }
    return out;
  }

  function apply() {
    if (!cfg) return 0;
    var tokens = tokenize(inputEl ? inputEl.value : '');
    var visible = 0;
    var list = cfg.items();
    for (var i = 0; i < list.length; i++) {
      var item = list[i];
      var ok = cfg.pass ? cfg.pass(item) : true;
      var titleRanges = [];
      if (ok && tokens.length) {
        var entry = entryOf(item);
        for (var t = 0; t < tokens.length && ok; t++) {
          var r = tokenRanges(entry, tokens[t]);
          if (r === null) ok = false;
          else titleRanges = titleRanges.concat(r);
        }
      }
      item.classList.toggle('hidden', !ok);
      if (ok) visible++;
      for (var h = 0; h < (cfg.hl || []).length; h++) {
        var target = cfg.hl[h];
        var el = target.el(item);
        if (!el) continue;
        if (target.py) {
          paintRanges(el, entryOf(item).chars, ok && tokens.length ? mergeRanges(titleRanges) : []);
        } else {
          var text = target.text(item);
          var rr = ok && tokens.length ? mergeRanges(plainRanges(text, tokens)) : [];
          paintRanges(el, Array.from(text), rr);
        }
      }
    }
    if (cfg.after) cfg.after(visible, tokens.join(' '));
    return visible;
  }

  function reset() {
    if (inputEl) inputEl.value = '';
    if (cfg && cfg.onReset) cfg.onReset();
    apply();
    if (inputEl) inputEl.focus();
  }

  var timer = null;
  function debounced() {
    clearTimeout(timer);
    timer = setTimeout(apply, 120);
  }

  function install(options) {
    cfg = options;
    inputEl = document.querySelector(options.input || '#searchInput');
    if (inputEl) {
      inputEl.addEventListener('input', debounced);
      inputEl.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { inputEl.value = ''; apply(); }
      });
    }
    document.addEventListener('keydown', function (e) {
      if (e.key === '/' && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) {
        e.preventDefault();
        if (inputEl) inputEl.focus();
      }
    });
    return apply;
  }

  return { install: install, apply: apply, reset: reset, _norm: norm, _tokenize: tokenize };
})();
"""
