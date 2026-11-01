import cloudscraper, re, os, time, json
from bs4 import BeautifulSoup

m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
site_url="https://www.showtv.com.tr"
GROUP_NAME="SHOW Dizileri"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(url):
    try:
        r=scraper.get(url, timeout=20)
        if len(r.text)>1000: return r.text
    except Exception as e:
        print(f"fetch hata {e}")
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
        if slug in h and "bolum" in h.lower() and "bolumler" not in h.lower():
            if h.startswith("/"): h=site_url+h
            links.add(h)
    print(f"  {len(links)} bolum bulundu")
    for full in list(links)[:8]:
        bhtml=fetch(full)
        m3u8=extract_m3u8(bhtml)
        if m3u8:
            bm=re.search(r'(\d+)',full)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
            print(f"  OK {bname}")
        time.sleep(0.3)

# 1- kendi m3u
with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="{GROUP_NAME}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

print(f"\nToplam {len(entries)} SHOW bolumu -> {m3u_file}")

# 2- mirti68.m3u içine EKLEME, silme değil
if os.path.exists(mirti_file):
    with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read()
    first=cont.splitlines()[0] if cont.startswith("#EXTM3U") else "#EXTM3U"
    # kendi grubun dışındakileri koru
    old_blocks=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP_NAME not in p]
else:
    first="#EXTM3U"
    old_blocks=[]

with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff:
    new_blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]

with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old_blocks: out.write(b+"\n\n")
    for b in new_blocks: out.write(b+"\n\n")

print(f"mirti68.m3u güncellendi -> {GROUP_NAME} grubu eklendi")
