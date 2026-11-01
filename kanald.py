import cloudscraper, re, os, json, time
from bs4 import BeautifulSoup

M3U="kanald_playlist.m3u"
MIRTI="mirti68.m3u"
BASE="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
GROUP="KANALD Dizileri"

# Senin istediğin 4 dizi - son bölüm sayıları
DIZILER={
    "daha-17": 22,
    "uzak-sehir": 32,
    "haysiyet": 8,
    "guller-ve-gunahlar": 10
}

def get_bolum_links(scraper, slug):
    """bolumler sayfasından gerçek linkleri al - 22-bolum 404 değil gerçek URL"""
    url=f"{BASE}/{slug}/bolumler"
    print(f"  {url}")
    try:
        r=scraper.get(url, timeout=20)
        soup=BeautifulSoup(r.text,'html.parser')
        links=[]
        seen=set()
        # select#video-finder-changer en garantisi
        sel=soup.find('select', id='video-finder-changer')
        if sel:
            for opt in sel.find_all('option'):
                t=opt.get('data-target') or opt.get('value')
                if not t: continue
                if t.startswith('/'): t=BASE+t
                if t in seen: continue
                seen.add(t)
                links.append(t)
        # yoksa tüm /bolum/ içeren a'lar
        if not links:
            for a in soup.find_all('a', href=True):
                href=a['href']
                if 'bolum' not in href.lower(): continue
                if 'fragman' in href.lower(): continue
                full=href if href.startswith('http') else BASE+href if href.startswith('/') else BASE+'/'+href
                if full in seen: continue
                seen.add(full)
                links.append(full)
        
        # en yeni 3 - sondan
        # link içinde numara var mı bak
        def num_from_link(l):
            m=re.search(r'(\d+)-bolum', l)
            return int(m.group(1)) if m else 0
        links=sorted(links, key=num_from_link, reverse=True)[:3]
        print(f"    {len(links)} link bulundu")
        return links
    except Exception as e:
        print(f"    hata {e}")
        return []

def get_m3u8(scraper, bolum_url):
    try:
        r1=scraper.get(bolum_url, timeout=15)
        # embedURL
        m=re.search(r'itemprop="embedURL"[^>]+href="([^"]+)"', r1.text)
        if not m: m=re.search(r'<iframe[^>]+src="([^"]+dailymotion[^"]+)"', r1.text)
        if not m:
            # direkt m3u8 var mı
            m2=re.search(r'(https://cdndirector\.dailymotion\.com[^\s"\'<>]+\.m3u8\?sec=[^"\'\s]+)', r1.text)
            if m2: return m2.group(1).replace('\\/', '/')
            return None
        embed=m.group(1)
        if embed.startswith('//'): embed='https:'+embed
        # worker
        r2=scraper.get(f"{WORKER}/?url={embed}", timeout=20)
        m2=re.search(r'(https://cdndirector\.dailymotion\.com[^\s"\'<>]+\.m3u8\?sec=[^"\'\s]+)', r2.text)
        if not m2: m2=re.search(r'(https?://[^"\'\s]+\.m3u8[^\s"\'\s]+)', r2.text)
        if m2:
            return m2.group(1).replace('\\/', '/').replace('&amp;','&')
    except Exception as e:
        print(f"      m3u8 hata {e}")
    return None

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
entries=[]

for slug,last in DIZILER.items():
    print(f"\n=== {slug} son {last} ===")
    links=get_bolum_links(scraper, slug)
    # fallback: elle kur
    if not links:
        for n in range(last, last-3, -1):
            links.append(f"{BASE}/{slug}/bolumler/{slug}-{n}-bolum")
    
    for link in links[:3]:
        print(f"  -> {link}")
        m3u8=get_m3u8(scraper, link)
        if m3u8:
            # numara çıkar
            mn=re.search(r'(\d+)-bolum', link)
            num=mn.group(1) if mn else "Son"
            entries.append((slug.replace('-',' ').title(), f"{num}. Bolum", m3u8))
            print(f"    OK {num}")
        else:
            print(f"    yok")
        time.sleep(0.5)

# Yaz - referrer ile oynar
poster_base="https://kanald.mncdn.com/mnresize/1180/665/upload/diziler"
with open(M3U,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for dizi,bolum,m3u8 in entries:
        f.write(f'#EXTINF:-1 tvg-logo="{poster_base}/{dizi.lower().replace(" ","-")}/afis.jpg" group-title="{GROUP}",{dizi} - {bolum}\n')
        f.write(f'#EXTVLCOPT:http-referrer={BASE}/\n')
        f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        f.write(f'{m3u8}\n\n')

print(f"\n{M3U} -> {len(entries)}")

# mirti68
if not os.path.exists(MIRTI): open(MIRTI,"w").write("#EXTM3U\n")
cont=open(MIRTI,"r",encoding="utf-8",errors="ignore").read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
new=["#EXTINF"+p for p in open(M3U,"r",encoding="utf-8",errors="ignore").read().split("#EXTINF")[1:] if "http" in p]
open(MIRTI,"w",encoding="utf-8").write(first+"\n"+"\n\n".join([b.strip() for b in old+new])+"\n")
print(f"{MIRTI} {len(new)} kayit")
