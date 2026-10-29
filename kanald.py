import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup
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
        except: pass
    return {"episodes": {}}

def save_cache(c):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def get_m3u8(bolum_url, cache):
    if bolum_url in cache.get("episodes", {}):
        return cache["episodes"][bolum_url]
    try:
        r1 = scraper.get(bolum_url, timeout=10)
        # embed linki bul
        m = re.search(r'itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        if not m:
            m = re.search(r'(https?://[^"\']+\.m3u8[^"\']*)', r1.text)
            if m:
                url = m.group(1).replace('\\/','/')
                cache["episodes"][bolum_url]=url
                return url
            cache["episodes"][bolum_url]=bolum_url
            return bolum_url
        embed = m.group(1)
        r2 = scraper.get(f"{WORKER_URL}/?url={embed}", timeout=15)
        m2 = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r2.text)
        if m2:
            url = m2.group(0).replace('\\/','/')
            cache["episodes"][bolum_url]=url
            return url
        cache["episodes"][bolum_url]=embed
        return embed
    except:
        cache["episodes"][bolum_url]=bolum_url
        return bolum_url

def run():
    cache = load_cache()
    entries = []
    print("KANALD taraniyor...")
    for page in range(1, 4): # 3 sayfa yeter, hizli
        print(f"Sayfa {page}")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # YENI selector - 2 yontem
            cards = soup.select('a.poster-card')
            if not cards:
                cards = soup.find_all("a", href=re.compile(r"/diziler/"))
            if not cards:
                break
            for card in cards:
                href = card.get("href","")
                if "/diziler/" not in href or "/bolum" in href:
                    continue
                if href.count("/") > 4:
                    continue
                title = card.get("title") or card.get_text(strip=True) or href.split("/")[-2]
                title = title.replace("\n","").strip()[:60]
                if len(title) < 2 or "Bölüm" in title:
                    continue
                full = BASE_URL + href if href.startswith("/") else href
                poster = ""
                img = card.find("img")
                if img:
                    poster = img.get("data-src") or img.get("src","")

                # bolumler sayfasini al
                try:
                    r = scraper.get(full.rstrip("/") + "/bolumler", timeout=10)
                    # YENI - regex ile tum bolum linklerini bul
                    links = re.findall(r'href=["\']([^"\']+/bolum/[^"\']+)["\']', r.text)
                    # dropdown
                    opts = re.findall(r'data-target=["\']([^"\']+/bolum/[^"\']+)["\']', r.text)
                    links = list(set(links + opts))
                    
                    for b_link in links[:30]: # her diziden max 30 bolum, cok olmasin
                        b_full = BASE_URL + b_link if b_link.startswith("/") else b_link
                        b_name_match = re.search(r'/(\d+)-bolum', b_link)
                        b_name = f"{b_name_match.group(1)}. Bölüm" if b_name_match else "Bölüm"
                        m3u8 = get_m3u8(b_full, cache)
                        if m3u8:
                            entries.append({"dizi": title, "bolum": b_name, "url": m3u8, "poster": poster})
                    time.sleep(0.3)
                except Exception as e:
                    print(f"  hata {title}: {e}")
                    continue
        except Exception as e:
            print(f"Sayfa hata: {e}")
            continue

    save_cache(cache)
    print(f"Bitti {len(entries)} bolum")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 tvg-logo="{e["poster"]}" group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

    if os.path.exists(MIRTI_FILE) and os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as ff:
            k_blocks = ["#EXTINF" + p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(MIRTI_FILE, "r", encoding="utf-8", errors="ignore") as ff:
            cont = ff.read()
            first = cont.splitlines()[0] if cont else "#EXTM3U"
            old = ["#EXTINF" + p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p and 'group-title="Kanal D"' not in p]
        with open(MIRTI_FILE, "w", encoding="utf-8") as out:
            out.write(first + "\n")
            for b in old: out.write(b + "\n\n")
            for b in k_blocks: out.write(b + "\n\n")
        print(f"Mirti guncellendi: {len(old)} eski + {len(k_blocks)} KANALD")

if __name__ == "__main__":
    run()
