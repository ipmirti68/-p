import cloudscraper, re, os, time
OUTPUT_FILE="atv_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.atv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.atv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    # once WORKER, olmazsa direkt
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

# Senin testlerin
slugs=["haysiyet","alti-ustu-istanbul","kurulus-osman","can-borcu"]

entries=[]
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    if len(html)<500:
        html=fetch(f"{BASE_URL}/diziler/{slug}")
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:8]
    print(f"  Bulunan bolum link: {len(uniq)}")
    if len(uniq)==0:
        uniq=[f"/diziler/{slug}/bolum/{i}-bolum" for i in range(1,9)]
        print(f"  Manuel liste kullaniliyor")
    for link in uniq[-5:]:
        full=BASE_URL+link
        bhtml=fetch(full)
        m3u8=None
        # duzeltildi - line 62 hatasi buradaydi
        m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',bhtml)
        if m:
            m3u8=m[0].replace("\\/","/")
        if not m3u8:
            m2=re.search(r'"videoUrl"\s*:\s*"([^"]+)"',bhtml)
            if m2 and "m3u8" in m2.group(1):
                m3u8=m2.group(1).replace("\\/","/")
        if m3u8 and ".m3u8" in m3u8:
            bm=re.search(r'(\d+)',link)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
            print(f"  OK {bname}")
        time.sleep(0.5)

print(f"\n{OUTPUT_FILE} - {len(entries)} bolum")
with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

if os.path.exists(MIRTI_FILE):
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read()
        first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "ATV Dizileri" not in p]
    with open(MIRTI_FILE,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
