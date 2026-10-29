import cloudscraper, re, os, time
OUTPUT_FILE="kanald_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=20)
        if len(r.text)>1000:
            return r.text
    except: pass
    try:
        r=scraper.get(url,timeout=15)
        return r.text
    except:
        return ""

entries=[]
# SENIN VERDIGIN KESIN LINK - Haysiyet 8
entries.append({"dizi":"Haysiyet","bolum":"8. Bolum (Son Bolum)","url":"https://www.dailymotion.com/video/xbrmr92"})
print("MANUEL Haysiyet 8 eklendi: xbrmr92")

# Sevdan Bir Ates 8 - Show icin de buraya ekle
# entries.append({"dizi":"Sevdan Bir Ates","bolum":"8. Bolum","url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793317167&st=9f56173e468ce41d4a9e21d474c60eb9"})

slugs=["haysiyet","inci-taneleri","uzak-sehir","annem-ankara"]
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:8]
    print(f"  Bulunan bolum link: {len(uniq)}")
    for link in uniq:
        full=BASE_URL+link
        bhtml=fetch(full)
        vid=re.findall(r'dailymotion\.com/video/([a-z0-9]+)',bhtml)
        if vid:
            video_id=vid[0]
            if video_id!="xbrmr92": # manuel olani tekrar ekleme
                bm=re.search(r'(\d+)',link)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":f"https://www.dailymotion.com/video/{video_id}"})
                print(f"  OK {bname} - {video_id}")
        time.sleep(0.5)

with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

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
    print(f"Bitti! {len(old)} eski + {len(blocks)} KANALD")
