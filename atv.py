import cloudscraper, re, json, os, time

OUTPUT_FILE = "atv_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.atv.com.tr"
WORKER = "https://mak.sadecenjoy.workers.dev"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def fetch(url):
    try:
        r = scraper.get(url, timeout=10)
        if len(r.text)>1000:
            return r.text
    except: pass
    try:
        r = scraper.get(f"{WORKER}/?url={url}", timeout=20)
        return r.text
    except:
        return ""

def run():
    series=[]
    for slug in ["kurulus-osman","bir-gece-masali","sahipsizler","zoraki-misafir","can-borcu","karadut","kor-nokta","kardeslerim"]:
        series.append({"name":slug.replace("-"," ").title(),"url":f"{BASE_URL}/diziler/{slug}","slug":slug})
    print(f"ATV {len(series)} dizi")

    entries=[]
    for s in series:
        print(f"\n{s['name']} bolumleri aliniyor...")
        html = fetch(s["url"] + "/bolumler")
        if not html or "bolum" not in html.lower():
            html = fetch(s["url"])
        links = re.findall(r'href=["\']([^"\']*'+re.escape(s["slug"])+r'[^"\']*bolum[^"\']*)["\']', html)
        links += re.findall(r'"url"\s*:\s*"([^"]*bolum[^"]*)"', html)
        uniq=[]
        for l in links:
            full = l if l.startswith("http") else BASE_URL + l if l.startswith("/") else BASE_URL + "/" + l.lstrip("/")
            if full not in uniq and "bolum" in full:
                uniq.append(full)
        print(f"  {len(uniq)} bolum linki")
        for link in uniq[:10]:
            bhtml = fetch(link)
            m = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', bhtml)
            if m:
                url=m[0].replace("\\/","/")
                bm=re.search(r'(\d+)[\.-]bolum', link)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":s["name"],"bolum":bname,"url":url})
                print(f"    OK {bname}")
            time.sleep(0.6)

    print(f"{OUTPUT_FILE} - {len(entries)} bolum")
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

    if os.path.exists(MIRTI_FILE):
        with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff:
            blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0]
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "ATV Dizileri" not in p]
        with open(MIRTI_FILE,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")
        print(f"Bitti! {len(old)} eski + {len(blocks)} ATV")

if __name__=="__main__": run()
