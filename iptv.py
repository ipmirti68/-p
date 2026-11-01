import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

source_urls = {
    "【entity-ATV¦canonical_name=ATV】": "https://www.atv.com.tr/canli-yayin",
    "【entity-KANAL D¦canonical_name=KANAL D】": "https://www.kanald.com.tr/canli-yayin",
    "【entity-SHOW TV¦canonical_name=SHOW TV】": "https://www.showtv.com.tr/canli-yayin",
    "【entity-STAR TV¦canonical_name=STAR TV】": "https://www.startv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "【entity-KANAL 7¦canonical_name=KANAL 7】": "https://www.kanal7.com/canli-izle",
    "【entity-TV8¦canonical_name=TV8】": "https://www.tv8.com.tr/canli-yayin",
}

ATV_TAZE = (
    "https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app=d5eb593f-39d9-4b01-9cfd-4748e8332cf0"
    "&st=aHpY5uG0xx5ECKzVhbwyOA&e=1793560183&ppid=b906dadf20123957255ac543c4d7f20e"
    "&dfp_paln=[STRIPPED 67 bytes]"
    "[STRIPPED 1284 bytes]"
)

STAR_TAZE = (
    "https://dogus.daioncdn.net/startv/startv.m3u8?ce=3&app=a20ac41e-bdc3-4aa1-934d-26b484480ac9"
    "&ppid=d8a548868677f2e880c7a220fb574b04"
    "&dfp_paln=[STRIPPED 1420 bytes]"
)

backup = {
    "【entity-ATV¦canonical_name=ATV】": ATV_TAZE,
    "【entity-KANAL D¦canonical_name=KANAL D】": "https://demiroren.daioncdn.net/kanald/kanald.m3u8",
    "【entity-SHOW TV¦canonical_name=SHOW TV】": "https://ciner.daioncdn.net/showtv/showtv.m3u8",
    "【entity-STAR TV¦canonical_name=STAR TV】": STAR_TAZE,
    "NOW TV": "https://nowtv-live-ad.ercdn.net/nowtv/playlist.m3u8",
    "【entity-KANAL 7¦canonical_name=KANAL 7】": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "【entity-TV8¦canonical_name=TV8】": "https://tv8.daioncdn.net/tv8/tv8.m3u8",
    "【entity-TRT 1¦canonical_name=TRT 1】": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
}

logos = {
    "【entity-TRT 1¦canonical_name=TRT 1】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "【entity-ATV¦canonical_name=ATV】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
    "【entity-KANAL D¦canonical_name=KANAL D】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "【entity-SHOW TV¦canonical_name=SHOW TV】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "【entity-STAR TV¦canonical_name=STAR TV】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "【entity-KANAL 7¦canonical_name=KANAL 7】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
    "【entity-TV8¦canonical_name=TV8】": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
}

def extract_with_ytdlp(page_url):
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            if info.get("url") and ".m3u8" in info["url"]:
                return info["url"]
            for f in info.get("formats", [])[::-1]:
                u = f.get("url", "")
                if ".m3u8" in u:
                    return u
    except Exception as e:
        print(f"yt-dlp hata {page_url}: {e}")
    return None

def extract_m3u8(site_url):
    try:
        h = {"User-Agent": "Mozilla/5.0", "Referer": site_url}
        r = requests.get(site_url, headers=h, timeout=15)
        cands = re.findall(r'https://[^\s\'"<>\\]+\.m3u8[^\s\'"<>\\]*', r.text)
        if cands: return cands[0].replace("\\/", "/")
    except: pass
    return None

epg_header = "#EXTM3U"
old_blocks = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            first = content.splitlines()[0] if content else "#EXTM3U"
            if "#EXTM3U" in first: epg_header = first.strip()
            for p in content.split("#EXTINF")[1:]:
                block = "#EXTINF" + p.strip()
                if YENI_GRUP in block: continue
                if "http" in block: old_blocks.append(block)
    except: pass

print(f"Eski korunan: {len(old_blocks)}")
new_ul = {"【entity-TRT 1¦canonical_name=TRT 1】": backup["【entity-TRT 1¦canonical_name=TRT 1】"]}

for name, url in source_urls.items():
    print(f"\nDeniyor {name}: {url}")
    fresh = None
    if name in ["【entity-ATV¦canonical_name=ATV】", "【entity-STAR TV¦canonical_name=STAR TV】", "【entity-SHOW TV¦canonical_name=SHOW TV】", "【entity-KANAL D¦canonical_name=KANAL D】"]:
        fresh = extract_with_ytdlp(url)
        if fresh: print(f"  -> YT-DLP TAZE {name}")
    if not fresh:
        fresh = extract_m3u8(url)
        if fresh: print(f"  -> SCRAPE TAZE {name}")
    if fresh and ".m3u8" in fresh:
        new_ul[name] = fresh
    else:
        new_ul[name] = backup.get(name, "")
        print(f"  -> YEDEK {name}")

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for name in ["【entity-TRT 1¦canonical_name=TRT 1】","【entity-ATV¦canonical_name=ATV】","【entity-KANAL D¦canonical_name=KANAL D】","【entity-SHOW TV¦canonical_name=SHOW TV】","【entity-STAR TV¦canonical_name=STAR TV】","NOW TV","【entity-KANAL 7¦canonical_name=KANAL 7】","【entity-TV8¦canonical_name=TV8】"]:
        m3u8 = new_ul.get(name, backup.get(name))
        logo = logos.get(name, "")
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'#EXTVLCOPT:http-referrer=https://www.google.com/\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{m3u8}\n\n')
    for b in old_blocks:
        out.write(b + "\n\n")

print("\nBitti - ULUSAL yt-dlp ile olustu")
