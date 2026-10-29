import cloudscraper, re, os, time
OUTPUT_FILE="kanald_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.kanald.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=25)
        return r.text
    except: return ""

# Senin verdigin ornek ID
# Haysiyet 8 = xbrmr92
# Bu ID'ler her bolum icin degisiyor, sayfadan cekecegiz

def get_dailymotion_m3u8(video_id):
    # video_id = xbrmr92 gibi
    # Dailymotion'dan fresh m3u8 al
    try:
        # 1. dailymotion api
        api_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        r = scraper.get(api_url, timeout=10)
        data = r.json()
        # qualities icinde m3u8 var
        qualities = data.get("qualities", {})
        # auto veya 720
        for q in ["720","480","1080","auto"]:
            if q in qualities:
                for item in qualities[q]:
                    if "url" in item and ".m3u8" in item["url"]:
                        return item["url"]
        # fallback - qualities dict direkt
        txt = r.text
        m = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', txt)
        if m:
            return m[0].replace("\\/","/")
    except Exception as e:
        print(f"dailymotion api hata: {e}")
    # 2. senin verdigin gibi cdndirector ile dene - direkt link
    return f"https://www.dailymotion.com/video/{video_id}"

def run():
    slugs=["haysiyet","inci-taneleri","uzak-sehir","annem-ankara"]
    entries=[]
    
    # Manuel test - senin verdigin ID
    print("=== MANUEL TEST - Senin verdigin link ===")
    print("xbrmr92 = Haysiyet 8. Bolum")
    # Bu linki direkt deneyelim
    test_m3u8 = "https://www.dailymotion.com/video/xbrmr92"
    entries.append({"dizi":"Haysiyet","bolum":"8. Bolum (Son Bolum)","url":test_m3u8})
    print(f"OK Haysiyet 8 -> {test_m3u8}")

    for slug in slugs:
        print(f"\n=== {slug.upper()} ===")
        html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
        if len(html)<1000:
            html=fetch(f"{BASE_URL}/diziler/{slug}")
        
        # Kanal D sayfasinda dailymotion ID ara - xbrmr92 gibi
        # Pattern: dailymotion.com/video/x....
        ids = re.findall(r'dailymotion\.com/video/([a-z0-9]+)', html)
        ids += re.findall(r'"videoId"\s*:\s*"([a-z0-9]+)"', html)
        ids += re.findall(r'x[a-z0-9]{6,8}', html) # xbrmr92 formati
        uniq_ids = list(dict.fromkeys(ids))[:8]
        print(f"  Bulunan Dailymotion ID: {uniq_ids}")

        # bolum linkleri
        links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
        uniq_links=list(dict.fromkeys(links))[:8]
        print(f"  Bulunan bolum link: {len(uniq_links)}")

        for link in uniq_links:
            full=BASE_URL+link if link.startswith("/") else link
            bhtml=fetch(full)
            # sayfada dailymotion ID bul
            vid = re.findall(r'dailymotion\.com/video/([a-z0-9]+)', bhtml)
            if not vid:
                vid = re.findall(r'/video/([a-z0-9]{7})', bhtml)
            if vid:
                video_id = vid[0]
                print(f"  ID bulundu: {video_id} icin {link}")
                # m3u8 degil, dailymotion linki olarak kaydet - IPTV playerlar anlar
                bm=re.search(r'(\d+)[-_]?bolum',link,re.I)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":f"https://www.dailymotion.com/video/{video_id}"})
            time.sleep(0.8)

    print(f"\n{OUTPUT_FILE} - {len(entries)} bolum")
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

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

if __name__=="__main__": run()
