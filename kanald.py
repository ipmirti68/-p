import os, re, time
M3U="kanald_playlist.m3u"
MIRTI="mirti68.m3u"
BASE="https://www.kanald.com.tr"
GROUP="KANALD Dizileri"

def get_m3u8(full_url):
    print(f" -> {full_url}")
    # YONTEM 1: yt-dlp (en garanti)
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(full_url, download=False)
            # en iyi m3u8'i bul
            best=None
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if "m3u8" in u and ("dailymotion" in u or "cdndirector" in u or "m3u8" in u):
                    best=u
                    break
            if best:
                print(f"   OK yt-dlp {best[:70]}...")
                return best
    except Exception as e:
        print(f"   yt-dlp hata {e}")

    # YONTEM 2: worker + embed
    try:
        import cloudscraper
        scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
        r1=scraper.get(full_url, timeout=15)
        m=re.search(r'itemprop="embedURL"[^>]+href="([^"]+)"', r1.text)
        if not m: m=re.search(r'<iframe[^>]+src="([^"]+dailymotion[^"]+)"', r1.text)
        if m:
            embed=m.group(1)
            if embed.startswith("//"): embed="https:"+embed
            r2=scraper.get(f"https://mak.sadecenjoy.workers.dev/?url={embed}", timeout=20)
            m2=re.search(r'(https://cdndirector\.dailymotion\.com/cdn/manifest/video/[^"\'\s]+\.m3u8\?sec=[^"\'\s]+)', r2.text)
            if not m2: m2=re.search(r'(https?://[^"\'\s]+\.m3u8[^\s"\'\s]+)', r2.text)
            if m2:
                url=m2.group(1).replace('\\/', '/').replace('&amp;','&')
                print(f"   OK worker {url[:70]}...")
                return url
    except Exception as e:
        print(f"   worker hata {e}")
    return None

# Daha 17 - son 3 bolum sabit URL (en garanti)
EPISODES=[
    ("22. Bolum Son Bolum", f"{BASE}/daha-17/bolum/22-bolum"),
    ("21. Bolum", f"{BASE}/daha-17/bolum/21-bolum"),
    ("20. Bolum", f"{BASE}/daha-17/bolum/20-bolum"),
]

entries=[]
for name,url in EPISODES:
    m3u8=get_m3u8(url)
    if m3u8:
        entries.append((name,m3u8))
    time.sleep(1)

print(f"\nToplam {len(entries)} bolum bulundu")

# senin verdigin linki de yedek olarak ekle, oynamazsa diye
if len(entries)==0:
    entries.append(("22. Bolum", "https://cdndirector.dailymotion.com/cdn/manifest/video/xbr6qi2.m3u8?sec=8ogxtYteeqQcdPOWTRVKenFeAn-jEadBHnQVPOu5qIRotfxBLIAUI2_S2TgrTy62AAeS7U4r0N68koszmjPFfHPb4xfuEUGGwG1Lf8KtnIEbuda"))

poster="https://kanald.mncdn.com/mnresize/1180/665/upload/diziler/daha-17/afis.jpg"
with open(M3U,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name,m3u8 in entries:
        f.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{GROUP}",TR: Daha 17 - {name}\n')
        f.write(f'#EXTVLCOPT:http-referrer={BASE}/\n')
        f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\n')
        f.write(f'{m3u8}\n\n')

# mirti68.m3u guncelle
if not os.path.exists(MIRTI): open(MIRTI,"w").write("#EXTM3U\n")
cont=open(MIRTI,"r",encoding="utf-8",errors="ignore").read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
new=["#EXTINF"+p for p in open(M3U,"r",encoding="utf-8",errors="ignore").read().split("#EXTINF")[1:] if "http" in p]
open(MIRTI,"w",encoding="utf-8").write(first+"\n"+"\n\n".join([b.strip() for b in old+new])+"\n")
print(f"{MIRTI} -> {len(new)} kayit")
