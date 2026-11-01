import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

source_urls = {
    "【entity-ATV¦canonical_name=ATV】": "https://www.atv.com.tr/canli-yayin",
    "【entity-KANAL D¦canonical_name=KANAL D】": "https://www.kanald.com.tr/canli-yayin",
    "SHOW TV": "https://www.showtv.com.tr/canli-yayin",
    "STAR TV": "https://www.startv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "KANAL 7": "https://www.kanal7.com/canli-izle",
    "【entity-TV8¦canonical_name=TV8】": "https://www.tv8.com.tr/canli-yayin",
}

backup = {
    "【entity-ATV¦canonical_name=ATV】": "https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app=d5eb593f-39d9-4b01-9cfd-4748e8332cf0&st=DEuWHVDFai9dO1g8iqkc0A&e=1793322513&ppid=3bcab250e6c871de99a1664e01d1966e",
    "KANAL D": "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3&ppid=f9fbf59814ca71a045d91069567bc196",
    "SHOW TV": "https://ciner.daioncdn.net/showtv/showtv.m3u8?ce=3&app=4bc856ef-4c68-4a94-bc87-37dfaaa66558&st=RBzhSuGauna0OGld-DJUVA&e=1664766175&tv=1nov",
    "STAR TV": "https://dogus.daioncdn.net/startv/startv.m3u8?ce=3&app=a20ac41e-bdc3-4aa1-934d-26b484480ac9&ppid=f707dc99c764a453381be07886dd1b57",
    "NOW TV": "https://nowtv-live-ad.ercdn.net/nowtv/playlist.m3u8?st=70w5DbQKtpXA39iFdH8w-g&e=1793292773",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "【entity-TV8¦canonical_name=TV8】": "https://tv8.daioncdn.net/tv8/tv8.m3u8?app=7ddc255a-ef47-4e81-ab14-c0e5f2949788&ce=3&ppid=2fa25e38651fb8e365593e24038bcaba",
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
    "【entity-TV8¦canonical_name=TV8】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
}

def extract_m3u8(site_url):
    try:
        sess = requests.Session()
        h = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Referer": site_url,
            "Accept-Language": "tr-TR,tr;q=0.9"
        }
        r = sess.get(site_url, headers=h, timeout=20)
        txt = r.text

        # 1. iframe varsa içine gir - ATV, NOW, 【entity-TV8¦canonical_name=TV8】 genelde burada
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', txt, re.I)
        for ifr in iframes:
            if ifr.startswith("//"):
                ifr = "https:" + ifr
            elif ifr.startswith("/"):
                ifr = "https://" + site_url.split("/")[2] + ifr
            try:
                r2 = sess.get(ifr, headers=h, timeout=15)
                txt += "\n" + r2.text
            except:
                pass

        # 2. tum m3u8 patternleri
        patterns = [
            r'https://[^\s\'"<>\\]+\.m3u8[^\s\'"<>\\]*',
            r'https:\\/\\/[^"\']+\.m3u8[^"\']*',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"src"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'source\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'file:\s*"([^"]+\.m3u8[^"]*)"',
        ]
        candidates = []
        for pat in patterns:
            candidates += re.findall(pat, txt)

        cleaned = []
        for c in candidates:
            c = c.replace("\\/", "/").replace("\\u002F", "/").replace("\\", "")
            c = c.split('"')[0].split("'")[0].strip()
            if ".m3u8" in c and "http" in c:
                cleaned.append(c)

        # 3. en alakalıyı seç
        for link in cleaned:
            low = link.lower()
            if any(x in low for x in ["atv","kanald","showtv","startv","nowtv","kanal7","tv8","daion","ercdn","trt"]):
                return link
        
        if cleaned:
            return cleaned[0]

    except Exception as e:
        print(f"Hata {site_url}: {e}")
    return None

# ESKI LISTEYI KORU - SADECE ULUSAL GRUBU SIL
epg_header = "#EXTM3U"
old_blocks = []
if os.path.exists(output_file):
    try:
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
    except:
        pass

print(f"Eski korunan blok: {len(old_blocks)}")

new_ul = {}
new_ul["TRT 1"] = backup["TRT 1"]

for name, url in source_urls.items():
    print(f"Deniyor {name}: {url}")
    fresh = extract_m3u8(url)
    if fresh and ".m3u8" in fresh:
        new_ul[name] = fresh
        print(f"  -> TAZE: {fresh[:120]}")
    else:
        new_ul[name] = backup[name]
        print(f"  -> YEDEK: {backup[name][:120]}")

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        m3u8 = new_ul.get(name, backup.get(name))
        logo = logos.get(name, "")
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
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'#EXTVLCOPT:http-referrer={ref}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{m3u8}\n\n')
    for b in old_blocks:
        out.write(b + "\n\n")

print("Bitti - ULUSAL oluştu")
