import cloudscraper, re, os, json
from bs4 import BeautifulSoup

M3U="kanald_playlist.m3u"
MIRTI="mirti68.m3u"
BASE="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
GROUP="KANALD Dizileri"

CACHE="kanald_cache.json"
def load_cache():
    try: return json.load(open(CACHE,"r",encoding="utf-8"))
    except: return {}

def save_cache(c):
    try: json.dump(c, open(CACHE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except: pass

def get_fresh_m3u8(scraper, bolum_url, cache):
    # cache varsa kullanma, sec ölüyor, her seferinde taze al
    try:
        r1=scraper.get(bolum_url, timeout=15)
        # embedURL -> dailymotion
        m=re.search(r'itemprop="embedURL"[^>]+href="([^"]+)"', r1.text)
        if not m:
            m=re.search(r'<iframe[^>]+src="([^"]+dailymotion[^"]+)"', r1.text)
        if not m: return None
        embed=m.group(1)
        if embed.startswith("//"): embed="https:"+embed
        # worker ile taze sec al
        r2=scraper.get(f"{WORKER}/?url={embed}", timeout=20)
        # içinden cdndirector...m3u8?sec=... bul
        m2=re.search(r'(https://cdndirector\.dailymotion\.com/cdn/manifest/video/[^"\'\s]+\.m3u8\?sec=[^"\'\s]+)', r2.text)
        if not m2:
            m2=re.search(r'(https?://[^"\'\s]+\.m3u8[^\s"\'\s]+)', r2.text)
        if m2:
            url=m2.group(1).replace('\\/', '/').replace('&amp;','&')
            return url
    except Exception as e:
        print(f"  hata {bolum_url[-30:]} {e}")
    return None

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
print("Daha 17 son 3 bolum cekiliyor...")

# Daha 17 bolumler sayfasi
url=f"{BASE}/daha-17/bolumler"
r=scraper.get(url, timeout=15)
soup=BeautifulSoup(r.text,'html.parser')

eps=[]
for a in soup.find_all('a', href=True):
    href=a.get('href','')
    if '/daha-17/' in href and 'bolum' in href:
        full=href if href.startswith('http') else BASE+href
        name=a.get_text(strip=True)
        if 'Bölüm' in name or 'bolum' in href.lower():
            if full not in [e['url'] for e in eps]:
                eps.append({'name':name or href.split('/')[-1], 'url':full})

# en yeni 3 - 22,21,20
def num(e):
    m=re.search(r'(\d+)', e['name'])
    return int(m.group(1)) if m else 0
eps=sorted(eps, key=num, reverse=True)[:3]

print(f"Bulunan: {eps}")

entries=[]
for ep in eps:
    print(f" -> {ep['name']} {ep['url']}")
    m3u8=get_fresh_m3u8(scraper, ep['url'], {})
    if m3u8:
        print(f"   OK {m3u8[:80]}...")
        entries.append((ep['name'], m3u8))
    else:
        print("   yok")

# senin verdigin linki de ekle, en garanti
entries.append(("22. Bolum Son Bolum", "https://cdndirector.dailymotion.com/cdn/manifest/video/xbr6qi2.m3u8?sec=8ogxtYteeqQcdPOWTRVKenFeAn-jEadBHnQVPOu5qIRotfxBLIAUI2_S2TgrTy62AAeS7U4r0N68koszmjPFfHPb4xfuEUGGwG1Lf8KtnIEbuda"))

# M3U yaz
poster="https://kanald.mncdn.com/mnresize/1180/665/upload/diziler/daha-17/afis.jpg"
with open(M3U,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name,url in entries:
        f.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{GROUP}",TR: Daha 17 - {name}\n{url}\n\n')

print(f"{M3U} -> {len(entries)} bolum")

# mirti68.m3u
if not os.path.exists(MIRTI): open(MIRTI,"w").write("#EXTM3U\n")
cont=open(MIRTI,"r",encoding="utf-8",errors="ignore").read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
new=["#EXTINF"+p for p in open(M3U,"r",encoding="utf-8",errors="ignore").read().split("#EXTINF")[1:] if "http" in p]
open(MIRTI,"w",encoding="utf-8").write(first+"\n"+"\n\n".join([b.strip() for b in old+new])+"\n")
print(f"{MIRTI} guncellendi")
