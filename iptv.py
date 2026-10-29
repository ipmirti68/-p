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

def get_m3u8(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": url}
        r = requests.get(url, headers=headers, timeout=15)
        m = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        if m:
            return m[0].replace("\\/", "/")
    except:
        pass
    return None

# Sabit yedekler - ATV STAR TV8 kesin gelecek
final_links = {}
final_links["TRT 1"] = "https://tv-trt1.medya.trt.com.tr/master.m3u8"
final_links["KANAL 7"] = "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8"
final_links["ATV"] = "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8"
final_links["STAR TV"] = "https://dogus-live.daioncdn.net/startv/startv.m3u8"
final_links["TV8"] = "https://tv8-live.ercdn.net/tv8/tv8.m3u8"

# Digerlerini sitesinden dene
sites = {
    "KANAL D": "https://www.kanald.com.tr/canli-yayin",
    "SHOW TV": "https://www.showtv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
}
backup_other = {
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
}

for name, site in sites.items():
    link = get_m3u8(site)
    if link:
        final_links[name] = link
        print("OK " + name)
    else:
        final_links[name] = backup_other[name]
        print("YEDEK " + name)

# Kendi sitelerinden ATV STAR TV8 icin de dene
atv_link = get_m3u8("https://www.atv.com.tr/canli-yayin")
if atv_link:
    final_links["ATV"] = atv_link
    print("ATV kendi sitesinden")

star_link = get_m3u8("https://www.startv.com.tr/canli-yayin")
if star_link:
    final_links["STAR TV"] = star_link
    print("STAR kendi sitesinden")

tv8_link = get_m3u8("https://www.tv8.com.tr/canli-yayin")
if tv8_link:
    final_links["TV8
