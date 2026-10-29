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

# HER KANAL ICIN 3 YEDEK - biri olmezse digeri
kaynaklar = {
    "TRT 1": [
        "https://tv-trt1.medya.trt.com.tr/master.m3u8",
        "https://trt.daioncdn.net/trt-1/master.m3u8"
    ],
    "ATV": [
        "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
        "https://ciner-live.ercdn.net/atv/atv.m3u8",
        "https://trn03.tulpar.uk/atv.m3u8"
    ],
    "KANAL D": [
        "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
        "https://kanal-d.daioncdn.net/kanal-d/master.m3u8",
        "https://trn03.tulpar.uk/kanald.m3u8"
    ],
    "SHOW TV": [
        "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
        "https://show-tv.daioncdn.net/show-tv/master.m3u8",
        "https://trn03.tulpar.uk/showtv.m3u8"
    ],
    "STAR TV": [
        "https://dogus-live.daioncdn.net/startv/startv.m3u8",
        "https://dogus-live.ercdn.net/startv/startv.m3u8",
        "https://trn03.tulpar.uk/startv.m3u8"
    ],
    "NOW TV": [
        "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
        "https://now-tv.daioncdn.net/now-tv/master.m3u8",
        "https://trn03.tulpar.uk/nowtv.m3u8"
    ],
    "KANAL 7": [
        "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
        "https://kanal7.daioncdn.net/kanal7/master.m3u8"
    ],
    "TV8": [
        "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
        "https://tv8-live.daioncdn.net/tv8/tv8.m3u8",
        "https://trn03.tulpar.uk/tv8.m3u8"
    ]
}

def en_iyi_link(bul_list):
    for url in bul_list:
        try:
            r = requests.head(url, timeout=6, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"})
            if r.status_code == 200:
                return url
        except:
            pass
        try:
            r = requests.get(url, timeout=6, headers={"User-Agent":"Mozilla/5.0"}, stream=True)
            if r.status_code == 200:
                return url
        except:
            pass
    return bul_list[0]

# EPG ve eski liste
epg_header = "#EXTM3U"
old_blocks = []
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first = content.splitlines()[0] if content else "#EXTM3U"
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
for isim, liste in kaynaklar.items():
    link = en_iyi_link(liste)
    final_links[isim] = link
    print(isim + " -> " + link)

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for isim in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = final_links.get(isim)
        logo = logos.get(isim,"")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + isim + '\n')
        out.write(url + '\n\n')
    for b in old_blocks:
        out.write(b + '\n\n')

print("Bitti - 8 kanal denendi")
