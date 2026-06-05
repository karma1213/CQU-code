#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests, re, json, os, sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

def analyze(name, url):
    print(f"\n{'='*60}")
    print(f"  {name}: {url}")
    print('='*60)
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8-sig'
        soup = BeautifulSoup(r.text, 'html.parser')

        # Dump all <li> contents
        lis = soup.find_all('li')
        print(f"  <li> count: {len(lis)}")
        for li in lis:
            a = li.find('a')
            if a and a.get_text(strip=True):
                href = a.get('href','')
                txt = a.get_text(strip=True)
                full = li.get_text(' ', strip=True)
                dates = re.findall(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', full)
                date = dates[0] if dates else ''
                print(f"    [{date}] {txt[:60]} | {href[:80]}")

        # Dump <div> with class containing "list" or "news"
        for div in soup.find_all('div', class_=re.compile(r'list|news|main|right', re.I)):
            cls = ' '.join(div.get('class', []))
            items = div.find_all('a', href=True)
            if len(items) >= 3:
                print(f"\n  DIV .{cls} has {len(items)} links:")
                for a in items[:5]:
                    txt = a.get_text(strip=True)
                    href = a.get('href','')
                    full = div.get_text(' ', strip=True)
                    dates = re.findall(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', full)
                    date = dates[0] if dates else ''
                    print(f"    [{date}] {txt[:60]} | {href[:80]}")
    except Exception as e:
        print(f"  ERROR: {e}")

analyze("重庆大学", "https://www.cqu.edu.cn/tzgg.htm")
analyze("学工部-学生管理", "https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1006")
analyze("学工部-思政教育", "https://xgb.cqu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1005")
analyze("研究生院", "https://graduate.cqu.edu.cn/tzgg.htm")
analyze("土木学院", "https://civil.cqu.edu.cn/xzwb/tzgg.htm")
