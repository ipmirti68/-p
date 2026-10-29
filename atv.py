import cloudscraper, re, os, time

OUTPUT_FILE = "atv_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.atv.com.tr"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def fetch(url):
    try:
        r = scraper.get(url, timeout=20)
        return r.text
    except:
        return ""

def run():
    slugs = ["kurulus-osman","bir-gece-masali","sahipsizler","can-borcu","karadut","kor-nokta","kardeslerim"]
    entries=[]
    for slug in slugs:
        print(f"\n{slug} bolumleri aliniyor...")
        html = fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
        if len(html) < 1000:
            html = fetch(f"{BASE_URL}/diziler/{slug}")
        links = re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\']+', html)
        uniq = list(dict.fromkeys(links))[:12]
        print(f"  {len(uniq)} bolum linki")
        for link in uniq:
            full = BASE_URL + link if link.startswith("/") else link
            bhtml = fetch(full)
            # ATV m3u8 - en garanti 3 pattern
            m3u8 = None
            pats = [
                r'"videoUrl"\s*:\s*"([^"]+m3u8[^"]*)"',
                r'"src"\s*:\s*"([^"]+m3u8[^"]*)"',
                r'(https?://[^"\']+atv[^"\']*\.m3u8[^"\']*)',
                r'(https?://[^"\']+\.m3u8[^"\']*)'
            ]
            for pat in pats:
                m = re.search(pat, bhtml)
                if m:
                    m3u8 = m.group(1).replace("\\/","/").replace("\\u002F","/")
                    break
            if m3u8 and ".m3u8" in m3u8:
                bm=re.search(r'(\d+)[-_]?bolum', link, re.I)
                bname = f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
                print(f"    OK {bname}")
            time.sleep(0.7)

    print(f"\n{OUTPUT_FILE} - {len(entries)} bolum")
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
