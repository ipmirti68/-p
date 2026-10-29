import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "ULUSAL"

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

# YEDEK - her zaman var
backup = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "ATV": "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
    "STAR TV": "https://dogus-live.daioncdn.net/startv/startv.m3u8",
    "TV8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
}

final_links = backup.copy()

def get_m3u8(url):
    try:
        h = {"User-Agent": "Mozilla/5.0", "Referer": url}
        r = requests.get(url, headers=h, timeout=12)
        m = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        for link in m:
            if ".m3u8" in link:
                return link.replace("\\/", "/")
    except:
        pass
    return None

# kendi sitelerinden dene, bulursan guncelle
for name, site in [
    ("ATV","https://www.atv.com.tr/canli-yayin"),
    ("STAR TV","https://www.startv.com.tr/canli-yayin"),
    ("TV8","https://www.tv8.com.tr/canli-yayin"),
    ("KANAL D","https://www.kanald.com.tr/canli-yayin"),
    ("SHOW TV","https://www.showtv.com.tr/canli-yayin"),
    ("NOW TV","https://www.nowtv.com.tr/canli-yayin")
]:
    link = get_m3u8(site)
    if link:
        final_links[name] = link
        print("OK " + name + " kendi sitesinden")
    else:
        print("YEDEK " + name)

# ESKI LISTEYI KORU - ULUSAL haric her sey
old_blocks = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
            parts = data.split("#EXTINF")
            for p in parts[1:]:
                # sadece ULUSAL olmayanlari al
                if "ULUSAL" not in p.upper():
                    if "http" in p:
                        old_blocks.append("#EXTINF" + p.strip())
        print("Eski korunan: " + str(len(old_blocks)))
    except Exception as e:
        print("Eski okuma hata: " + str(e))

# YAZ
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    # once 8 ULUSAL
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = final_links.get(name)
        logo = logos.get(name,"")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + name + '\n')
        out.write(url + '\n\n')
    # sonra eski diger kategoriler
    for b in old_blocks:
        out.write(b + '\n\n')

print("Bitti - Toplam ULUSAL 8 + eski " + str(len(old_blocks)))
