import os
import requests
import re

channel_info = {
    "trt1": {"tvg_id": "TRT.1.hd", "tvg_name": "TRT 1.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "group": "📺 ULUSAL.", "name": "TRT 1"},
    "atv": {"tvg_id": "ATV.hd", "tvg_name": "ATV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "group": "📺 ULUSAL.", "name": "ATV"},
    "kanald": {"tvg_id": "Kanal.D.hd", "tvg_name": "Kanal D.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "group": "📺 ULUSAL.", "name": "Kanal D"},
    "showtv": {"tvg_id": "Show.TV.hd", "tvg_name": "Show TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "group": "📺 ULUSAL.", "name": "Show TV"},
    # EKLENECEKLER
    "startv": {"tvg_id": "Star.TV.hd", "tvg_name": "Star TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "group": "📺 ULUSAL.", "name": "Star TV"},
    "nowtv": {"tvg_id": "NOW.TV.hd", "tvg_name": "NOW TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "group": "📺 ULUSAL.", "name": "NOW TV"},
    "kanal7": {"tvg_id": "Kanal.7.hd", "tvg_name": "Kanal 7.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "group": "📺 ULUSAL.", "name": "Kanal 7"},
    "tv8": {"tvg_id": "TV8.hd", "tvg_name": "TV8.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "group": "📺 ULUSAL.", "name": "TV8"},
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
        headers = {"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"}
        r = requests.get(url, timeout=15, headers=headers)
        m = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', r.text)
        if m:
            # En uzun link genelde master oluyor
            m = sorted(m, key=len, reverse=True)
            return m[0]
    except Exception as e:
        print(f"hata {url}: {e}")
    return None

output_file = "mirti68.m3u"

# 1. MEVCUT LİSTEYİ KORU
old_channels = {}
if os.path.exists(output_file):
    print(f"[>] Mevcut liste korunuyor...")
    with open(output_file,
