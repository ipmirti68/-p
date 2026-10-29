import os
import requests
import re
import json

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# Kendi siteleri
source_urls = {
    "ATV": "https://www.atv.com.tr/canli-yayin",
    "KANAL D": "https://www.kanald.com.tr/canli-yayin",
    "SHOW TV": "https://www.showtv.com.tr/canli-yayin",
    "STAR TV": "https://www.startv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "KANAL 7": "https://www.kanal7.com/canli-izle",
    "TV8": "https://www.tv8.com.tr/canli-yayin",
}

# YEDEK - site vermezse
backup = {
    "ATV": "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "STAR TV": "https://dogus-live.ercdn.net/startv/startv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "TV8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
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

def extract_from_site(page_url, channel_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": page_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9",
    }
    try:
        r = requests.get(page_url, headers=headers, timeout=20)
        txt = r.text

        # 1. Direk m3u8
        m = re.findall(r'https://[^\s\'"<>\\]+\.m3u8[^\s\'"<>\\]*', txt)
        for link in m:
            # reklami at, sadece o kanalin linkini al
            l = link.lower()
            cn = channel_name.lower().replace(" ", "")
            if cn in l or "live" in l or "master" in l:
                if "atv" in l or "kanald" in l or "showtv" in l or "startv" in l or "nowtv" in l or "kanal7" in l or "tv8" in l or "ciner" in l or "dogus" in l or "daion" in l or "cdnvideo" in l:
                    return link.replace("\\/", "/")

        # 2. Escaped m3u8  https:\/\/...
        m2 = re.findall(r'https:\\/\\/[^\s\'"]+\.m3u8[^\s\'"]*', txt)
        if m2:
            link = m2[0].replace("\\/", "/").replace("\\u002F", "/")
            return link.split('"')[0]

        # 3. JSON icinde "hls": "https://..."
        m3 = re.search(r'"(?:hls|file|src|source|videoUrl|liveUrl)"\s*:\s*"(https:[^"]+\.m3u8[^"]*)"', txt)
        if m3:
            return m3.group(1).replace("\\/", "/")

        # 4. window.__DATA__ icinde
        if "atv" in page_url:
            # ATV icin ozel: canli json
            try:
                # bazen ayri api var
                api = "https://www.atv.com.tr/webtv/live"
                ra = requests.get(api, headers=headers, timeout=10)
                ma = re.findall(r'https://[^\s\'"]+\.m3u8[^\s\'"]*', ra.text)
                if ma:
                    return ma[0]
            except:
                pass

    except Exception as e:
        print(f"Hata {channel_name}: {e}")
    return None

# Eski kategorileri koru
old_blocks = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
            parts = data.split("#EXTINF")
            for p in parts[1:]:
                # ULUSAL'i alma, yenileyecegiz
                if "ULUSAL" not in p and "📺" not in p:
                    if "http" in p:
                        old_blocks.append("#EXTINF" + p.strip())
    except:
        pass

print(f"Eski diger kategoriler: {len(old_blocks)}")

# Yeni ULUSAL
new_ul = {}

# TRT1 SABIT - dedigin gibi
new_ul["TRT 1"] = backup["TRT 1"]
print("Sabit: TRT 1 -> master.m3u8")

for name, url in source_urls.items():
    print(f"Cekiliyor {name} sitesinden: {url}")
    found = extract_from_site(url, name)
    if found:
        new_ul[name] = found
        print(f"OK {name} kendi sitesinden: {found[:80]}")
    else:
        new_ul[name] = backup[name]
        print(f"Yedek kullanildi {name}: {backup[name]}")

# Yaz
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for name, m3u8 in new_ul.items():
        logo = logos.get(name, "")
        out.write(f'#EXTINF:-1 tvg-id="{name}" tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        # Referer cok onemli, kendi sitesini ver
        ref_map = {
            "ATV": "https://www.atv.com.tr/",
            "KANAL D": "https://www.kanald.com.tr/",
            "SHOW TV": "https://www.showtv.com.tr/",
            "STAR TV": "https://www.startv.com.tr/",
            "NOW TV": "https://www.nowtv.com.tr/",
            "KANAL 7": "https://www.kanal7.com/",
            "TV8": "https://www.tv8.com.tr/",
            "TRT 1": "https://www.trt1.com.tr/",
        }
        ref = ref_map.get(name, "https://www.google.com/")
        out.write(f'#EXTVLCOPT:http-referrer={ref}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{m3u8}\n\n')
    for b in old_blocks:
        out.write(b + "\n\n")

print(f"Bitti! Toplam yeni {len(new_ul)} ULUSAL + eski {len(old_blocks)}")
