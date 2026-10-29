import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup
from tqdm import tqdm

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
site_url = "https://www.showtv.com.tr"
diziler_url = "https://www.showtv.com.tr/diziler"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
BLACKLIST = ["tanitim","tum_bolumler","tum-bolumler","sahne","sahneler","fragman","fragmanlar","bolum","bolumler","oyuncular"]

def get_arsiv_list():
    print("Diziler sayfasi cekiliyor...")
    series = []
    try:
        r = scraper.get(diziler_url, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/dizi/" not in href: continue
            slug = href.split("/dizi/")[-1].split("/")[0].lower()
            if not slug or slug in BLACKLIST or "_" in slug or len(slug)<3: continue
            if slug not in [s["id"] for s in series]:
                series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": ""})
    except Exception as e:
        print(e)
    # fallback gercek diziler
    if len(series) < 5:
        for slug in ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates"]:
            if slug not in [s["id"] for s in series]:
                series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": ""})
    print(f"Toplam {len(series)} dizi bulundu")
    for u in series: print(" -", u["name"])
    return series

def parse_episodes_page(sid, pno):
    try:
        url = f"https://www.showtv.com.tr/dizi/pagination/{sid}/2/{pno}"
        r = scraper.get(url, timeout=10)
        data = r.json().get("episodes", [])
        items = []
        for it in data:
            items.insert(0, {"name": it["title"].replace("-"," "), "img": it.get("image",""), "url": site_url + it["link"]})
        return items
    except: return []

def get_all_episodes(serie):
    all_eps=[]; page=0
    while page < 15:
        eps=parse_episodes_page(serie["id"], page)
        if not eps: break
        all_eps = eps + all_eps
        page+=1; time.sleep(0.2)
    return all_eps

def get_stream(url):
    try:
        r = scraper.get(url, timeout=15)
        html = r.text
        # 1. eski yontem
        m = re.search(r"data-hope-video='(.*?)'", html)
        if m:
            data = json.loads(m.group(1).replace('&quot;','"'))
            for item in data.get("media",{}).get("m3u8",[]):
                if "src" in item and ".m3u8" in item["src"]:
                    return item["src"]
        # 2. YENI - sayfada herhangi bir m3u8 ara (en garanti)
        m2 = re.findall(r'https?://[^"\']+\.m3u8[^"\']*', html)
        if m2:
            # en temiz olani sec
            for u in m2:
                if "master" in u or "720" in u or "480" in u:
                    return u.replace('\\/','/')
            return m2[0].replace('\\/','/')
        # 3. __NEXT_DATA__ icinde
        m3 = re.search(r'"src"\s*:\s*"(https://[^"]+\.m3u8[^"]*)"', html)
        if m3:
            return m3.group(1)
    except Exception as e:
        print(f"stream hata {url}: {e}")
    return None

def main():
    series=get_arsiv_list()
    data=[]
    for idx in tqdm(range(len(series))):
        s=series[idx]
        print(f"{idx+1}/{len(series)} {s['name']}")
        eps=get_all_episodes(s)
        temp=[]
        for ep in eps:
            stream=get_stream(ep["url"])
            if stream:
                ep["stream_url"]=stream
                temp.append(ep)
                print(f"  -> {ep['name']}")
            time.sleep(0.4)
        if temp:
            s["episodes"]=temp
            data.append(s)
    with open(m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in data:
            for ep in serie["episodes"]:
                f.write(f'#EXTINF:-1 tvg-logo="{ep["img"]}" group-title="SHOWTV Dizileri",TR: {ep["name"]}\n{ep["stream_url"]}\n')
    print(f"{m3u_file} olusturuldu! {sum(len(s['episodes']) for s in data)} bolum")
    if os.path.exists(m3u_file) and os.path.exists(mirti_file):
        with open(m3u_file, "r", encoding="utf-8", errors="ignore") as ff:
            show_blocks = ["#EXTINF" + p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file, "r", encoding="utf-8", errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
            old=["#EXTINF" + p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
        with open(mirti_file, "w", encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in show_blocks: out.write(b+"\n\n")
        print(f"Bitti! {len(old)} eski + {len(show_blocks)} SHOWTV")

if __name__=="__main__": main()
