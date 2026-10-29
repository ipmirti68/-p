import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
from datetime import datetime

OUTPUT_DIR = "."
OUTPUT_FILE = "kanald_playlist.m3u"
CACHE_FILE = "kanald_cache.json"
MIRTI_FILE = "mirti68.m3u"  # ANA LISTE

BASE_URL = "https://www.kanald.com.tr"
ARCHIVE_URL = "https://www.kanald.com.tr/diziler/arsiv?page="
WORKER_URL = "https://mak.sadecenjoy.workers.dev"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"episodes": {}}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_real_m3u8(scraper, bolum_url, cache):
    if bolum_url in cache.get("episodes", {}):
        return cache["episodes"][bolum_url]
    try:
        r1 = scraper.get(bolum_url, timeout=10)
        embed_match = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        if not embed_match:
            for pattern in [r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', r'data-url=["\']([^"\']+\.m3u8[^"\']*)["\']']:
                m = re.search(pattern, r1.text)
                if m:
                    url = m.group(1).replace('\\/', '/')
                    cache.setdefault("episodes", {})[bolum_url] = url
                    return url
            cache.setdefault("episodes", {})[bolum_url] = bolum_url
            return bolum_url
        embed_url = embed_match.group(1)
        print(f"      🔗 Embed: {embed_url[:60]}...")
        worker_req_url = f"{WORKER_URL}/?url={embed_url}"
        r2 = scraper.get(worker_req_url, timeout=15)
        if r2.status_code == 200:
            m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r2.text)
            if m3u8_match:
                url = m3u8_match.group(0).replace('\\/', '/')
                cache.setdefault("episodes", {})[bolum_url] = url
                return url
        final_url = r2.url if r2.url != worker_req_url else embed_url
        cache.setdefault("episodes", {})[bolum_url] = final_url
        return final_url
    except Exception as e:
        print(f"      ⚠️ Worker hatası: {e}")
        cache.setdefault("episodes", {})[bolum_url] = bolum_url
        return bolum_url

def fetch_all_episodes(scraper, series_url):
    episodes = []
    bolum_url = series_url.rstrip('/') + "/bolumler"
    seen = set()
    try:
        def parse_page(url):
            r = scraper.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            select_box = soup.find('select', id='video-finder-changer')
            if select_box:
                for opt in select_box.find_all('option', {'data-target': True}):
                    name = opt.get_text(strip=True)
                    target = opt['data-target']
                    if target not in seen:
                        seen.add(target)
                        episodes.append({'name': name, 'url': target})
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '/bolum/' not in href:
                    continue
                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    title_tag = a.select_one('.title, h3, h2, .name, .caption')
                    if title_tag:
                        name = title_tag.get_text(strip=True)
                    else:
                        match = re.search(r'/(\d+)-bolum', href)
                        if match:
                            name = f"{match.group(1)}. Bölüm"
                if not name or len(name) < 2:
                    continue
                if href.startswith('/'):
                    full_url = BASE_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = bolum_url.rstrip('/') + '/' + href.lstrip('/')
                if full_url not in seen:
                    seen.add(full_url)
                    episodes.append({'name': name, 'url': full_url})
            pagination = soup.select('.pagination a, .page-numbers a, a[href*="/bolumler/"]')
            next_urls = []
            for p in pagination:
                phref = p.get('href', '')
                if phref and '/bolumler/' in phref and phref not in seen:
                    if phref.startswith('/'):
                        next_urls.append(BASE_URL + phref)
                    else:
                        next_urls.append(phref)
            return next_urls
        next_pages = parse_page(bolum_url)
        for next_url in next_pages[:5]:
            if next_url not in seen:
                seen.add(next_url)
                parse_page(next_url)
        def extract_num(ep):
            match = re.search(r'(\d+)', ep['name'])
            return int(match.group(1)) if match else 0
        episodes.sort(key=extract_num)
        print(f"      📑 {len(episodes)} bölüm bulundu")
        return episodes
    except Exception as e:
        print(f"      ⚠️ Bölüm hatası: {e}")
        return []

def append_to_mirti68():
    """kanald_playlist.m3u -> mirti68.m3u bozmayacak şekilde ekle"""
    if not os.path.exists(OUTPUT_FILE) or not os.path.exists(MIRTI_FILE):
        return
    with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        kanald_content = f.read()
    kanald_blocks = []
    for p in kanald_content.split("#EXTINF")[1:]:
        if "http" in p:
            # group-title'i mirti68 standardina cevir: KANALD Dizileri
            block = "#EXTINF" + p.strip()
            block = block.replace('group-title="Kanal D"', 'group-title="KANALD Dizileri"')
            kanald_blocks.append(block)

    print(f"KANALD Dizileri: {len(kanald_blocks)} bölüm")

    with open(MIRTI_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first_line = content.splitlines()[0] if content else "#EXTM3U"
        epg_header = first_line if "#EXTM3U" in first_line else "#EXTM3U"
        old_blocks = []
        for p in content.split("#EXTINF")[1:]:
            if "KANALD Dizileri" in p or 'group-title="Kanal D"' in p:
                continue
            if "http" in p:
                old_blocks.append("#EXTINF" + p.strip())

    with open(MIRTI_FILE, "w", encoding="utf-8") as out:
        out.write(epg_header + "\n")
        for b in old_blocks:
            out.write(b + "\n\n")
        for b in kanald_blocks:
            out.write(b + "\n\n")
    print(f"Bitti! Bozulmadı - {len(old_blocks)} eski + {len(kanald_blocks)} KANALD")

def run_scraper():
    print("🚀 Kanal D M3U (Worker Proxy)")
    print("=" * 60)
    cache = load_cache()
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    m3u_entries = []
    total_series = 0
    total_episodes = 0
    new_episodes = 0
    for page in range(1, 11):
        print(f"📄 Sayfa {page}/10")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards =
