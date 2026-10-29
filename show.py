import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup
from tqdm import tqdm

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
site_url = "https://www.showtv.com.tr"
diziler_url = "https://www.showtv.com.tr/diziler"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

BLACKLIST = ["tanitim","tum_bolumler","tum-bolumler","sahne","sahneler","fragman","fragmanlar","bolum","bolumler","oyuncular","sezon","ozet","haber","galeri"]

def get_arsiv_list():
    print("Diziler sayfasi cekiliyor...")
    series = []
    try:
        # 1. SITEMAP dene - en garanti
        try:
            r = scraper.get("https://www.showtv.com.tr/sitemap.xml", timeout=15)
            slugs = re.findall(r"/dizi/([a-z0-9-]+)/", r.text)
            for slug in set(slugs):
                if slug.lower() in BLACKLIST or "_" in slug or len(slug) < 3:
                    continue
                if slug not in [s["id"] for s in series]:
                    series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": ""})
            print(f"Sitemapten {len(series)} bulundu")
        except:
            pass

        # 2. Ana sayfadan
        r = scraper.get(diziler_url, timeout=20)
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/dizi/" not in href:
                continue
            slug = href.split("/dizi/")[-1].split("/")[0].split("?")[0].strip().lower()
            if not slug or slug in BLACKLIST or len(slug) < 3 or "_" in slug:
                continue
            if slug not in [s["id"] for s in series]:
                img = a.find("img")
                series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": img.get("src","") if img else ""})

        # 3. Fallback gercek diziler
        if len(series) < 5:
            print("Fallback gercek diziler ekleniyor...")
            real = ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates","guldur-guldur-show","kizilcik-serbeti","bahar","deha","siyah-kalp","sandik-kokusu"]
            for slug in real:
                if slug in BLACKLIST:
                    continue
                if slug not in [s["id"] for s in series]:
                    series.append({"name": slug.replace("-"," ").title(), "url": f"{site_url}/dizi/{slug}", "id": slug, "img": ""})

        # Temizle ve dogrula - pagination var mi kontrol et
        final = []
        for s in series:
            if s["id"] in BLACKLIST:
                continue
            # hizli dogrulama
            try:
                test_url = f"https://www.showtv.com.tr/dizi/pagination/{s['id']}/2/0"
                tr = scraper.get(test_url, timeout=5)
                if '"episodes"' in tr.text or '"title"' in tr.text:
                    final.append(s)
                else:
                    # yine de ekle eger bilinen gercek diziyse
                    if s["id"] in ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates"]:
                        final.append(s)
            except:
                final.append(s)

        print(f"Toplam {len(final)} dizi bulundu")
        for u in final:
            print(" -", u["name"])
        return final
    except Exception as e:
        print(f"Hata: {e}")
        return series

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
