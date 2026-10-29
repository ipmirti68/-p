import cloudscraper, re, os, time
OUTPUT_FILE="atv_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.atv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=20)
        return r.text
    except: return ""
def run():
    slugs=["kurulus-osman","bir-gece-masali","sahipsizler","can-borcu","karadut","kor-nokta"]
    entries=[]
    for slug in slugs:
        print(f"\n{slug} bolumleri aliniyor...")
        html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
        if len(html)<500: html=fetch(f"{BASE_URL}/diziler/{slug}")
        links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\']+',html)
        uniq=list(dict.fromkeys(links))[:10]
        print(f"  {len(uniq)} bolum linki")
        for link in uniq:
            full=BASE_URL+link
            bhtml=fetch(full)
            m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',bhtml)
            if not m:
                m=re.findall(r'"videoUrl"\s*:\s*"([^"]+m3u8[^"]*)"',bhtml)
            if m:
                url=m[0].replace("\\/","/")
                bm=re.search(r'(\d+)[-_]?bolum',link,re.I)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":slug.title(),"bolum":bname,"url":url})
                print(f"    OK {bname}")
            time.sleep(0.6)
    print(f"\n{OUTPUT_FILE} - {len(entries)} bolum")
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries: f.write(f'#EXTINF:-1 group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')
    if os.path.exists(MIRTI_FILE):
        with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read(); first=cont.splitlines()[0]; old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "ATV Dizileri" not in p]
        with open(MIRTI_FILE,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")
if __name__=="__main__": run()
