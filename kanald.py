import cloudscraper, re, json, os, time

OUTPUT_FILE = "kanald_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.kanald.com.tr"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
scraper.headers.update({"Referer": BASE_URL + "/", "User-Agent": "Mozilla/5.0"})

def fetch(url):
    try:
        r = scraper.get(url, timeout=20)
        return r.text
    except:
        return ""

def run():
    slugs = ["inci-taneleri","uzak-sehir","annem-ankara","esref-ruya","piyasa","guller-ve-gunahlar","balon"]
    entries=[]
    for slug in slugs:
        print(f"\n{slug.replace('-',' ').title()}")
        html = fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
        if not html or "bolum" not in html.lower():
            html = fetch(f"{BASE_URL}/diziler/{slug}")
        # KANALD - __NEXT_DATA__ icinden link bul
        links = re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\']+', html)
        # uniq
        uniq = list(dict.fromkeys(links))[:12]
        print(f"  -> {len(uniq)} link")
        for link in uniq:
            full = BASE_URL + link if link.startswith("/") else link
            bhtml = fetch(full)
            # KANALD m3u8 patternleri - 5 yontem
            m3u8 = None
            # 1. direkt m3u8
            m = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', bhtml)
            if m:
                m3u8 = m[0].replace("\\/","/")
            # 2. videoUrl
            if not m3u8:
                m2 = re.search(r'"videoUrl"\s*:\s*"([^"]+m3u8[^"]*)"', bhtml)
                if m2: m3u8 = m2.group(1).replace("\\/","/")
            # 3. embed
            if not m3u8:
                m3 = re.search(r'embedURL[^>]+href="([^"]+)"', bhtml)
                if m3:
                    emb = m3.group(1)
                    bhtml2 = fetch(emb)
                    m4 = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', bhtml2)
                    if m4: m3u8 = m4[0]
                    else: m3u8 = emb
            
            if m3u8 and ".m3u8" in m3u8:
                bm=re.search(r'(\d+)-bolum', link)
                bname = f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
                print(f"    OK {bname} -> {m3u8[:60]}")
            time.sleep(0.8)

    print(f"\nBitti {len(entries)} bolum")
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
        print(f"Mirti: {len(old)} eski + {len(k_blocks)} KANALD")

if __name__=="__main__": run()
