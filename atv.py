import cloudscraper, re, os, time
from bs4 import BeautifulSoup

OUTPUT_FILE="atv_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.atv.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.atv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        r=scraper.get(url, timeout=20)
        if len(r.text) > 2000: return r.text
    except Exception as e:
        print(f"  fetch hata: {e}")
    return ""

def extract_with_ytdlp(page_url):
    # bolumler sayfasini asla ytdlp'ye verme
    if "bolumler" in page_url.lower():
        return None
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(page_url, download=False)
            for f in info.get("formats", [])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u and "erbvr" in u:
                    return u
            if info.get("url") and ".m3u8" in info["url"]:
                return info["url"]
    except Exception as e:
        print(f"  yt-dlp hata {page_url} -> {e}")
    return None

def extract_atv_m3u8(html):
    html=html.replace("hxxps","https").replace("hxxp","http").replace("httxx","https")
    m=re.findall(r'https?://[^\s"\'\\]*erbvr\.com[^\s"\'\\]*\.m3u8[^\s"\'\\]*', html)
    if m: return m[0].replace("\\/","/").replace("\\u002F","/").strip()
    return None

entries=[]
slugs=[
    "alti-ustu-istanbul",
    "gunesin-dogdugu-yer",
    "abi",
    "ask-ve-taht",
    "mercan-kosk",
    "sevdam-bir-ates",
    "muhtemel-ask",
    "menekse",
    "kurulus-osman",
    "bir-gece-masali"
]

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    # DOGRU URL: /diziler/ + slug + /bolumler
    bolumler_url=f"{BASE_URL}/diziler/{slug}/bolumler"
    html=fetch(bolumler_url)
    if not html:
        html=fetch(f"{BASE_URL}/diziler/{slug}")
    soup=BeautifulSoup(html, "html.parser")
    links=set()
    for a in soup.find_all("a", href=True):
        href=a["href"].strip()
        if "bolumler" in href: continue  # bolumler linkini alma
        if "/bolum/" in href and slug in href.lower():
            if href.startswith("/"): href=BASE_URL+href
            links.add(href)
    # yedek regex
    for m in re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^\s"\'\\]+', html):
        if "bolumler" not in m:
            links.add(BASE_URL+m if m.startswith("/") else m)

    uniq=list(links)[:8]
    print(f"  {len(uniq)} bolum bulundu")
    if len(uniq)==0:
        # Güneşin Doğduğu Yer için senin attığın örnek
        if slug=="gunesin-dogdugu-yer":
            uniq=[f"{BASE_URL}/diziler/{slug}/bolum/7-bolum"]
            print(f"  örnek deneniyor: {uniq[0]}")
        else:
            continue

    for full in uniq:
        print(f"  -> {full}")
        m3u8=extract_with_ytdlp(full)
        if not m3u8:
            bhtml=fetch(full)
            m3u8=extract_atv_m3u8(bhtml)
        if m3u8:
            bm=re.search(r'(\d+)[^0-9]*bolum', full.lower())
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            dizi_adi=slug.replace("-"," ").title()
            entries.append({"dizi":dizi_adi,"bolum":bname,"url":m3u8})
            print(f"  OK {dizi_adi} {bname}")
        time.sleep(0.5)

print(f"\nToplam {len(entries)} bolum")
with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n#EXTVLCOPT:http-referrer=https://www.atv.com.tr/\n{e["url"]}\n\n')

if os.path.exists(MIRTI_FILE):
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "ATV Dizileri" not in p]
    with open(MIRTI_FILE,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
