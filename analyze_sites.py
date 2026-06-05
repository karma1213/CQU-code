#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import re

urls = [
    ('cqu_tzgg', '重庆大学通知公告', 'https://www.cqu.edu.cn/tzgg.htm'),
    ('xgb_xsgl', '学工部-学生管理', 'https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1006'),
    ('xgb_sizheng', '学工部-思政教育', 'https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1005'),
    ('graduate', '研究生院通知公告', 'https://graduate.cqu.edu.cn/tzgg.htm'),
    ('civil', '土木学院通知公告', 'https://civil.cqu.edu.cn/xzwb/tzgg.htm'),
]

for key, label, url in urls:
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8-sig'
        soup = BeautifulSoup(r.text, 'html.parser')
        print(f'===== {label} ({key}) ===== status={r.status_code}')

        # Look for list items
        for li in soup.find_all('li'):
            a = li.find('a', href=True) if li else None
            if not a:
                continue
            text = a.get_text(strip=True)
            if len(text) < 6:
                continue
            href = a.get('href', '')
            # Find date - look for span, font, or text node with date pattern
            date_str = ''
            for span in li.find_all(['span', 'font', 'em', 'small']):
                t = span.get_text(strip=True)
                if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', t):
                    date_str = t
                    break
            if not date_str:
                # Try text nodes
                full = li.get_text(strip=True)
                m = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', full)
                if m:
                    date_str = m.group(1)
            print(f'  [{date_str}] {text[:80]} -> {href[:100]}')

        # Also look for div.list or similar structures
        for div in soup.find_all('div', class_=re.compile(r'list|news|item|content')):
            for a in div.find_all('a', href=True):
                text = a.get_text(strip=True)
                if len(text) >= 6:
                    date_str = ''
                    parent = a.parent
                    full = parent.get_text(strip=True) if parent else ''
                    m = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', full)
                    if m:
                        date_str = m.group(1)
                    print(f'  [{date_str}] (div) {text[:80]} -> {a["href"][:100]}')
        print()
    except Exception as e:
        print(f'===== {label} ({key}) ===== ERROR: {e}')
        print()
