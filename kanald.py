import cloudscraper, re, os, time
OUTPUT_FILE="kanald_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.kanald.com.tr/"})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=25)
        if len(r.text)>1000: return r.text
    except: pass
    try:
        r=scraper.get(url,timeout=15)
        return r.text
    except: return ""

def get_fresh_with_ytdlp(page_url):
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            for f in info.get("formats", [])[::-1]:
                u = f.get("url","")
                if ".m3u8" in u:
                    return u
    except Exception as e:
        print(f"    yt-dlp hata: {e}")
    return None

def get_fresh_dailymotion_m3u8(video_id):
    try:
        api=f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        r=scraper.get(api,timeout=15)
        txt=r.text
        m=re.findall(r'https?://[^"\'\s]+dailymotion\.com[^"\'\s]*\.m3u8[^"\'\s]*',txt)
        if not m:
            m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',txt)
        if m:
            return sorted(m,key=len)[-1].replace("\\/","/").replace("\\u002F","/")
    except: pass
    return None

entries=[]
print("=== MANUEL HAYSIYET 8 ===")
fresh=get_fresh_dailymotion_m3u8("xbrmr92")
if fresh:
    entries.append({"dizi":"Haysiyet","bolum":"8. Bolum","url":fresh})

# KANAL D GÜNCEL 4 DİZİ - FOTOĞRAFTAKİ LİSTE
slugs=[
    "uzak-sehir",
    "haysiyet",
    "guller-ve-gunahlar",
    "daha-17"
]

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:10]
    print(f"  {len(uniq)} link")
    for link in uniq:
        if "xbrmr92" in link: continue
        full=BASE_URL+link
        m3u8 = get_fresh_with_ytdlp(full)
        if not m3u8:
            bhtml=fetch(full)
            vids=re.findall(r'dailymotion\.com/video/([a-z0-9]+)',bhtml)
            if vids:
                m3u8=get_fresh_dailymotion_m3u8(vids[0])
        if m3u8:
            bm=re.search(r'(\d+)',link)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            dizi_adi = slug.replace("-"," ").title()
            if slug=="uzak-sehir": dizi_adi="Uzak Sehir"
            if slug=="guller-ve-gunahlar": dizi_adi="Guller Ve Gunahlar"
            if slug=="daha-17": dizi_adi="Daha 17"
            entries.append({"dizi":dizi_adi,"bolum":bname,"url":m3u8})
            print(f"  OK {dizi_adi} {bname}")
        time.sleep(0.6)

with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n')
        f.write(f'#EXTVLCOPT:http-referrer=https://www.kanald.com.tr/\n')
        f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        f.write(f'{e["url"]}\n\n')
print(f"\n{OUTPUT_FILE} - {len(entries)} bolum")

if os.path.exists(MIRTI_FILE):
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p]
    with open(MIRTI_FILE,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
