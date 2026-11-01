import cloudscraper, re, os, time, json
from bs4 import BeautifulSoup
m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
site_url="https://www.showtv.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(url):
    try:
        r=scraper.get(url, timeout=20)
        if len(r.text)>1000: return r.text
    except: return ""
    return ""

def extract_m3u8(html):
    m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*',html)
    if m: return m[0].replace("\\/","/")
    mh=re.search(r"data-hope-video='(.*?)'",html)
    if mh:
        try:
            data=json.loads(mh.group(1).replace('&quot;','"'))
            return data["media"]["m3u8"][0]["src"].replace("\\/","/")
        except: pass
    return None

slugs=["kizilcik-serbeti","sevdan-bir-ates","menekse","muhtemel-ask","bahar","siyah-kalp"]
entries=[]
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{site_url}/dizi/{slug}")
    soup=BeautifulSoup(html, "html.parser")
    links=set()
    for a in soup.find_all("a", href=True):
        h=a["href"]
        if slug in h and "bolum" in h.lower():
            if h.startswith("/"): h=site_url+h
            links.add(h)
    print(f"  {len(links)} bolum")
    for full in list(links)[:8]:
        bhtml=fetch(full)
        m3u8=extract_m3u8(bhtml)
        if m3u8:
            bm=re.search(r'(\d+)',full)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
            print(f"  OK {bname}")

with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="SHOWTV Dizileri",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

if os.path.exists(mirti_file):
    with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
    with open(mirti_file,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
