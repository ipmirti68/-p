import cloudscraper, re, os, time, json
m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
site_url="https://www.showtv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=25)
        if len(r.text)>1000: return r.text
    except: pass
    try:
        r=scraper.get(url,timeout=15)
        return r.text
    except: return ""

def extract_m3u8(html):
    m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*',html)
    if m: return m[0].replace("\\/","/")
    mh=re.search(r"data-hope-video='(.*?)'",html)
    if mh:
        try:
            data=json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            if "media" in data and "m3u8" in data["media"]:
                return data["media"]["m3u8"][0]["src"].replace("\\/","/")
        except: pass
    return None

entries=[]
# Senin verdiğin Sevdan 8 manuel
entries.append({"dizi":"Sevdan Bir Ates","bolum":"8. Bolum","url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793317167&st=9f56173e468ce41d4a9e21d474c60eb9"})
print("MANUEL Sevdan 8 eklendi")

# SENİN İSTEDİĞİN 4'LÜ + DİĞERLERİ
slugs=[
    "kizilcik-serbeti",
    "sevdan-bir-ates",
    "menekse",
    "muhtemel-ask",
    "bahar",
    "siyah-kalp",
    "deha",
    "sandik-kokusu",
    "guldur-guldur-show"
]

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{site_url}/dizi/{slug}")
    links=re.findall(r'/dizi/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:8]
    print(f"  {len(uniq)} bolum linki")
    for link in uniq:
        if "8-bolum" in link and slug=="sevdan-bir-ates": continue
        full=site_url+link
        bhtml=fetch(full)
        m3u8=extract_m3u8(bhtml)
        if m3u8:
            bm=re.search(r'(\d+)',link)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            dizi_adi = slug.replace("-"," ").title()
            if slug=="kizilcik-serbeti": dizi_adi="Kizilcik Serbeti"
            if slug=="sevdan-bir-ates": dizi_adi="Sevdan Bir Ates"
            if slug=="menekse": dizi_adi="Menekse"
            if slug=="muhtemel-ask": dizi_adi="Muhtemel Ask"
            entries.append({"dizi":dizi_adi,"bolum":bname,"url":m3u8})
            print(f"  OK {dizi_adi} {bname}")
        time.sleep(0.6)

with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="SHOWTV Dizileri",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')
print(f"\n{m3u_file} -> {len(entries)} bolum")

if os.path.exists(mirti_file):
    with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff:
        blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
    with open(mirti_file,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
