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

final_links = {}
final_links["TRT 1"] = "https://tv-trt1.medya.trt.com.tr/master.m3u8"
final_links["KANAL 7"] = "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8"
final_links["ATV"] = "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8"
final_links["STAR TV"] = "https://dogus-live.daioncdn.net/startv/startv.m3u8"
final_links["TV8"] = "https://tv8-live.ercdn.net/tv8/tv8.m3u8"
final_links["KANAL D"] = "https://ciner-live.ercdn.net/kanald/kanald.m3u8"
final_links["SHOW TV"] = "https://ciner-live.ercdn.net/showtv/showtv.m3u8"
final_links["NOW TV"] = "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8"

def get_m3u8(url):
    try:
        h = {"User-Agent": "Mozilla/5.0", "Referer": url}
        r = requests.get(url, headers=h, timeout=10)
        m = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        if m:
            return m[0].replace("\\/", "/")
    except:
        pass
    return None

for name, site in [("ATV","https://www.atv.com.tr/canli-yayin"),("STAR TV","https://www.startv.com.tr/canli-yayin"),("TV8","https://www.tv8.com.tr/canli-yayin")]:
    link = get_m3u8(site)
    if link:
        final_links[name] = link
        print("OK " + name + " kendi sitesinden")

with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = final_links.get(name)
        logo = logos.get(name,"")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + name + '\n')
        out.write(url + '\n\n')

print("Bitti")
