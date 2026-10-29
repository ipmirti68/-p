import cloudscraper
from bs4 import BeautifulSoup
import json, time, re, os
from datetime import datetime

OUTPUT_FILE = "kanald_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
CACHE_FILE = "kanald_cache.json"
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
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_m3u8(scraper, bolum_url, cache):
    if bolum_url in cache.get("episodes", {}):
        return cache["episodes"][bolum_url]
    try:
        r1 = scraper.get(bolum_url, timeout=10)
        m = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        if m:
            embed = m.group(1)
            r2 = scraper.get(f"{WORKER_URL}/?url={embed}", timeout=15)
            f = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r2.text)
            if f:
                url = f.group(0).replace('\\/', '/')
                cache["episodes"][bolum_url] = url
                return url
        cache["episodes"][bolum_url] = bolum_url
        return bolum_url
    except:
        cache["episodes"][bolum_url] = bolum_url
        return bolum_url

def run_scraper():
    cache = load_cache()
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    entries = []
    for page in range(1, 3):  # 10 yerine 2 yaptim, hizli bitsin
        print(f"Sayfa {page}")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('a.poster-card')
            if not cards:
                break
            for card in cards:
                title = card.get('title') or 'Dizi'
                href = card.get('href')
                if not href:
                    continue
                full = BASE_URL + href if href.startswith('/') else href
                img = card.find('img')
                poster = (img.get('data-src') or img.get('src','')) if img else ''
                # bolumler sayfasi
                try:
                    r = scraper.get(full.rstrip('/') + "/bolumler", timeout=10)
                    s = BeautifulSoup(r.text, 'html.parser')
                    sel = s.find('select', id='video-finder-changer')
                    if sel:
                        for opt in sel.find_all('option', {'data-target': True}):
                            b_url = opt['data-target']
                            b_name = opt.get_text(strip=True)
                            m3u8 = get_m3u8(scraper, b_url, cache)
                            entries.append({'dizi': title, 'bolum': b_name, 'url': m3u8, 'poster': poster})
                except:
                    continue
        except:
            continue
    
    save_cache(cache)
    # m3u yaz
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 tvg-logo="{e["poster"]}" group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')
    
    # mirti68 e ekle - BOZMAYAN
    if os.path.exists(MIRTI_FILE) and os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as ff:
            k_blocks = []
            for p in ff.read().split("#EXTINF")[1:]:
                if "http" in p:
                    k_blocks.append("#EXTINF" + p.strip())
        with open(MIRTI_FILE, "r", encoding="utf-8", errors="ignore") as ff:
            cont = ff.read()
            first = cont.splitlines()[0] if cont else "#EXTM3U"
            old = []
            for p in cont.split("#EXTINF")[1:]:
                if "KANALD Dizileri" in p or 'group-title="Kanal D"' in p:
                    continue
                if "http" in p:
                    old.append("#EXTINF" + p.strip())
        with open(MIRTI_FILE, "w", encoding="utf-8") as out:
            out.write(first + "\n")
            for b in old:
                out.write(b + "\n\n")
            for b in k_blocks:
                out.write(b + "\n\n")
    print(f"Bitti {len(entries)} bolum")

if __name__ == "__main__":
    run_scraper()
