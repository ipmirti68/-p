import cloudscraper, re, os, time, json

m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
GROUP="SHOW Dizileri"
site="https://www.showtv.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(u):
    try:
        r=scraper.get(u, timeout=20)
        if len(r.text)>1000: return r.text
    except: return ""
    return ""

def extract_m3u8(html):
    m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*', html)
    if m:
        return sorted(m, key=len)[-1].replace("\\/","/")
    mh=re.search(r"data-hope-video='(.*?)'", html)
    if mh:
        try:
            j=json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            return j["media"]["m3u8"][0]["src"].replace("\\/","/")
        except: pass
    return None

def ytdlp_m3u8(page_url):
    if "fragman" in page_url or "galeri" in page_url: return None
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(page_url, download=False)
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u and "vmcdn" in u:
                    return u
    except: pass
    return None

# MANUEL - senin verdiğin 8. bölüm hep duracak
MANUEL={
    "sevdan-bir-ates": [{"num":8, "url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392"}]
}

entries=[]
for slug, items in MANUEL.items():
    for it in items:
        entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{it['num']}. Bolum","url":it["url"],"num":it["num"]})
        print(f"MANUEL {slug} {it['num']}")

# DİZİ BAŞINA SON BÖLÜM NUMARALARI - bunları otomatik bulamazsa buradan deneyecek
LAST_NUM={
    "kizilcik-serbeti": 145,
    "sevdan-bir-ates": 8,
    "muhtemel-ask": 10,
    "menekse": 5
}

slugs=["kizilcik-serbeti","sevdan-bir-ates","muhtemel-ask","menekse"]

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    last=LAST_NUM.get(slug, 10)
    # son 3 bölümü dene: 145,144,143 gibi
    for num in range(last, last-3, -1):
        # manuelde varsa atla
        if any(e["dizi"].lower()==slug.replace("-"," ").title().lower() and e["num"]==num for e in entries):
            continue
        # SHOW TV'de 2 farklı URL kalıbı var, ikisini de dene
        candidates=[
            f"{site}/dizi/{slug}/bolum/{num}-bolum",
            f"{site}/dizi/{slug}/bolum/{num}-bolum-izle",
            f"{site}/dizi/{slug}/{num}-bolum",
        ]
        found=False
        for url in candidates:
            print(f"  -> dene {url}")
            # önce yt-dlp
            m3u8=ytdlp_m3u8(url)
            if not m3u8:
                html=fetch(url)
                if not html: continue
                # fragman sayfası mı?
                if "fragman" in html.lower() and f"{num}. bolum fragman" in html.lower():
                    print(f"     fragman, atla")
                    continue
                m3u8=extract_m3u8(html)
            if m3u8 and len(m3u8)>60:
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum","url":m3u8,"num":num})
                print(f"  OK {num} -> {m3u8[:70]}...")
                found=True
                break
        if not found:
            print(f"  BULAMADI {num}")
        time.sleep(0.5)

# tekrar temizle - her diziden son 3
final={}
for e in entries:
    k=e["dizi"].lower()
    if k not in final: final[k]=[]
    final[k].append(e)

all_final=[]
for k,v in final.items():
    uniq={it["num"]:it for it in v}
    top3=sorted(uniq.values(), key=lambda x:x["num"], reverse=True)[:3]
    all_final.extend(top3)

with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x:(x["dizi"], -x["num"])):
        f.write(f'#EXTINF:-1 group-title="{GROUP}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

print(f"\n{m3u_file} -> {len(all_final)} bolum")

if not os.path.exists(mirti_file): open(mirti_file,"w").write("#EXTM3U\n")
with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")

print(f"mirti68.m3u güncellendi - {len(new)} kayıt, fragman yok")
