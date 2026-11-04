import os
import re
import html
import requests
from m3u_manager import update_group

OUTPUT_FILE = "mirti68.m3u"
GROUP = "📺 ULUSAL 🔗"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

CHANNELS = {
    "TRT 1": {
        "page": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
        "backup": "https://trt.daioncdn.net/trt-1/master.m3u8?app=web",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png"
    },
    "ATV": {
        "page": "https://www.atv.com.tr/canli-yayin",
        "backup": "https://trkvz.daioncdn.net/atv/atv_1080p.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"
    },
    "KANAL D": {
        "page": "https://www.kanald.com.tr/canli-yayin",
        "backup": "https://demiroren.daioncdn.net/kanald/kanald_1080p.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png"
    },
    "【entity-SHOW TV¦canonical_name=SHOW TV】": {
        "page": "https://www.showtv.com.tr/canli-yayin",
        "backup": "https://ciner.daioncdn.net/showtv/showtv.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png"
    },
    "【entity-STAR TV¦canonical_name=STAR TV】": {
        "page": "https://www.startv.com.tr/canli-yayin",
        "backup": "https://dogus.daioncdn.net/startv/startv_720p.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png"
    },
    "NOW TV": {
        "page": "https://www.nowtv.com.tr/canli-yayin",
        "backup": "https://nowtv-live-ad.ercdn.net/nowtv/nowtv_720p.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png"
    },
    "KANAL 7": {
        "page": "https://www.kanal7.com/canli-izle",
        "backup": "https://kanal7.daioncdn.net/kanal7/kanal7.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png"
    },
    "【entity-TV8¦canonical_name=TV8】": {
        "page": "https://www.tv8.com.tr/canli-yayin",
        "backup": "https://tv8.daioncdn.net/tv8/tv8_1080p.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png"
    }
}

# 【entity-ATV¦canonical_name=ATV】, STAR, 【entity-TV8¦canonical_name=TV8】 kesinlikle yt-dlp istiyor
YTDLP_CHANNELS = {"【entity-ATV¦canonical_name=ATV】", "KANAL D", "【entity-SHOW TV¦canonical_name=SHOW TV】", "【entity-STAR TV¦canonical_name=STAR TV】", "【entity-TV8¦canonical_name=TV8】", "NOW TV"}

session = requests.Session()
session.headers.update(HEADERS)

def valid_m3u8(url):
    if not url or not isinstance(url, str): return False
    url = html.unescape(url.strip())
    if not url.startswith(("http://", "https://")): return False
    if ".m3u8" not in url.lower(): return False
    if " " in url or "[STRIPPED" in url: return False
    return True

def extract_with_ytdlp(page_url):
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "format": "best[protocol^=m3u8]/best",
            "http_headers": {"Referer": page_url, "User-Agent": HEADERS["User-Agent"]},
            # 【entity-atv¦canonical_name=ATV】 ve 【entity-tv8¦canonical_name=TV8】 extractor'ları için
            "extractor_args": {"generic": {"impersonate": ["chrome"]}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            if valid_m3u8(info.get("url","")):
                return info["url"]
            for f in reversed(info.get("formats", [])):
                if valid_m3u8(f.get("url","")):
                    return f["url"]
    except Exception as e:
        print(f"YT-DLP HATASI [{page_url}]: {e}")
    return None

def extract_m3u8(page_url):
    try:
        r = session.get(page_url, timeout=25)
        r.raise_for_status()
        src = html.unescape(r.text).replace("\\/", "/")
        # token'lı linkleri de yakala
        regex = r'https?://[^\s\'"<>\\]+\.m3u8[^\s\'"<>\\]*'
        for m in re.findall(regex, src, re.IGNORECASE):
            m = m.rstrip("\\),;\"'")
            if valid_m3u8(m): return m
    except Exception as e:
        print(f"SAYFA TARAMA HATASI: {e}")
    return None

def read_old_playlist():
    header = "#EXTM3U"
    old_blocks, old_channels = [], {}
    if not os.path.exists(OUTPUT_FILE): return header, old_blocks, old_channels
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8-sig", errors="ignore") as f:
            lines = f.read().splitlines()
        if lines and lines[0].startswith("#EXTM3U"): header = lines[0]
        curr = []
        for line in lines:
            if line.startswith("#EXTM3U"): continue
            if line.startswith("#EXTINF:"):
                if curr: old_blocks.append(curr)
                curr = [line]
            elif curr: curr.append(line)
        if curr: old_blocks.append(curr)
        for block in old_blocks:
            if GROUP not in block[0] or "," not in block[0]: continue
            name = block[0].split(",", 1)[1].strip()
            for l in block[1:]:
                if l.startswith("http") and valid_m3u8(l):
                    old_channels[name] = l.strip(); break
    except Exception as e: print("ESKİ LİSTE HATASI:", e)
    return header, old_blocks, old_channels

def scan_channel(name, info, old_channels):
    print(f"\n{'='*45}\nKANAL: {name}\n{'='*45}")
    fresh = None
    page = info.get("page")

    if page and name in YTDLP_CHANNELS:
        print("YT-DLP deneniyor...")
        fresh = extract_with_ytdlp(page)
        if valid_m3u8(fresh): print("-> YT-DLP BULDU")

    if not valid_m3u8(fresh) and page:
        print("Sayfa taraması...")
        fresh = extract_m3u8(page)
        if valid_m3u8(fresh): print("-> SAYFADAN BULDU")

    if not valid_m3u8(fresh) and valid_m3u8(info.get("backup")):
        fresh = info["backup"]
        print("-> YEDEK KULLANILIYOR")

    if not valid_m3u8(fresh) and valid_m3u8(old_channels.get(name)):
        fresh = old_channels[name]
        print("-> ESKİ ADRES KORUNDU")

    return fresh if valid_m3u8(fresh) else None

def main():
    print("\nMIRTI68 ULUSAL TARAMA BAŞLADI")
    header, old_blocks, old_channels = read_old_playlist()
    new_channels = {}
    for name, info in CHANNELS.items():
        stream = scan_channel(name, info, old_channels)
        if stream: new_channels[name] = stream
        else: print(f"YAYIN BULUNAMADI: {name}")

    preserved = [ "\n".join(b).strip() for b in old_blocks if GROUP not in b[0] ]

    # HATA BURADAYDI: "a" yerine "w" olmalı
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n\n")
        for name, stream in new_channels.items():
            logo = CHANNELS[name].get("logo","")
            page = CHANNELS[name].get("page","")
            f.write(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{GROUP}",{name}\n')
            f.write(f'#EXTVLCOPT:http-referrer={page}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n')
            f.write(f'#EXTHTTP:{{"referer":"{page}"}}\n')
            f.write(stream + "\n\n")
        for block in preserved:
            f.write(block + "\n\n")

    print(f"\nBİTTİ -> Bulunan: {len(new_channels)} | Korunan: {len(preserved)}")

if __name__ == "__main__":
    main()eski kayıt:", len(preserved))
        print("Dosya:", OUTPUT_FILE)
        print("=" * 45)

    except Exception as error:
        print("M3U YAZMA HATASI:", error)


# ==================================================
# BASLAT
# ==================================================

if __name__ == "__main__":
    main()
