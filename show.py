import cloudscraper, re, json, os, time
from tqdm import tqdm

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
site_url = "https://www.showtv.com.tr"
WORKER = "https://mak.sadecenjoy.workers.dev"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def fetch(url):
    # 1. normal dene
    try:
        r = scraper.get(url, timeout=15)
        if len(r.text) > 1000 and "bolum" in r.text.lower():
            return r.text
    except: pass
    # 2. worker proxy ile dene - bu kesin aliyor
    try:
        r = scraper.get(f"{WORKER}/?url={url}", timeout=20)
        return r.text
    except:
        return ""

def get_diziler():
    series=[]
    for slug in ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates"]:
        series.append({"name":slug.replace("-"," ").title(),"url":f"{site_url}/dizi/{slug}","id":slug})
    print(f"Toplam {len(series)} dizi")
    return series

def get_episodes(serie):
    eps=[]
    # pagination API'yi worker ile dene
    for page in range(0,5):
        try:
            api = f"{site_url}/dizi/pagination/{serie['id']}/2/{page}"
            txt = fetch(api)
            data = json.loads(txt) if txt.strip().startswith("{") else {}
            episodes = data.get("episodes",[])
            if not episodes:
                break
            for it in episodes:
                eps.insert(0, {"name": it["title"], "url": site_url + it["link"], "img": it.get("image","")})
        except:
            break
    print(f"  {serie['name']} API -> {len(eps)} bolum")
    # API bos ise HTML'den dene
    if not eps:
        html = fetch(serie["url"])
        links = re.findall(r'href=["\']([^"\']*'+re.escape(serie["id"])+r'[^"\']*bolum[^"\']*)["\']', html)
        links += re.findall(r'"link"\s*:\s*"(/dizi/'+re.escape(serie["id"])+r'/[^"]+)"', html)
        for l in list(dict.fromkeys(links))[:20]:
            full = l if l.startswith("http") else site_url + l
            m=re.search(r'(\d+)-bolum', l)
            name = f"{m.group(1)}. Bolum" if m else "Bolum"
            eps.append({"name":name,"url":full,"img":""})
        print(f"  {serie['name']} HTML -> {len(eps)} bolum")
    return eps

def get_stream(url):
    html = fetch(url)
    if not html: return None
    found = re.findall(r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*', html)
    if found:
        for u in found:
            if "master" in u or "720" in u:
                return u.replace("\\/","/")
        return found[0].replace("\\/","/")
    m = re.search(r"data-hope-video='(.*?)'", html)
    if m:
        try:
            data=json.loads(m.group(1).replace('&quot;','"'))
            for item in data.get("media",{}).get("m3u8",[]):
                return item["src"]
        except: pass
    return None

def main():
    series=get_diziler()
    all_data=[]
    for s in tqdm(series):
        eps=get_episodes(s)
        ok=[]
        for ep in eps[:10]:
            stream=get_stream(ep["url"])
            if stream:
                ep["stream_url"]=stream
                ok.append(ep)
                print(f"    OK {ep['name']}")
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
    if os.path.exists(mirti_file):
        with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff:
            blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0]
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
        with open(mirti_file,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")

if __name__=="__main__": main()
