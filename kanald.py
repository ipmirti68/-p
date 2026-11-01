import cloudscraper, re, os, time
from bs4 import BeautifulSoup
OUTPUT_FILE="kanald_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.kanald.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(url):
    try:
        r=scraper.get(url, timeout=20)
        if len(r.text)>1000: return r.text
    except: return ""
    return ""

def ytdlp(url):
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u: return u
    except Exception as e: print(f"  yt-dlp hata {e}")
    return None

def get_links(slug):
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    if not html: html=fetch(f"{BASE_URL}/diziler/{slug}")
    soup=BeautifulSoup(html, "html.parser")
    out=set()
    for a in soup.find_all("a", href=True):
        h=a["href"]
        if slug in h and "bolum" in h.lower():
            if h.startswith("/"): h=BASE_URL+h
            out.add(h)
    return list(out)[:10]

slugs=["uzak-sehir","haysiyet","guller-ve-gunahlar","daha-17"]
entries=[]
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    links=get_links(slug)
    print(f"  {len(links)} bolum bulundu")
    for full in links:
        print(f"  -> {full}")
        m3u8=ytdlp(full)
        if m3u8:
            bm=re.search(r'(\d+)',full)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
            print(f"  OK {bname}")
        time.sleep(0.5)

with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n#EXTVLCOPT:http-referrer=https://www.kanald.com.tr/\n{e["url"]}\n\n')

if os.path.exists(MIRTI_FILE):
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p]
    with open(MIRTI_FILE,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
