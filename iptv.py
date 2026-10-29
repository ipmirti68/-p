import os
import requests

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

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

# DAHA ONCE CALISAN LINKLER - ATV STAR geri gelecek
links = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "ATV": "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "STAR TV": "https://dogus-live.daioncdn.net/startv/startv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "TV8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
}

epg_header = "#EXTM3U"
old_blocks = []

if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first = content.splitlines()[0] if content else "#EXTM3U"
        if "url-tvg" in first.lower() or "#EXTM3U" in first:
            if len(first.strip()) > 7:
                epg_header = first.strip()
        parts = content.split("#EXTINF")
        for p in parts[1:]:
            block = "#EXTINF" + p.strip()
            if YENI_GRUP in block:
                continue
            if "http" in block:
                old_blocks.append(block)

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = links.get(name)
        logo = logos.get(name,"")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + name + '\n')
        out.write(url + '\n\n')
    for b in old_blocks:
        out.write(b + '\n\n')

print("Bitti - 8 kanal ULUSAL grubunda, EPG korundu")
