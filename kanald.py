import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup

OUTPUT_FILE = "kanald_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.kanald.com.tr"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def get_series():
    series=[]
    try:
        for page in range(1,4):
            r = scraper.get(f"{BASE_URL}/diziler/arsiv?page={page}", timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all("a", href=True):
                href=a["href"]
                if "/diziler/" not in href or "/bolum" in href: continue
                if href.count("/")>3: continue
                slug=href.split("/diziler/")[-1].split("/")[0]
                if not slug or len(slug)<2: continue
                full = BASE_URL + href if href.startswith("/") else href
                if full not in [s["url"] for s in series]:
                    title=a.get("title") or slug.replace("-"," ").title()
                    series.append({"name":title,"url":full,"slug":slug})
    except: pass
    if len(series)<3:
        for slug in ["inci-taneleri","uzak-sehir","annem-ankara","esref-ruya","piyasa"]:
            full=f"{BASE_URL}/diziler/{slug}"
            if full not in [s["url"] for s in series]:
                series.append({"name":slug.replace("-"," ").title(),"url":full,"slug":slug})
    print(f"KANALD {len(series)} dizi")
    return series

def get_episodes(serie):
    eps=[]
    try:
        # bolumler sayfasi
        r = scraper.get(serie["url"].rstrip("/")+"/bolumler", timeout=15)
        html=r.text
        # 1. __NEXT_DATA__ icinden
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data=json.loads(m.group(1))
                txt=json.dumps(data)
                links=re.findall(r'/diziler/'+re.escape(serie["slug"])+r'/[^"\']*bolum[^"\']*', txt)
                for l in set(links):
                    full=BASE_URL + l if l.startswith("/") else l
                    eps.append(full)
            except: pass
        # 2. normal href
        links=re.findall(r'href=["\']([^"\']+/bolum/[^"\']+)["\']', html)
        links+=re.findall(r'data-target=["\']([^"\']+/bolum/[^"\']+)["\']', html)
        for l in links:
            full=BASE_URL + l if l.startswith("/") else l
            if full not in eps:
                eps.append(full)
    except Exception as e:
        print(f"bolum hata {serie['name']}: {e}")
    print(f"  {serie['name']} -> {len(eps)} link")
    return eps[:20]

def get_m3u8(url):
    try:
        r=scraper.get(url, timeout=10)
        # direkt m3u8
        m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', r.text)
        if m: return m[0].replace("\\/","/")
        # embed
        m2=re.search(r'itemprop="embedURL"[^>]+href="([^"]+)"', r.text)
        if m2:
            embed=m2.group(1)
            r2=scraper.get(f"https://mak.sadecenjoy.workers.dev/?url={embed}", timeout=10)
            m3=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', r2.text)
            if m3: return m3[0]
            return embed
    except: pass
    return url

def run():
    series=get_series()
    entries=[]
    for s in series[:8]:
        print(f"\n{s['name']}")
        links=get_episodes(s)
        for link in links:
            m3u8=get_m3u8(link)
            if m3u8 and ".m3u8" in m3u8:
                bm=re.search(r'/(\d+)-bolum', link)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                entries.append({"dizi":s["name"],"bolum":bname,"url":m3u8})
                print(f"  OK {bname}")
            time.sleep(0.4)

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
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p and 'Kanal D' not in p]
        with open(MIRTI_FILE,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in k_blocks: out.write(b+"\n\n")
        print(f"Mirti: {len(old)} eski + {len(k_blocks)} KANALD")

if __name__=="__main__": run()
