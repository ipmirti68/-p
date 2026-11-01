import cloudscraper, re, os, time, json
from bs4 import BeautifulSoup

m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
GROUP_NAME="SHOW Dizileri"
site_url="https://www.showtv.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(url):
    try:
        r=scraper.get(url, timeout=20)
        if len(r.text)>1000: return r.text
    except: return ""
    return ""

def extract_m3u8(html):
    # 1. vmcdn m3u8 direkt
    m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*', html)
    if m:
        # en uzun olan genelde master
        return sorted(m, key=len)[-1].replace("\\/","/")
    # 2. data-hope-video json içinde
    mh=re.search(r"data-hope-video='(.*?)'", html)
    if mh:
        try:
            data=json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            if "media" in data:
                for typ in ["m3u8","mp4"]:
                    if typ in data["media"]:
                        for item in data["media"][typ]:
                            if "src" in item and ".m3u8" in item["src"]:
                                return item["src"].replace("\\/","/")
                        # mp4 varsa bile m3u8'e çevir dene
                        if typ=="mp4" and data["media"][typ]:
                            mp4=data["media"][typ][0]["src"]
                            # mp4 -> m3u8 bazen aynı path'te
                            return mp4.replace(".mp4",".m3u8")
        except: pass
    # 3. genel m3u8
    m2=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html)
    if m2: return m2[0].replace("\\/","/")
    return None

slugs=["kizilcik-serbeti","sevdan-bir-ates","menekse","muhtemel-ask"]
entries=[]

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{site_url}/dizi/{slug}")
    if not html: continue
    soup=BeautifulSoup(html, "html.parser")
    links={}
    for a in soup.find_all("a", href=True):
        href=a["href"]
        if slug not in href.lower(): continue
        if "bolum" not in href.lower(): continue
        if "bolumler" in href.lower(): continue
        if href.startswith("/"): href=site_url+href
        # bolum numarası al
        bm=re.search(r'(\d+)\s*[-.]?\s*bolum', href.lower())
        if not bm: bm=re.search(r'bolum[^0-9]*(\d+)', href.lower())
        num=int(bm.group(1)) if bm else 0
        # duplicate engelle - en büyük numaralı link kalsın
        if href not in links:
            links[href]=num

    # numaraya göre sırala, en son 3 bölümü al
    sorted_links=sorted(links.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  Son {len(sorted_links)} bolum: {[x[0].split('/')[-1] for x in sorted_links]}")

    for full, num in sorted_links:
        print(f"  -> {full}")
        bhtml=fetch(full)
        m3u8=extract_m3u8(bhtml)
        if m3u8:
            bname=f"{num}. Bolum" if num else "Bolum"
            dizi_adi=slug.replace("-"," ").title()
            if slug=="kizilcik-serbeti": dizi_adi="Kizilcik Serbeti"
            if slug=="sevdan-bir-ates": dizi_adi="Sevdan Bir Ates"
            entries.append({"dizi":dizi_adi,"bolum":bname,"url":m3u8,"num":num})
            print(f"  OK {dizi_adi} {bname} -> {m3u8[:70]}...")
        else:
            print(f"  URL bulunamadı")
        time.sleep(0.5)

# numaraya göre tekrar sırala
entries=sorted(entries, key=lambda x: (x["dizi"], -x["num"]))

# yaz
with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        # DUPLICATE engellemek için unique
        f.write(f'#EXTINF:-1 group-title="{GROUP_NAME}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

print(f"\n{m3u_file} -> {len(entries)} bolum (tekrar yok, son 3'er)")

# mirti68.m3u
if not os.path.exists(mirti_file):
    open(mirti_file,"w").write("#EXTM3U\n")

with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP_NAME not in p]
with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]

with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")

print(f"mirti68.m3u güncellendi - {GROUP_NAME} içinde {len(new)} kayıt")
