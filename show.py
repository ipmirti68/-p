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

def get_m3u8_yt(url):
    if any(x in url.lower() for x in ["fragman","galeri","fotograf"]): return None
    try:
        import yt_dlp
        ydl_opts={"quiet":True,"no_warnings":True,"skip_download":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u and "vmcdn" in u:
                    return u
    except: return None
    return None

def get_flat(slug):
    try:
        import yt_dlp
        url=f"{site}/dizi/{slug}"
        ydl_opts={"quiet":True,"skip_download":True,"extract_flat":"in_playlist"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
            return info.get("entries",[])[-3:]
    except: return []

# MANUEL TAZE - senin verdiğin hep kalacak
MANUEL={
    "sevdan-bir-ates": [{"num":8, "url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392"}]
}

slugs=["kizilcik-serbeti","sevdan-bir-ates","muhtemel-ask","menekse"]
entries=[]
posters={slug:get_poster(slug) for slug in slugs}

for slug, items in MANUEL.items():
    for it in items:
        entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{it['num']}. Bolum","url":it["url"],"num":it["num"],"logo":posters.get(slug,"")})

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    flat=get_flat(slug)
    print(f"  flat {len(flat)} bulundu")
    for ent in flat:
        url=ent.get("url") or ent.get("webpage_url") or ""
        if not url or "fragman" in url.lower(): continue
        mm=re.search(r'(\d+)[^0-9]*bolum', url.lower())
        num=int(mm.group(1)) if mm else 0
        if any(e["num"]==num and slug in e["dizi"].lower() for e in entries): continue
        print(f"  -> {url}")
        m3u8=get_m3u8_yt(url)
        if m3u8:
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum" if num else "Bolum","url":m3u8,"num":num,"logo":posters.get(slug,"")})
            print(f"  OK {num}")

# fallback numara deneme
LAST={"kizilcik-serbeti":145,"sevdan-bir-ates":8,"muhtemel-ask":10,"menekse":5}
for slug,last in LAST.items():
    for num in range(last, last-2, -1):
        if any(e["num"]==num and slug.replace("-"," ").title().lower() in e["dizi"].lower() for e in entries): continue
        for cand in [f"{site}/dizi/{slug}/bolum/{num}-bolum", f"{site}/dizi/{slug}/bolum/{num}-bolum-izle"]:
            m3u8=get_m3u8_yt(cand)
            if m3u8:
                entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum","url":m3u8,"num":num,"logo":posters.get(slug,"")})
                print(f"  FALLBACK OK {slug} {num}")
                break

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

# YAZ - kanal önüne SHOW - ve logo
with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x:(x["dizi"], -x["num"])):
        logo=e.get("logo","")
        dizi=e["dizi"]
        # kanal önüne SHOW - ekle
        if logo:
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{GROUP}",TR: SHOW - {e["bolum"]} - {dizi}\n{e["url"]}\n\n')
        else:
            f.write(f'#EXTINF:-1 group-title="{GROUP}",TR: SHOW - {e["bolum"]} - {dizi}\n{e["url"]}\n\n')

print(f"\n{m3u_file} -> {len(all_final)} bolum (otomatik + poster)")

if not os.path.exists(mirti_file): open(mirti_file,"w").write("#EXTM3U\n")
with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")

print(f"mirti68.m3u güncellendi - {len(new)} kayıt, otomatik")
