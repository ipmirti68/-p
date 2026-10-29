import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup

OUTPUT_FILE = "atv_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"
BASE_URL = "https://www.atv.com.tr"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def run():
    print("ATV diziler cekiliyor...")
    series = []
    try:
        r = scraper.get(f"{BASE_URL}/diziler", timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/diziler/" not in href or "/bolum" in href or "fragman" in href:
                continue
            if href.count("/") > 3:
                continue
            if len(href) < 10:
                continue
            slug = href.split("/diziler/")[-1].split("/")[0]
            if not slug or slug in series:
                continue
            if slug in ["arsiv","tum","hepsi"]:
                continue
            full = BASE_URL + href if href.startswith("/") else href
            if full not in [s["url"] for s in series]:
                title = a.get("title") or slug.replace("-"," ").title()
                series.append({"name": title, "url": full, "slug": slug})
    except Exception as e:
        print(f"Dizi liste hata: {e}")

    # Fallback - en populer atv dizileri
    if len(series) < 3:
        print("Fallback ATV listesi")
        for slug in ["kurulus-osman","bir-gece-masali","sahipsizler","zoraki-misafir","can-borcu","karadut","kor-nokta","kardeslerim"]:
            full = f"{BASE_URL}/diziler/{slug}"
            if full not in [s["url"] for s in series]:
                series.append({"name": slug.replace("-"," ").title(), "url": full, "slug": slug})

    print(f"Toplam {len(series)} dizi bulundu")
    for s in series:
        print(" -", s["name"])

    entries = []
    for s in series[:10]: # ilk 10 dizi, fazla surmesin
        print(f"{s['name']} bolumleri aliniyor...")
        try:
            # bolumler sayfasi
            urls_to_try = [f"{s['url']}/bolumler", s['url']]
            found_links = []
            for u in urls_to_try:
                try:
                    r = scraper.get(u, timeout=15)
                    links = re.findall(r'href=["\']([^"\']+/bolum[^"\']*)["\']', r.text)
                    for l in links:
                        if "/bolum/" in l and l not in found_links:
                            found_links.append(l)
                except:
                    continue
            
            print(f"  {len(found_links)} bolum linki")
            for b_link in found_links[:20]:
                b_full = BASE_URL + b_link if b_link.startswith("/") else b_link
                if not b_full.startswith("http"):
                    b_full = BASE_URL + "/" + b_full.lstrip("/")
                try:
                    r = scraper.get(b_full, timeout=15)
                    # m3u8 bul
                    m = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', r.text)
                    if m:
                        url = m[0].replace('\\/','/').replace('\\u002F','/')
                        b_name_match = re.search(r'(\d+)\.?\s*[Bb]ol', r.text)
                        if not b_name_match:
                            b_name_match = re.search(r'/(\d+)-bolum', b_link)
                        b_name = f"{b_name_match.group(1)}. Bölüm" if b_name_match else "Bölüm"
                        entries.append({"dizi": s["name"], "bolum": b_name, "url": url, "poster": ""})
                        print(f"    {b_name} -> ok")
                    time.sleep(0.5)
                except:
                    continue
        except Exception as e:
            print(f"  hata: {e}")
            continue

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 tvg-logo="" group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

    print(f"{OUTPUT_FILE} - {len(entries)} bolum")

    if os.path.exists(MIRTI_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as ff:
            atv_blocks = ["#EXTINF" + p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(MIRTI_FILE, "r", encoding="utf-8", errors="ignore") as ff:
            cont = ff.read()
            first = cont.splitlines()[0] if cont else "#EXTM3U"
            old = ["#EXTINF" + p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "ATV Dizileri" not in p]
        with open(MIRTI_FILE, "w", encoding="utf-8") as out:
            out.write(first + "\n")
            for b in old: out.write(b + "\n\n")
            for b in atv_blocks: out.write(b + "\n\n")
        print(f"Bitti! {len(old)} eski + {len(atv_blocks)} ATV")

if __name__ == "__main__":
    run()
