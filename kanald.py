import cloudscraper, re, os, time, json
from bs4 import BeautifulSoup
from datetime import datetime

OUTPUT_FILE = "kanald_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.kanald.com.tr"
WORKER_URL = "https://mak.sadecenjoy.workers.dev"

WANTED = {
    "uzak-sehir": "Uzak Şehir",
    "haysiyet": "Haysiyet",
    "guller-ve-gunahlar": "Güller ve Günahlar",
    "daha-17": "Daha 17"
}

def get_real_m3u8(scraper, bolum_url):
    try:
        r1 = scraper.get(bolum_url, timeout=10)
        embed_match = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        if not embed_match:
            m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', r1.text)
            if m: return m.group(1).replace('\\/', '/')
            return None
        embed_url = embed_match.group(1)
        worker_req_url = f"{WORKER_URL}/?url={embed_url}"
        r2 = scraper.get(worker_req_url, timeout=15)
        if r2.status_code == 200:
            m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r2.text)
            if m3u8_match: return m3u8_match.group(0).replace('\\/', '/')
        return r2.url if r2.url != worker_req_url else embed_url
    except: return None

def fetch_episodes(scraper, series_url):
    episodes = []
    seen = set()
    try:
        r = scraper.get(series_url.rstrip('/') + "/bolumler", timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a.get('href','')
            if '/bolum/' not in href: continue
            if href.startswith('/'): full = BASE_URL + href
            else: full = href
            if full in seen: continue
            seen.add(full)
            name = a.get_text(strip=True) or f"{len(episodes)+1}. Bölüm"
            if len(name) < 3: continue
            episodes.append({'name': name, 'url': full})
        # numara ile sırala son 3
        def num(ep):
            m = re.search(r'(\d+)', ep['name'])
            return int(m.group(1)) if m else 0
        episodes = sorted(episodes, key=num, reverse=True)[:3]
        return episodes
    except Exception as e:
        print(f"  hata {e}")
        return []

scraper = cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
entries = []
print("🚀 【entity-Kanal D¦canonical_name=Kanal D】 - KANALD Dizileri")

for slug, title in WANTED.items():
    url = f"{BASE_URL}/diziler/{slug}"
    print(f"\n=== {title} ===")
    eps = fetch_episodes(scraper, url)
    print(f"  {len(eps)} bolum bulundu")
    for ep in eps:
        m3u8 = get_real_m3u8(scraper, ep['url'])
        if m3u8:
            entries.append({'dizi': title, 'bolum': ep['name'], 'url': m3u8})
            print(f"  OK {ep['name']}")

# yaz
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

print(f"\n{OUTPUT_FILE} -> {len(entries)} bolum")

if not os.path.exists(MIRTI_FILE): open(MIRTI_FILE,"w").write("#EXTM3U\n")
with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p]
with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(MIRTI_FILE,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")
print(f"mirti68.m3u guncellendi {len(new)} kayit")
