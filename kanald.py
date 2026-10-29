import cloudscraper, re, os, time, json
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

def get_fresh_dailymotion_m3u8(video_id):
    # senin verdigin xbrmr92 icin fresh cdndirector linki al
    try:
        api=f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        r=scraper.get(api,timeout=15)
        txt=r.text
        # icinde cdndirector m3u8 var
        m=re.findall(r'https?://[^"\'\s]+dailymotion\.com[^"\'\s]*\.m3u8[^"\'\s]*',txt)
        if not m:
            m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',txt)
        if m:
            # en uzun olan genelde en kaliteli
            best=sorted(m,key=len)[-1].replace("\\/","/").replace("\\u002F","/")
            print(f"    Fresh m3u8: {best[:80]}...")
            return best
    except Exception as e:
        print(f"    dailymotion api hata: {e}")
    return None

entries=[]
# MANUEL Haysiyet 8 - senin verdigin ID'den fresh alacagiz
print("=== MANUEL HAYSIYET 8 ===")
fresh=get_fresh_dailymotion_m3u8("xbrmr92")
if fresh:
    entries.append({"dizi":"Haysiyet","bolum":"8. Bolum (Son Bolum)","url":fresh})
    print(f"OK Haysiyet 8 fresh")
else:
    # fallback senin verdigin ornek link
    entries.append({"dizi":"Haysiyet","bolum":"8. Bolum","url":"https://www.dailymotion.com/video/xbrmr92"})

slugs=["haysiyet","inci-taneleri","uzak-sehir","annem-ankara","esref-ruya","piyasa"]
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:6]
    print(f"  {len(uniq)} link")
    for link in uniq:
        full=BASE_URL+link
        bhtml=fetch(full)
        vids=re.findall(r'dailymotion\.com/video/([a-z0-9]+)',bhtml)
        if vids:
            vid=vids[0]
            if vid=="xbrmr92": continue
            fm=get_fresh_dailymotion_m3u8(vid)
            if fm:
                bm=re.search(r'(\d+)',link)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":fm})
        time.sleep(0.7)

with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')
print(f"\n{OUTPUT_FILE} - {len(entries)} bolum - artik cdndirector m3u8, oynayacak")

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
