import cloudscraper, re, json, os, time
from bs4 import BeautifulSoup
from tqdm import tqdm

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
site_url = "https://www.showtv.com.tr"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
BLACKLIST = ["tanitim","tum_bolumler","sahne","fragman","oyuncular"]

def get_diziler():
    series=[]
    try:
        r = scraper.get(f"{site_url}/diziler", timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all("a", href=True):
            href=a["href"]
            if "/dizi/" not in href: continue
            slug=href.split("/dizi/")[-1].split("/")[0].lower().strip()
            if not slug or "_" in slug or slug in BLACKLIST or len(slug)<3: continue
            if slug not in [s["id"] for s in series]:
                series.append({"name":slug.replace("-"," ").title(),"url":f"{site_url}/dizi/{slug}","id":slug})
    except: pass
    # Fallback - en az bunlar olsun
    for slug in ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates"]:
        if slug not in [s["id"] for s in series]:
            series.append({"name":slug.replace("-"," ").title(),"url":f"{site_url}/dizi/{slug}","id":slug})
    print(f"Toplam {len(series)} dizi")
    return series

def get_episodes_html(serie):
    # YENI YONTEM - direkt dizi sayfasindan bolum linklerini cek
    eps=[]
    try:
        r = scraper.get(serie["url"], timeout=15)
        html=r.text
        # 1. tum /dizi/slug/xxx-bolum linkleri
        links = re.findall(r'href=["\'](/dizi/'+re.escape(serie["id"])+r'/[^"\']*bolum[^"\']*)["\']', html)
        links += re.findall(r'href=["\']('+re.escape(serie["url"])+r'/[^"\']*bolum[^"\']*)["\']', html)
        # 2. tum bolum linkleri genel
        links += re.findall(r'href=["\']([^"\']*/\d+-bolum[^"\']*)["\']', html)
        
        uniq=list(dict.fromkeys(links))
        for link in uniq[:40]:
            full = link if link.startswith("http") else site_url + link if link.startswith("/") else site_url + "/" + link
            # isim
            m = re.search(r'(\d+)[\.-]bolum', link)
            name = f"{m.group(1)}. Bolum" if m else link.split("/")[-1].replace("-"," ")
            eps.append({"name":name, "url":full, "img":""})
    except Exception as e:
        print(f"ep hata {serie['id']}: {e}")
    print(f"  {serie['name']} -> {len(eps)} bolum linki")
    return eps

def get_stream(url):
    try:
        r = scraper.get(url, timeout=15)
        html=r.text
        # tum m3u8leri bul
        found = re.findall(r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*', html)
        if found:
            # en kaliteli sec
            for u in found:
                if "master" in u or "1080" in u or "720" in u:
                    return u.replace("\\/","/")
            return found[0].replace("\\/","/")
        # data-hope
        m = re.search(r"data-hope-video='(.*?)'", html)
        if m:
            data=json.loads(m.group(1).replace('&quot;','"'))
            for item in data.get("media",{}).get("m3u8",[]):
                if "src" in item:
                    return item["src"]
    except: pass
    return None

def main():
    series=get_diziler()
    all_data=[]
    for s in tqdm(series):
        print(f"\n{s['name']}")
        eps=get_episodes_html(s)
        ok=[]
        for ep in eps[:15]: # her diziden 15 bolum max, hizli bitsin
            stream=get_stream(ep["url"])
            if stream:
                ep["stream_url"]=stream
                ok.append(ep)
                print(f"  OK {ep['name']}")
            time.sleep(0.5)
        if ok:
            s["episodes"]=ok
            all_data.append(s)

    with open(m3u_file,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in all_data:
            for ep in serie["episodes"]:
                f.write(f'#EXTINF:-1 tvg-logo="{ep["img"]}" group-title="SHOWTV Dizileri",TR: {ep["name"]} - {serie["name"]}\n{ep["stream_url"]}\n')

    print(f"{m3u_file} -> {sum(len(s['episodes']) for s in all_data)} bolum")
    if os.path.exists(m3u_file) and os.path.exists(mirti_file):
        with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff:
            blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0]
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
        with open(mirti_file,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")
        print(f"Mirti: {len(old)} eski + {len(blocks)} SHOWTV")

if __name__=="__main__": main()
