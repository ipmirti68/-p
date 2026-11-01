import re, os, time, json
from bs4 import BeautifulSoup

OUTPUT="atv_playlist.m3u"
MIRTI="mirti68.m3u"
BASE="https://www.atv.com.tr"
GROUP="【entity-ATV¦canonical_name=ATV】 Dizileri"

def get_poster(slug):
    try:
        import requests
        r=requests.get(f"{BASE}/diziler/{slug}", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        soup=BeautifulSoup(r.content, "html.parser")
        og=soup.find("meta", property="og:image")
        if og and og.get("content"): return og["content"]
    except: pass
    return ""

def get_m3u8(url):
    if "bolumler" in url.lower(): return None
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u and "erbvr" in u:
                    return u
    except Exception as e:
        print(f"    yt-dlp hata {url[:40]}: {e}")
    # fallback regex
    try:
        import cloudscraper
        scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
        html=scraper.get(url, timeout=20).text
        html=html.replace("hxx","https")
        m=re.findall(r'https?://[^\s"\'\\]*erbvr\.com[^\s"\'\\]*\.m3u8[^\s"\'\\]*', html)
        if m: return m[0].replace("\\/","/")
    except: pass
    return None

# senin örneğin gibi taze token - süresi uzun
MANUEL={
    # "gunesin-dogdugu-yer": [{"num":7, "url":"https://htxkbiqd.erbvr.com/vms/5/5f/aa/55faa449-9cfb-4461-8099-eca9b7aced6e/55faa449-9cfb-4461-8099-eca9b7aced6e.smil/.m3u8?st=o5jgR3fHDwMG2b_k7aPlog&e=1793568485&sid=_GE7aEi-wEGpYrZmrgE3hg"}]
}

# son bölüm numaraları - burayı güncelle yeter
LAST_NUM={
    "gunesin-dogdugu-yer": 7,
    "alti-ustu-istanbul": 5,
    "abi": 10,
    "ask-ve-taht": 8,
    "mercan-kosk": 6,
    "kurulus-osman": 180,
    "bir-gece-masali": 30
}

entries=[]
posters={}

for slug in LAST_NUM.keys():
    p=get_poster(slug)
    posters[slug]=p
    print(f"Poster {slug}: {p[:60]}")

# manuel ekle
for slug, items in MANUEL.items():
    for it in items:
        entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{it['num']}. Bolum","url":it["url"],"num":it["num"],"logo":posters.get(slug,"")})

# otomatik son 3
for slug, last in LAST_NUM.items():
    print(f"\n=== {slug.upper()} son {last} ===")
    for num in range(last, last-3, -1):
        if any(e["dizi"].lower()==slug.replace("-"," ").title().lower() and e["num"]==num for e in entries):
            continue
        candidates=[
            f"{BASE}/diziler/{slug}/bolum/{num}-bolum",
            f"{BASE}/diziler/{slug}/bolum/{num}-bolum-izle",
            f"{BASE}/diziler/{slug}/{num}-bolum",
        ]
        ok=False
        for url in candidates:
            print(f"  -> {url}")
            m3u8=get_m3u8(url)
            if m3u8 and len(m3u8)>50:
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum","url":m3u8,"num":num,"logo":posters.get(slug,"")})
                print(f"  OK {num}")
                ok=True
                break
            else:
                print(f"  yok")
        if not ok:
            print(f"  BULAMADI {num}")
        time.sleep(0.5)

# son 3'e indir
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

with open(OUTPUT,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x:(x["dizi"], -x["num"])):
        logo=e.get("logo","")
        if logo:
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{GROUP}",{e["dizi"]} - {e["bolum"]}\n#EXTVLCOPT:http-referrer={BASE}/\n{e["url"]}\n\n')
        else:
            f.write(f'#EXTINF:-1 group-title="{GROUP}",{e["dizi"]} - {e["bolum"]}\n#EXTVLCOPT:http-referrer={BASE}/\n{e["url"]}\n\n')

print(f"\n{OUTPUT} -> {len(all_final)} bolum")

if not os.path.exists(MIRTI): open(MIRTI,"w").write("#EXTM3U\n")
with open(MIRTI,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(OUTPUT,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(MIRTI,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")

print(f"mirti68.m3u güncellendi - {len(new)} kayit")
