import os
import requests
import re

channel_info = {
    "atv": ["ATV.hd", "ATV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "ULUSAL", "ATV"],
    "kanald": ["Kanal.D.hd", "Kanal D.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "ULUSAL", "Kanal D"],
    "showtv": ["Show.TV.hd", "Show TV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "ULUSAL", "Show TV"],
    "startv": ["Star.TV.hd", "Star TV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "ULUSAL", "Star TV"],
    "nowtv": ["NOW.TV.hd", "NOW TV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "ULUSAL", "NOW TV"],
    "kanal7": ["Kanal.7.hd", "Kanal 7.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "ULUSAL", "Kanal 7"],
    "tv8": ["TV8.hd", "TV8.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "ULUSAL", "TV8"],
    "trt1": ["TRT.1.hd", "TRT 1.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "ULUSAL", "TRT 1"],
}

source_urls = {
    "atv": "https://www.atv.com.tr/canli-yayin",
    "kanald": "https://www.kanald.com.tr/canli-yayin",
    "showtv": "https://www.showtv.com.tr/canli-yayin",
    "startv": "https://www.startv.com.tr/canli-yayin",
    "nowtv": "https://www.nowtv.com.tr/canli-yayin",
    "kanal7": "https://www.kanal7.com/canli-izle",
    "tv8": "https://www.tv8.com.tr/canli-yayin",
    "trt1": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
}

def extract_m3u8(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=15, headers=headers)
        m = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', r.text)
        if m:
            m.sort(key=len, reverse=True)
            return m[0]
    except:
        pass
    return None

output_file = "mirti68.m3u"

old_channels = {}
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                if i+1 < len(lines):
                    link = lines[i+1].strip()
                    if link.startswith("http"):
                        old_channels[lines[i].strip()] = link

updated = {}
for name, page_url in source_urls.items():
    print("Kontrol: " + name)
    m3u8_link = extract_m3u8(page_url)
    if name == "trt1" and not m3u8_link:
        m3u8_link = "https://tv-trt1.medya.trt.com.tr/master.m3u8"
    if m3u8_link:
        info = channel_info[name]
        extinf = '#EXTINF:-1 tvg-id="' + info[0] + '" tvg-name="' + info[1] + '" tvg-logo="' + info[2] + '" group-title="' + info[3] + '",' + info[4]
        updated[extinf] = m3u8_link
        print("OK: " + info[4])

final_list = old_channels.copy()
final_list.update(updated)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for extinf, link in final_list.items():
        out.write(extinf + "\n")
        out.write(link + "\n\n")

print("Bitti! Toplam kanal: " + str(len(final_list)))
