import os, subprocess

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# YouTube 7/24 canli - token istemez, hep acik
yt_sources = {
    "ATV": "https://www.youtube.com/@atvturkiye/live",
    "KANAL D": "https://www.youtube.com/@kanald/live",
    "SHOW TV": "https://www.youtube.com/@ShowTV/live",
    "STAR TV": "https://www.youtube.com/@startv/live",
    "NOW TV": "https://www.youtube.com/@nowtvturkiye/live",
    "TV8": "https://www.youtube.com/@tv8/live",
    # Bunlar zaten saglam
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "ATV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "STAR TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
    "TV8": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
}

def get_m3u8(url):
    try:
        r = subprocess.run(
            ["yt-dlp", "--get-url", "-f", "best", "--no-warnings", url],
            capture_output=True, text=True, timeout=30
        )
        out = r.stdout.strip().split("\n")[0]
        if "m3u8" in out or "googlevideo" in out:
            return out
    except Exception as e:
        print(f"Hata {url}: {e}")
    return None

yeni_linkler = {}
for name, src in yt_sources.items():
    if src.endswith(".m3u8"):
        yeni_linkler[name] = src
        print(f"Sabit: {name}")
    else:
        print(f"YouTube'dan cekiliyor: {name}")
        link = get_m3u8(src)
        if link:
            yeni_linkler[name] = link
            print(f"OK {name}")
        else:
            # YouTube canli bulamazsa direk youtube linkini birak, TiviMate yt-dlp ile acar
            yeni_linkler[name] = src
            print(f"YouTube linki direk birakildi {name}")

# Eski listeyi koru
lines=[]
if os.path.exists(output_file):
    with open(output_file,"r",encoding="utf-8",errors="ignore") as f:
        lines=f.readlines()
old={}
i=0
while i < len(lines):
    if lines[i].startswith("#EXTINF"):
        ext=lines[i].strip()
        j=i+1
        while j < len(lines) and lines[j].startswith("#EXTVLCOPT"):
            j+=1
        url = lines[j].strip() if j < len(lines) else ""
        name = ext.split(",")[-1].strip().upper()
        if name not in [k.upper() for k in yeni_linkler.keys()]:
            old[name]=[ext,url]
        i=j+1
    else:
        i+=1

with open(output_file,"w",encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for name, url in yeni_linkler.items():
        logo = logos.get(name,"")
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'{url}\n\n')
    for ext,url in old.values():
        out.write(ext+"\n"+url+"\n\n")

print(f"Bitti toplam {len(old)+len(yeni_linkler)} kanal")
