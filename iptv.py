import os
import requests
import re

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

# DAHA ONCE CALISAN - geri getiriyoruz
coklu_yedek = {
    "ATV": [
        "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
        "https://ciner-live.ercdn.net/atv/atv.m3u8",
        "https://trn03.tulpar.uk/atv.m3u8"
    ],
    "STAR TV": [
        "https://dogus-live.daioncdn.net/startv/startv.m3u8",
        "https://dogus-live.ercdn.net/startv/startv.m3u8",
        "https://trn03.tulpar.uk/startv.m3u8"
    ],
    "TV8": [
        "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
        "https://tv8-live.daioncdn.net/tv8/tv8.m3u8",
        "https://trn03.tulpar.uk/tv8.m3u8"
    ],
    "TRT 1": ["https://tv-trt1.medya.trt.com.tr/master.m3u8"],
    "KANAL D": ["https://ciner-live.ercdn.net/kanald/kanald.m3u8"],
    "SHOW TV": ["https://ciner-live.ercdn.net/showtv/showtv.m3u8"],
    "NOW TV": ["https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8"],
    "KANAL 7": ["https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8"],
}

def calisan_link_bul(liste):
    for url in liste:
        try:
            r = requests.head(url, timeout=5, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code == 200:
                return url
            # head engelliyse get ile dene
            r2 = requests.get(url, timeout=5, headers={"User-Agent":"Mozilla/5.0"}, stream=True)
            if r2.status_code == 200 and "m3u8" in r2.text[:1000].lower() or r2.status_code == 200:
                return url
        except:
            continue
    return liste[0]  # hicbiri olmasa ilkini ver, player denesin

# EPG ve eski liste koruma
epg_header = "#EXTM3U"
old_blocks = []
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first = content.splitlines()[0] if content else "#EXTM3U"
        if "url-tvg" in first.lower() or "tvg-url" in first.lower() or len(first) > 10:
            if "#EXTM3U" in first:
                epg_header = first.strip()
        parts = content.split("#EXTINF")
        for p in parts[1:]:
            block = "#EXTINF" + p.strip()
            if YENI_GRUP in block:
                continue
            if "http" in block:
                old_blocks.append(block)

final_links = {}
for name, liste in coklu_yedek.items():
    link = calisan_link_bul(liste)
    final_links[name] = link
    print(name + " -> " + link)

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    # 8'li ULUSAL - hepsi geri geldi
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = final_links.get(name)
        logo = logos.get(name,"")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + name + '\n')
        out.write(url + '\n\n')
    # eski liste korunuyor - ama ULUSAL olmayanlar
    for b in old_blocks:
        # eski ULUSAL olmayan ATV STAR TV8 tekrar etmesin diye filtrele
        up = b.upper()
        if any(x in up for x in ["TRT 1","KANAL D","SHOW TV","NOW TV","KANAL 7"]):
            # bu isimler zaten yeni grupta, eski kopyayi at
