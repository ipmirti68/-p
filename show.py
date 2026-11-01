import re, os, time, json
from bs4 import BeautifulSoup

m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
GROUP="SHOW Dizileri"
site="https://www.showtv.com.tr"

def get_poster(slug):
    try:
        import requests
        r=requests.get(f"{site}/dizi/{slug}", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        soup=BeautifulSoup(r.content, "html.parser")
        og=soup.find("meta", property="og:image")
        if og and og.get("content"): return og["content"]
    except: pass
    return ""

def get_m3u8(url):
    # 1. yt-dlp en sağlamı 【entity-SHOW TV¦canonical_name=SHOW TV】 için
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u and "vmcdn" in u:
                    return u
            # data-hope-video json içinde de olabilir
            if "formats" in info and info["formats"]:
                for f in info["formats"]:
                    if ".m3u8" in f.get("url",""):
                        return f["url"]
    except Exception as e:
        print(f"    yt-dlp hata: {e}")
    
    # 2. cloudscraper fallback
    try:
        import cloudscraper
        scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
        r=scraper.get(url, timeout=20)
        html=r.text
        m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*', html)
        if m: return sorted(m, key=len)[-1].replace("\\/","/")
        mh=re.search(r"data-hope-video='(.*?)'", html)
        if mh:
            j=json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            return j["media"]["m3u8"][0]["src"].replace("\\/","/")
    except: pass
    return None

# TAZE MANUEL - senin verdiğin hep duracak
MANUEL={
    "sevdan-bir-ates": [
        {"num":8, "url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392", "poster":""},
    ]
}

# son bölüm numaraları - burayı güncelle yeter
LAST_NUM={
    "kizilcik-serbeti": 145,
    "sevdan-bir-ates": 8,
    "muhtemel-ask": 10,
    "menekse": 5
}

entries=[]
posters={}

# posterleri çek
for slug in LAST_NUM.keys():
    p=get_poster(slug)
    posters[slug]=p
    print(f"Poster {slug}: {p[:60]}")

# manuel ekle
for slug, items in MANUEL.items():
    for it in items:
        logo=posters.get(slug,"")
        entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{it['num']}. Bolum","url":it["url"],"num":it["num"],"logo":logo})

# otomatik son 3
for slug, last in LAST_NUM.items():
    print(f"\n=== {slug.upper()} son {last} ===")
    for num in range(last, last-3, -1):
        if any(e["dizi"].lower()==slug.replace("-"," ").title().lower() and e["num"]==num for e in entries):
            continue
        candidates=[
            f"{site}/dizi/{slug}/bolum/{num}-bolum",
            f"{site}/dizi/{slug}/bolum/{num}-bolum-izle",
            f"{site}/dizi/{slug}/{num}-bolum",
            f"{site}/dizi/{slug}/bolum/{num}",
        ]
        ok=False
        for url in candidates:
            print(f"  -> {url}")
            m3u8=get_m3u8(url)
            if m3u8 and len(m3u8)>60 and "fragman" not in m3u8.lower():
                logo=posters.get(slug,"")
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum","url":m3u8,"num":num,"logo":logo})
                print(f"  OK {num}")
                ok=True
                break
            else:
                print(f"  yok")
        if not ok:
            print(f"  BULAMADI {num}")
        time.sleep(0.5)

# her diziden son 3'e indir, tekrar yok
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

# yaz
with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x:(x["dizi"], -x["num"])):
        logo=e.get("logo","")
        if logo:
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{GROUP}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')
        else:
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

print(f"mirti68.m3u güncellendi - {len(new)} kayit")
