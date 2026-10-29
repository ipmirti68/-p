import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup
from tqdm import tqdm

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
site_url = "https://www.showtv.com.tr"
diziler_url = "https://www.showtv.com.tr/diziler"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def get_arsiv_list():
    print("Diziler sayfasi cekiliyor...")
    try:
        r = scraper.get(diziler_url, timeout=20)
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        series = []

        # YENI YONTEM 1: __NEXT_DATA__ json
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                txt = json.dumps(data)
                links = re.findall(r'"/dizi/([^"/]+)"', txt)
                for slug in set(links):
                    series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": ""})
            except:
                pass

        # YENI YONTEM 2: tum a[href=/dizi/...]
        if not series:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/dizi/" in href and "/bolum" not in href and "/fragman" not in href:
                    slug = href.split("/dizi/")[-1].split("/")[0].split("?")[0]
                    if slug and len(slug) > 2 and slug not in [s["id"] for s in series]:
                        img = a.find("img")
                        series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": img.get("src","") if img else ""})

        # YENI YONTEM 3: fallback - en populer diziler elle (site json vermezse)
        if len(series) < 3:
            print("Fallback liste kullaniliyor...")
            fallback = ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","guzel-gunler","aile","kizilcik-serbeti","sevdan-bir-ates"]
            for slug in fallback:
                if slug not in [s["id"] for s in series]:
                    series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": ""})

        uniq = []
        seen = set()
        for s in series:
            if s["id"] not in seen:
                seen.add(s["id"])
                uniq.append(s)
        print(f"Toplam {len(uniq)} dizi bulundu")
        for u in uniq[:10]:
            print(" -", u["name"])
        return uniq
    except Exception as e:
        print(f"Hata: {e}")
        return []

def parse_episodes_page(serie_id, page_no):
    try:
        url = f"https://www.showtv.com.tr/dizi/pagination/{serie_id}/2/{page_no}"
        r = scraper.get(url, timeout=10)
        data = r.json().get("episodes", [])
        items = []
        for it in data:
            items.insert(0, {"name": it["title"].replace("-"," "), "img": it.get("image",""), "url": site_url + it["link"]})
        return items
    except:
        return []

def get_all_episodes(serie):
    all_eps = []
    page = 0
    while page < 25:
        eps = parse_episodes_page(serie["id"], page)
        if not eps:
            break
        all_eps = eps + all_eps
        page += 1
        time.sleep(0.2)
    return all_eps

def get_stream(url):
    try:
        r = scraper.get(url, timeout=10)
        m = re.search(r"data-hope-video='(.*?)'", r.text)
        if m:
            data = json.loads(m.group(1).replace('&quot;','"'))
            for item in data.get("media",{}).get("m3u8",[]):
                if "src" in item and ".m3u8" in item["src"]:
                    return item["src"]
        # yedek
        m2 = re.search(r'(https://[^"\']+\.m3u8[^"\']*)', r.text)
        if m2:
            return m2.group(1)
    except:
        pass
    return None

def main():
    series = get_arsiv_list()
    data = []
    for idx in tqdm(range(len(series))):
        s = series[idx]
        print(f"{idx+1}/{len(series)} {s['name']}")
        eps = get_all_episodes(s)
        temp = []
        for ep in eps:
            stream = get_stream(ep["url"])
            if stream:
                ep["stream_url"] = stream
                temp.append(ep)
            time.sleep(0.3)
        if temp:
            s["episodes"] = temp
            data.append(s)
    
    # showtv.m3u yaz
    with open(m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in data:
            for ep in serie["episodes"]:
                f.write(f'#EXTINF:-1 tvg-logo="{ep["img"]}" group-title="SHOWTV Dizileri",TR: {ep["name"]}\n{ep["stream_url"]}\n')

    print(f"{m3u_file} olusturuldu! {sum(len(s['episodes']) for s in data)} bolum")

    # mirti68 e ekle
    if os.path.exists(m3u_file) and os.path.exists(mirti_file):
        with open(m3u_file, "r", encoding="utf-8", errors="ignore") as ff:
            show_blocks = ["#EXTINF" + p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file, "r", encoding="utf-8", errors="ignore") as ff:
            cont = ff.read()
            first = cont.splitlines()[0] if cont else "#EXTM3U"
            old = ["#EXTINF" + p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
        with open(mirti_file, "w", encoding="utf-8") as out:
            out.write(first + "\n")
            for b in old:
                out.write(b + "\n\n")
            for b in show_blocks:
                out.write(b + "\n\n")
        print(f"Bitti! {len(old)} eski + {len(show_blocks)} SHOWTV")

if __name__ == "__main__":
    main()
