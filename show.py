import os, re, time
m3u="showtv.m3u"
mirti="mirti68.m3u"
GROUP="SHOW Dizileri"
BASE="https://www.showtv.com.tr"

def get_m3u8(full_url):
    if any(x in full_url.lower() for x in ["fragman","galeri"]): return None
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True}) as ydl:
            info=ydl.extract_info(full_url, download=False)
            for f in info.get("formats",[])[::-1]:
                u=f.get("url","")
                if ".m3u8" in u and "vmcdn" in u:
                    return u
    except Exception as e:
        print(f"  yt-dlp hata {full_url[-30:]}: {e}")
    return None

LAST={"kizilcik-serbeti":145,"sevdan-bir-ates":8,"muhtemel-ask":10,"menekse":5}
entries=[]

# Senin taze manuel hep dursun - otomatik bulamazsa bile 1 tane kalır
MANUEL_URL="https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392"
entries.append(("Sevdan-Bir-Ates",8,MANUEL_URL))
print(f"MANUEL 8 eklendi")

for slug,last in LAST.items():
    if slug=="sevdan-bir-ates": last=7 # 8 manuel var, 7,6 dene
    print(f"\n=== {slug} ===")
    for num in range(last, last-2, -1):
        url=f"{BASE}/dizi/{slug}/bolum/{num}-bolum"
        print(f"  -> {url}")
        m3u8=get_m3u8(url)
        if m3u8:
            entries.append((slug.replace("-"," ").title(),num,m3u8))
            print(f"  OK {num}")
        else:
            url2=f"{BASE}/dizi/{slug}/bolum/{num}-bolum-izle"
            m3u8=get_m3u8(url2)
            if m3u8:
                entries.append((slug.replace("-"," ").title(),num,m3u8))
                print(f"  OK {num} (izle)")
        time.sleep(0.5)

# tekilleştir son 3
uniq={}
for d,n,u in entries:
    k=f"{d.lower()}_{n}"
    if k not in uniq: uniq[k]=(d,n,u)

with open(m3u,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for d,n,u in sorted(uniq.values(), key=lambda x:(x[0],-x[1])):
        f.write(f'#EXTINF:-1 group-title="{GROUP}",TR: SHOW - {n}. Bolum - {d}\n{u}\n\n')

if not os.path.exists(mirti): open(mirti,"w").write("#EXTM3U\n")
with open(mirti,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(m3u,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(mirti,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")
print(f"SHOW {len(new)} bolum")
