import cloudscraper
from bs4 import BeautifulSoup
import re
import os
import time
import json
from datetime import datetime

OUTPUT_FILE = "atv_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
CACHE_FILE = "atv_cache.json"
BASE_URL = "https://www.atv.com.tr"
ARCHIVE_URL = "https://www.atv.com.tr/diziler"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

def create_scraper():
    return cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def get_series_list(scraper):
    print("📄 ATV diziler çekiliyor...")
    series = []
    try:
        r = scraper.get(ARCHIVE_URL, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        # atv kart yapısı
        cards = soup.select('a[href*="/diziler/"]')
        seen = set()
        for a in cards:
            href = a.get('href','')
            if '/diziler/' not in href or '/bolum' in href or href.count('/') > 3:
                continue
            if href in seen:
                continue
            # sadece dizi ana sayfası /diziler/dizi-adi
            if not re.match(r'^/diziler/[^/]+/?$', href):
                continue
            seen.add(href)
            title_tag = a.select_one('h3, h2, .title, img')
            title = ""
            if a.get('title'):
                title = a.get('title')
            elif title_tag and title_tag.get('alt'):
                title = title_tag.get('alt')
            else:
                title = href.split('/')[-2].replace('-',' ').title()
            
            img = a.find('img')
            poster = img.get('data-src') or img.get('src','') if img else ''
            full_url = BASE_URL + href if href.startswith('/') else href
            series.append({'name': title.strip(), 'url': full_url, 'poster': poster})
        print(f"  {len(series)} dizi bulundu")
    except Exception as e:
        print(f"Dizi listesi hatası: {e}")
    return series

def get_episodes(scraper, serie_url, cache):
    episodes = []
    bolum_url = serie_url.rstrip('/') + "/bolumler"
    try:
        r = scraper.get(bolum_url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1 - json data
        json_match = re.search(r'"episodes"\s*:\s*(\[.*?\])', r.text, re.DOTALL)
        if json_match:
            try:
                eps = json.loads(json_match.group(1))
                for ep in eps:
                    episodes.append({
                        'name': ep.get('title','').replace('-',' '),
                        'url': BASE_URL + ep.get('link',''),
                        'img': ep.get('image','')
                    })
            except:
                pass
        
        # 2 - html kartlar
        if not episodes:
            cards = soup.select('a[href*="/bolum/"]')
            for a in cards:
                href = a.get('href','')
                if '/bolum/' not in href:
                    continue
                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    m = re.search(r'/(\d+)-bolum', href)
                    name = f"{m.group(1)}. Bölüm" if m else "Bölüm"
                full = BASE_URL + href if href.startswith('/') else href
                img = a.find('img')
                poster = img.get('data-src') or img.get('src','') if img else ''
                episodes.append({'name': name, 'url': full, 'img': poster})
        
        episodes = list({e['url']: e for e in episodes}.values())
        print(f"      📑 {len(episodes)} bölüm")
        return episodes
    except Exception as e:
        print(f"      Bölüm hatası: {e}")
        return []

def get_m3u8(scraper, bolum_url, cache):
    if bolum_url in cache:
        return cache[bolum_url]
    try:
        time.sleep(0.3)
        r = scraper.get(bolum_url, timeout=15)
        # atv player data
        patterns = [
            r'"src"\s*:\s*"(https://[^"]+\.m3u8[^"]*)"',
            r"src:\s*'(https://[^']+\.m3u8[^']*)'",
            r'(https://[^"\'\s<>]+\.m3u8[^"\'\s<>]*)',
            r'data-url=["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'videoUrl["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
        ]
        for pat in patterns:
            m = re.search(pat, r.text)
            if m:
                url = m.group(1).replace('\\/','/').replace('\\u002F','/')
                cache[bolum_url] = url
                return url
    except Exception as e:
        print(f"      m3u8 hatası: {e}")
    cache[bolum_url] = ""
    return ""

def append_to_mirti68():
    if not os.path.exists(OUTPUT_FILE) or not os.path.exists(MIRTI_FILE):
        return
    with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        atv_content = f.read()
    atv_blocks = []
    for p in atv_content.split("#EXTINF")[1:]:
        if "http" in p:
            atv_blocks.append("#EXTINF" + p.strip())
    
    print(f"ATV Dizileri: {len(atv_blocks)} bölüm")
    
    with open(MIRTI_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first_line = content.splitlines()[0] if content else "#EXTM3U"
        epg_header = first_line if "#EXTM3U" in first_line else "#EXTM3U"
        old_blocks = []
        for p in content.split("#EXTINF")[1:]:
            if "ATV Dizileri" in p:
                continue
            if "http" in p:
                old_blocks.append("#EXTINF" + p.strip())
    
    with open(MIRTI_FILE, "w", encoding="utf-8") as out:
        out.write(epg_header + "\n")
        for b in old_blocks:
            out.write(b + "\n\n")
        for b in atv_blocks:
            out.write(b + "\n\n")
    print(f"Bitti! {len(old_blocks)} eski + {len(atv_blocks)} ATV")

def main():
    cache = load_cache()
    scraper = create_scraper()
    series = get_series_list(scraper)
    
    all_entries = []
    for idx, serie in enumerate(series, 1):
        print(f"[{idx}/{len(series)}] {serie['name']}")
        eps = get_episodes(scraper, serie['url'], cache)
        if not eps:
            continue
        for ep in eps:
            m3u8 = get_m3u8(scraper, ep['url'], cache)
            if m3u8:
                all_entries.append({
                    'dizi': serie['name'],
                    'bolum': ep['name'],
                    'logo': ep.get('img') or serie['poster'],
                    'url': m3u8
                })
        time.sleep(0.5)
    
    save_cache(cache)
    
    today = datetime.now().strftime("%d.%m.%Y")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# ATV Dizileri - {today} - {len(all_entries)} bolum\n\n")
        for e in all_entries:
            f.write(f'#EXTINF:-1 tvg-logo="{e["logo"]}" group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')
    
    print(f"✅ {OUTPUT_FILE} - {len(all_entries)} bölüm")
    append_to_mirti68()

if __name__ == "__main__":
    main()
