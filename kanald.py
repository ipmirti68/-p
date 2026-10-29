import cloudscraper, re, json, os, time

OUTPUT_FILE = "kanald_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.kanald.com.tr"
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
    for slug in ["inci-taneleri","uzak-sehir","annem-ankara","esref-ruya","piyasa","guller-ve-gunahlar","balon"]:
        series.append({"name":slug.replace("-"," ").title(),"url":f"{BASE_URL}/diziler/{slug}","slug":slug})
    print(f"KANALD {len(series)} dizi")

    entries=[]
    for s in series[:6]:
        print(f"\n{s['name']}")
        html = fetch(s["url"].rstrip("/")+"/bolumler")
        if not html:
            html = fetch(s["url"])
        # tum bolum linkleri
        links = re.findall(r'href=["\']([^"\']*/bolum/[^"\']+)["\']', html)
        links += re.findall(r'"/diziler/'+re.escape(s["slug"])+r'/([^"]*bolum[^"]*)"', html)
        uniq=[]
        for l in links:
            full = l if l.startswith("http") else BASE_URL + l if l.startswith("/") else BASE_URL + "/diziler/"+s["slug"]+"/"+l
            if full not in uniq:
                uniq.append(full)
        print(f"  -> {len(uniq)} link")
        for link in uniq[:12]:
            try:
                bhtml = fetch(link)
                m = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', bhtml)
                if not m:
                    m2=re.search(r'embedURL[^>]+href="([^"]+)"', bhtml)
                    if m2:
                        bhtml2=fetch(f"{WORKER}/?url={m2.group(1)}")
                        m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', bhtml2)
                if m:
                    url=m[0].replace("\\/","/")
                    bm=re.search(r'(\d+)-bolum', link)
                    bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                    entries.append({"dizi":s["name"],"bolum":bname,"url":url})
                    print(f"    OK {bname}")
                time.sleep(0.5)
            except: continue

    print(f"Bitti {len(entries)} bolum")
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

    if os.path.exists(MIRTI_FILE):
        with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff:
            k_blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0]
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p]
        with open(MIRTI_FILE,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in k_blocks: out.write(b+"\n\n")

if __name__=="__main__": run()
