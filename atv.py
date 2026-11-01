import cloudscraper, re, os, time
OUTPUT_FILE="atv_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.atv.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.atv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        r=scraper.get(url, timeout=20)
        print(f"  fetch {url} -> {len(r.text)} byte")
        if len(r.text) > 1000:
            return r.text
    except Exception as e:
        print(f"  fetch hata {url}: {e}")
    return ""

def extract_with_ytdlp(page_url):
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            for f in info.get("formats", [])[::-1]:
                u = f.get("url","")
                if ".m3u8" in u and ("erbvr" in u or "atv" in u):
                    print(f"  yt-dlp buldu: {u[:80]}...")
                    return u
            if info.get("url") and ".m3u8" in info["url"]:
                return info["url"]
    except Exception as e:
        print(f"  yt-dlp hata: {e}")
    return None

def extract_atv_m3u8(html):
    m=re.findall(r'https?://[^"\'\s]*erbvr\.com[^"\'\s]*\.m3u8[^"\'\s]*',html)
    if m: 
        return m[0].replace("\\/","/")
    m2=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',html)
    for u in m2:
        if "erbvr" in u or "atv" in u or "vms" in u:
            return u.replace("\\/","/")
    return None

entries=[]
MANUEL_ATV = "https://htxkbiqd.erbvr.com/vms/b/ed/37/bed370e4-9d69-4e43-9f14-a0f06d76deda/bed370e4-9d69-4e43-9f14-a0f06d76deda.smil/.m3u8?st=fCvXO6JJBqhmiQSqOCS1Bw&e=1793352335&sid=LfEBink3_EaHevhNMPf_Vg"
entries.append({"dizi":"Alti Ustu Istanbul","bolum":"18. Bolum","url":MANUEL_ATV})
print(f"MANUEL eklendi")

slugs=[
    "alti-ustu-istanbul",
    "gunesin-dogdugu-yer",
    "abi",
    "ask-ve-taht",
    "mercan-kosk",
    "kurulus-osman",
    "bir-gece-masali",
    "can-borcu",
    "karadut",
    "kor-nokta"
]

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:6]
    print(f"  {len(uniq)} link bulundu")
    if len(uniq)==0:
        # korumalıysa son bölümleri dene
        uniq=[f"/diziler/{slug}/bolum/{i}-bolum" for i in range(15,21)]
        print(f"  manuel denenecek: {uniq}")

    for link in uniq:
        if "18-bolum" in link and slug=="alti-ustu-istanbul": 
            continue
        full=BASE_URL+link
        print(f"  deniyor {full}")
        m3u8 = extract_with_ytdlp(full)
        if not m3u8:
            bhtml=fetch(full)
            m3u8=extract_atv_m3u8(bhtml)

        if m3u8:
            bm=re.search(r'(\d+)',link)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            dizi_adi = slug.replace("-"," ").title()
            if slug=="gunesin-dogdugu-yer": dizi_adi="Gunesin Dogdugu Yer"
            if slug=="abi": dizi_adi="A.B.I."
            if slug=="ask-ve-taht": dizi_adi="Ask Ve Taht"
            if slug=="mercan-kosk": dizi_adi="Mercan Kosk"
            entries.append({"dizi":dizi_adi,"bolum":bname,"url":m3u8})
            print(f"  OK {dizi_adi} {bname}")
        else:
            print(f"  BULAMADI {link}")
        time.sleep(0.8)

print(f"\nToplam {len(entries)} bölüm bulundu")

with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n')
        f.write(f'#EXTVLCOPT:http-referrer=https://www.atv.com.tr/\n')
        f.write(f'{e["url"]}\n\n')
print(f"{OUTPUT_FILE} yazıldı")

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
    print(f"{MIRTI_FILE} güncellendi")
