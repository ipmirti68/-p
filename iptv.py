import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# Calisanlar - bunlar guncellenecek
guncellenecek_siteler = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "KANAL D": "https://www.kanald.com.tr/canli-yayin",
    "SHOW TV": "https://www.showtv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "KANAL 7": "https://www.kanal7.com/canli-izle",
}

backup = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
}

def get_m3u8_from_site(url):
    try:
        h = {"User-Agent": "Mozilla/5.0", "Referer": url}
        r = requests.get(url, headers=h, timeout=12)
        m = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        if m:
            return m[0].replace("\\/", "/")
    except:
        pass
    return None

# 1- ESKI DOSYAYI OKU, EPG VE TUM KANALLARI KORU
epg_header = "#EXTM3U"
old_blocks = []
korunacak_atv_star_tv8 = {}  # ATV STAR TV8 eski halleri

if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.splitlines()
            if lines and "url-tvg" in lines[0].lower() or "x-tvg-url" in lines[0].lower() or 'tvg' in lines[0].lower():
                epg_header = lines[0].strip()  # EPG satirini koru
                print("EPG korundu: " + epg_header[:100])

            parts = content.split("#EXTINF")
            for p in parts[1:]:
                block = "#EXTINF" + p.strip()
                # 📺 ULUSAL 🔗 grubundakileri alma, yenileyecegiz
                if "ULUSAL" in block or "📺" in block:
                    continue
                # ATV STAR TV8'i ayri sakla, silme
                upper = block.upper()
                if ",ATV" in upper or "ATV" in block and 'group-title' in block:
                    if "ATV" in block.split(",")[-1].upper():
                        korunacak_atv_star_tv8["ATV"] = block
                        continue
                if "STAR TV" in upper:
                    korunacak_atv_star_tv8["STAR TV"] = block
                    continue
                if ",TV8" in upper or "TV8" in block.split(",")[-1].upper():
                    korunacak_atv_star_tv8["TV8"] = block
                    continue
                if "http" in block:
                   
