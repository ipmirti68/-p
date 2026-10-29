import os
import requests
import re
import json

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

# GARANTI YEDEK LINKLER - bulamazsa bunlar girer, liste bos kalmaz
fallback_links = {
    "atv": "https://trkvz-live.ercdn.net/atv/atv.m3u8",
    "kanald": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "showtv": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "startv": "https://dogus-live.ercdn.net/startv/startv.m3u8",
    "nowtv": "https://foxnow-live.ercdn.net/nowtv/nowtv.m3u8",
    "kanal7": "https://kanal7-live.ercdn.net/kanal7/kanal7.m3u8",
    "tv8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
    "trt1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
}

def extract_m3u8(name, url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": url
        }
        r = requests.get(url, timeout=15, headers=headers)
        text = r.text

        # 1. Genel m3u8 ara
        m = re.findall(r'https?://[^\s\'"\\]+\.m3u8[^\s\'"\\]*', text)
        # unescape
        cleaned = []
        for link in m:
            link = link.replace("\\u002F", "/").replace("\\/", "/")
            if "master" in link or "index" in link or name in link.lower() or "live" in link:
                cleaned.append(link)
        
        if cleaned:
            cleaned.sort(key=len, reverse=True)
            # ATV icin en alakali olani sec
            for c in cleaned:
                if name in c.lower() or "atv" in c.lower() or "tv8" in c.lower():
                    return c
            return cleaned[0]

        # 2. JSON icinde ara (atv.com.tr icin)
        m2 = re.findall(r'"videoUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"', text)
        if m2:
            return m2[0].replace("\\/", "/")

        m3 = re.findall(r'"hlsUrl"\s*:\s*"([^"]+)"', text)
        if m3:
            return m3[0]

    except Exception as e:
        print(f"Hata {name}: {e}")
    
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
for name, page_url in {
    "atv": "https://www.atv.com.tr/canli-yayin",
    "kanald": "https://www.kanald.com.tr/canli-yayin",
    "showtv": "https://www.showtv.com.tr/canli-yayin",
    "startv": "https://www.startv.com.tr/canli-yayin",
    "nowtv": "https://www.nowtv.com.tr/canli-yayin",
    "kanal7": "https://www.kanal7.com/canli-izle",
    "tv8": "https://www.tv8.com.tr/canli-yayin",
    "trt1": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
}.items():
    print("Kontrol: " + name)
    link = extract_m3u8(name, page_url)
    
    if not link:
        print(f"Bulunamadi, yedek kullaniliyor: {name}")
        link = fallback_links.get(name)

    if link:
        info = channel_info[name]
        extinf = '#EXTINF:-1 tvg-id="' + info[0] + '" tvg-name="' + info[1] + '" tvg-logo="' + info[2] + '" group-title="' + info[3] + '",' + info[4]
        updated[extinf] = link
        print("OK: " + info[4] + " -> " + link[:60])

final_list = old_channels.copy()
final_list.update(updated)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for extinf, link in final_list.items():
        out.write(extinf + "\n")
        out.write(link + "\n\n")

print("Bitti! Toplam: " + str(len(final_list)))
