import cloudscraper, re, json, os, time
from tqdm import tqdm

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
site_url = "https://www.showtv.com.tr"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def fetch(url):
    try:
        r = scraper.get(url, timeout=20)
        if len(r.text) > 800:
            return r.text
    except: pass
    return ""

def get_episodes(serie):
    eps=[]
    html = fetch(serie["url"])
    if not html: return []
    # tum bolum linkleri - duplicate engelle
    links = re.findall(r'href=["\'](/dizi/'+re.escape(serie["id"])+r'/[^"\']*bolum[^"\']*)["\']', html)
    links += re.findall(r'/dizi/'+re.escape(serie["id"])+r'/(\d+[^"\']*bolum[^"\']*)', html)
    # uniq yap
    uniq = []
    seen = set()
    for l in links:
        full = l if l.startswith("http") else site_url + (l if l.startswith("/") else "/" + l)
        full = full.split("?")[0].split("#")[0]
        if full not in seen and "bolum" in full.lower():
            seen.add(full)
            uniq.append(full)
    print(f"  {serie['name']} HTML -> {len(uniq)} bolum")
    for u in uniq[:20]:
        m=re.search(r'(\d+)[\.-_]?bolum', u, re.I)
        name = f"{m.group(1)}. Bolum" if m else u.split("/")[-1].replace("-"," ")[:40]
        eps.append({"name":name,"url":u,"img":""})
    return eps

def get_stream(url):
    html = fetch(url)
    if not html: return None
    # 1. tum m3u8
    found = re.findall(r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*', html)
    found = [f.replace("\\/","/").replace("\\u002F","/") for f in found]
    # en iyi sec
    for u in found:
        if "master" in u: return u
    if found: return found[0]
    # 2. data-hope
    m=re.search(r"data-hope-video='(.*?)'", html)
    if m:
        try:
            data=json.loads(m.group(1).replace('&quot;','"'))
            for item in data.get("media",{}).get("m3u8",[]):
                return item["src"]
        except: pass
    return None

def main():
    diziler = []
    for slug in ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates","guldur-guldur-show"]:
        diziler.append({"name":slug.replace("-"," ").title(),"id":slug,"url":f"{site_url}/dizi/{slug}"})
    print(f"Toplam {len(diziler)} dizi")
    all_data=[]
    for s in diziler:
        eps=get_episodes(s)
        ok=[]
        seen_stream=set()
        for ep in eps[:12]:
            stream=get_stream(ep["url"])
            if stream and stream not in seen_stream:
                seen_stream.add(stream)
                ep["stream_url"]=stream
                ok.append(ep)
                print(f"    OK {ep['name']}")
            time.sleep(0.6)
        if ok:
            s["episodes"]=ok
            all_data.append(s)

    with open(m3u_file,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in all_data:
            for ep in serie["episodes"]:
                f.write(f'#EXTINF:-1 group-title="SHOWTV Dizileri",TR: {ep["name"]} - {serie["name"]}\n{ep["stream_url"]}\n')

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
