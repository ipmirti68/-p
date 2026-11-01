import cloudscraper, re, os, time, json
from bs4 import BeautifulSoup

M3U="kanald_playlist.m3u"
MIRTI="mirti68.m3u"
BASE="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
GROUP="KANALD Dizileri"

WANTED=["uzak-sehir","haysiyet","guller-ve-gunahlar","daha-17"]

CACHE_FILE="kanald_cache.json"
def load_cache():
    if os.path.exists(CACHE_FILE):
        try: return json.load(open(CACHE_FILE,"r",encoding="utf-8"))
        except: pass
    return {}

def save_cache(c):
    try: json.dump(c, open(CACHE_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except: pass

def get_m3u8(scraper, bolum_url, cache):
    if bolum_url in cache: 
        print(f"    cache {bolum_url[-30:]}")
        return cache[bolum_url]
    try:
        r1=scraper.get(bolum_url, timeout=15)
        # 1. embedURL bul
        m1=re.search(r'itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        if not m1:
            m1=re.search(r'<iframe[^>]+src=["\']([^"\']+dailymotion[^"\']+)["\']', r1.text)
        if not m1:
            print(f"    embed yok {bolum_url}")
            return None
        embed=m1.group(1)
        if embed.startswith("//"): embed="https:"+embed
        print(f"    embed {embed[:50]}...")
        # 2. worker ile al
        wr=f"{WORKER}/?url={embed}"
        r2=scraper.get(wr, timeout=20)
        txt=r2.text
        # 3. m3u8 ara
        m2=re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', txt)
        if m2:
            url=m2.group(1).replace('\\/', '/').replace('\\u002F','/').replace('&amp;','&')
            # bazen json içinde kaçışlı
            url=re.sub(r'\\', '', url)
            cache[bolum_url]=url
            save_cache(cache)
            return url
        print(f"    m3u8 yok worker'da")
        return None
    except Exception as e:
        print(f"    hata {e}")
        return None

def get_bolumler(scraper, dizi_url):
    url=dizi_url.rstrip('/')+"/bolumler"
    print(f"  bolumler sayfasi {url}")
    try:
        r=scraper.get(url, timeout=15)
        soup=BeautifulSoup(r.text,'html.parser')
        eps=[]
        seen=set()
        # YONTEM 1: select#video-finder-changer
        sel=soup.find('select', id='video-finder-changer')
        if sel:
            for opt in sel.find_all('option', {'data-target':True}):
                t=opt['data-target']
                name=opt.get_text(strip=True)
                if t and t not in seen:
                    seen.add(t)
                    full=t if t.startswith('http') else BASE+t
                    eps.append({'name':name,'url':full})
        # YONTEM 2: tum /bolum/ linkleri
        if not eps:
            for a in soup.find_all('a', href=True):
                href=a.get('href','')
                if '/bolum/' not in href: continue
                if 'fragman' in href or 'galeri' in href: continue
                full=href if href.startswith('http') else BASE+href if href.startswith('/') else url+'/'+href
                if full in seen: continue
                seen.add(full)
                name=a.get_text(strip=True)
                if len(name)<2:
                    mt=re.search(r'(\d+)[\.\-\s]*bölüm', full, re.I)
                    name=f"{mt.group(1)}. Bölüm" if mt else "Bölüm"
                eps.append({'name':name,'url':full})
        # sirala son 3
        def nmb(e):
            m=re.search(r'(\d+)', e['name'])
            return int(m.group(1)) if m else 0
        eps=sorted(eps, key=nmb, reverse=True)[:3]
        print(f"    {len(eps)} bolum secildi")
        return eps
    except Exception as e:
        print(f"    bolumler hata {e}")
        return []

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
cache=load_cache()
entries=[]
print(f"🚀 {GROUP}")

for slug in WANTED:
    dizi_url=f"{BASE}/diziler/{slug}"
    print(f"\n=== {slug} ===")
    bolumler=get_bolumler(scraper, dizi_url)
    for ep in bolumler:
        print(f"  -> {ep['name']} {ep['url'][-40:]}")
        m3u8=get_m3u8(scraper, ep['url'], cache)
        if m3u8:
            entries.append({'dizi':slug.replace('-',' ').title(),'bolum':ep['name'],'url':m3u8})
            print(f"    OK")
        else:
            print(f"    yok")
        time.sleep(0.4)

# YAZ
with open(M3U,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="{GROUP}",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

print(f"\n{M3U} -> {len(entries)}")

# mirti68
if not os.path.exists(MIRTI): open(MIRTI,"w").write("#EXTM3U\n")
with open(MIRTI,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(M3U,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(MIRTI,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")
print(f"{MIRTI} {len(new)} kayit eklendi")
