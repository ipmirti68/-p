#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DiziCaN Kore dizileri TEST M3U oluşturucu.
ÖNEMLİ: M3U'ya bölüm sayfası adreslerini yazar; bunlar doğrudan .m3u8 video akışı değildir.
Mevcut mirti68.m3u dosyasına dokunmaz.
"""
import re
import time
import html
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE = "https://dizican.cc"
CATEGORY = "https://dizican.cc/ulke/kore-dizileri-izle-hd/"
OUTPUT = "hanim_kore_test.m3u"
GROUP = "🩷◆ HANIM KORE DİZİLERİ ⭕"
MAX_CATEGORY_PAGES = 8
MAX_SHOWS = 250
DELAY = 0.6

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)

def get_soup(url):
    r = session.get(url, timeout=25)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return BeautifulSoup(r.text, "html.parser")

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

def abs_url(href, base):
    u = urljoin(base, href or "")
    p = urlparse(u)
    if p.scheme not in ("http", "https") or p.netloc.lower() not in ("dizican.cc", "www.dizican.cc"):
        return ""
    return u.split("#")[0]

def is_episode_anchor(a):
    text = clean(a.get_text(" ", strip=True)).lower()
    href = (a.get("href") or "").lower()
    return (
        ("bölüm" in text or "bolum" in text or re.search(r"\b\d+\s*[x.]\s*\d+\b", text))
        and bool(href)
    )

def get_show_links():
    found = {}
    for page in range(1, MAX_CATEGORY_PAGES + 1):
        url = CATEGORY if page == 1 else urljoin(CATEGORY, f"page/{page}/")
        print(f"[KATEGORİ] {page}: {url}")
        try:
            soup = get_soup(url)
        except Exception as e:
            print(f"[UYARI] Kategori okunamadı: {e}")
            break

        count_before = len(found)
        for a in soup.select("a[href]"):
            href = abs_url(a.get("href"), url)
            if not href or href.rstrip("/") == CATEGORY.rstrip("/"):
                continue
            path = urlparse(href).path.lower()
            # Dizi detay sayfaları genellikle /dizi/slug/ biçiminde.
            if "/dizi/" in path and not any(x in path for x in ("/bolum/", "/kategori/")):
                title = clean(a.get_text(" ", strip=True))
                if title and len(title) > 1:
                    found[href] = title
        if len(found) == count_before and page > 1:
            print("[BİLGİ] Yeni dizi bulunmadı; kategori taraması durdu.")
            break
        time.sleep(DELAY)
    return list(found.items())[:MAX_SHOWS]

def extract_show_info(show_url, fallback_title):
    soup = get_soup(show_url)
    title = clean((soup.select_one("h1") or soup.select_one("title")).get_text(" ", strip=True)) if (soup.select_one("h1") or soup.select_one("title")) else fallback_title
    title = re.sub(r"\s*[-|].*$", "", title).strip() or fallback_title

    poster = ""
    for sel in ("meta[property='og:image']", "meta[name='twitter:image']"):
        tag = soup.select_one(sel)
        if tag and tag.get("content"):
            poster = urljoin(show_url, tag["content"])
            break
    if not poster:
        img = soup.select_one("img")
        if img:
