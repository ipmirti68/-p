import os, subprocess, json

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# yt-dlp ile alinacak siteler - tokenli linki cozer
yt_sources = {
    "ATV": "https://www.atv.com.tr/canli-yayin",
    "KANAL D": "https://www.kanald.com.tr/canli-yayin",
    "SHOW TV": "https://www.showtv.com.tr/canli-yayin",
    "STAR TV": "https://www.startv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "TV8": "https://www.tv8.com.tr/canli-yayin",
    # TRT1 ve KANAL 7 zaten acik, direk link
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
        # yt-dlp direk m3u8 linkini veriyor
        result = subprocess.run(
            ["yt-dlp", "--get-url", "--no-warnings", url],
            capture_output=True, text=True, timeout=30
        )
        out = result.stdout.strip().split("\n")[0]
        if ".m3u8" in out:
            return out
    except Exception as e:
        print(f"yt-dlp hata {url}: {e}")
    return None

# yeni linkleri cek
yeni_linkler = {}
for name, src in yt_sources.items():
    if src.endswith(".m3u8"):
        yeni_linkler[name] = src
        print(f"Sabit: {name}")
    else:
        print(f"yt-dlp ile aliniyor: {name} -> {src}")
        link = get_m3u8(src)
        if link:
            yeni_linkler[name] = link
            print(f"OK {name}: {link[:70]}")
        else:
            # yedek ercdn
            yeni_linkler[name] = f"https://ciner-live.ercdn.net/{name.lower().replace(' ','')}/{name.lower().replace(' ','')}.m3u8"
            print(f"Yedek kullanildi {name}")

# eski listeyi oku
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
        ref_map = {
            "ATV": "https://www.atv.com.tr/",
            "KANAL D": "https://www.kanald.com.tr/",
            "SHOW TV": "https://www.showtv.com.tr/",
            "STAR TV": "https://www.startv.com.tr/",
            "NOW TV": "https://www.nowtv.com.tr/",
            "TV8": "https://www.tv8.com.tr/",
            "TRT 1": "https://www.trt1.com.tr/",
            "KANAL 7": "https://www.kanal7.com/",
        }
        ref = ref_map.get(name,"")
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        if ref:
            out.write(f'#EXTVLCOPT:http-referrer={ref}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{url}\n\n')
    for ext,url in old.values():
        out.write(ext+"\n"+url+"\n\n")

print(f"Bitti toplam {len(old)+len(yeni_linkler)} kanal")
