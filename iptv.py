import os
import re
import html
import requests

OUTPUT_FILE = "mirti68.m3u"
GROUP = "📺 ULUSAL 🔗"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
}

CHANNELS = {
    "TRT 1": {"page": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002", "backup": "https://trt.daioncdn.net/trt-1/master.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png"},
    "ATV": {"page": "https://www.atv.com.tr/canli-yayin", "backup": "https://trkvz.daioncdn.net/atv/atv_1080p.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"},
    "KANAL D": {"page": "https://www.kanald.com.tr/canli-yayin", "backup": "https://demiroren.daioncdn.net/kanald/kanald_1080p.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png"},
    "【entity-SHOW TV¦canonical_name=SHOW TV】": {"page": "https://www.showtv.com.tr/canli-yayin", "backup": "https://ciner.daioncdn.net/showtv/showtv.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png"},
    "【entity-STAR TV¦canonical_name=STAR TV】": {"page": "https://www.startv.com.tr/canli-yayin", "backup": "https://dogus.daioncdn.net/startv/startv_720p.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png"},
    "NOW TV": {"page": "https://www.nowtv.com.tr/canli-yayin", "backup": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png"},
    "KANAL 7": {"page": "https://www.kanal7.com/canli-izle", "backup": "https://kanal7.daioncdn.net/kanal7/kanal7.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png"},
    "【entity-TV8¦canonical_name=TV8】": {"page": "https://www.tv8.com.tr/canli-yayin", "backup": "https://tv8.daioncdn.net/tv8/tv8_1080p.m3u8", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png"},
}

YTDLP_CHANNELS = {"ATV", "KANAL D", "【entity-SHOW TV¦canonical_name=SHOW TV】", "【entity-STAR TV¦canonical_name=STAR TV】", "NOW TV", "【entity-TV8¦canonical_name=TV8】"}

session = requests.Session()
session.headers.update(HEADERS)

def valid_m3u8(url):
    if not url or not isinstance(url, str): return False
    url = html.unescape(url.strip())
    if not url.startswith("http"): return False
    if ".m3u8" not in url.lower(): return False
    if " " in url: return False
    return True

def extract_with_ytdlp(page_url):
    try:
        import yt_dlp
        opts = {
            "quiet": True, "no_warnings": True, "skip_download": True,
            "format": "best[protocol^=m3u8]/best",
            "http_headers": {"Referer": page_url, "User-Agent": HEADERS["User-Agent"]}
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            if valid_m3u8(info.get("url","")): return info["url"]
            for f in reversed(info.get("formats", [])):
                if valid_m3u8(f.get("url","")): return f["url"]
    except Exception as e:
        print("YT-DLP HATASI: {}".format(e))
    return None

def extract_m3u8(page_url):
    try:
        r = session.get(page_url, timeout=20)
        src = r.text.replace("\\/", "/")
        m = re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', src)
        for u in m:
            u = u.strip().rstrip('",);')
            if valid_m3u8(u): return u
    except Exception as e:
        print("SAYFA HATASI: {}".format(e))
    return None

def read_old_playlist():
    header = "#EXTM3U"
    old_blocks, old_channels = [], {}
    if not os.path.exists(OUTPUT_FILE): return header, old_blocks, old_channels
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        curr = []
        for line in lines:
            if line.startswith("#EXTM3U"): continue
            if line.startswith("#EXTINF:"):
                if curr: old_blocks.append(curr)
                curr = [line]
            elif curr: curr.append(line)
        if curr: old_blocks.append(curr)
        for block in old_blocks:
            if GROUP not in block[0]: continue
            if "," not in block[0]: continue
            name = block[0].split(",", 1)[1].strip()
            for l in block[1:]:
                if l.startswith("http") and valid_m3u8(l):
                    old_channels[name] = l.strip(); break
    except: pass
    return header, old_blocks, old_channels

def scan_channel(name, info, old_channels):
    print("\n--- KANAL: {} ---".format(name))
    fresh = None
    page = info.get("page")
    if page and name in YTDLP_CHANNELS:
        fresh = extract_with_ytdlp(page)
        if valid_m3u8(fresh): print("YT-DLP OK")
    if not valid_m3u8(fresh) and page:
        fresh = extract_m3u8(page)
        if valid_m3u8(fresh): print("SAYFA OK")
    if not valid_m3u8(fresh) and valid_m3u8(info.get("backup")):
        fresh = info["backup"]
        print("YEDEK")
    if not valid_m3u8(fresh) and valid_m3u8(old_channels.get(name)):
        fresh = old_channels[name]
        print("ESKI KORUNDU")
    return fresh if valid_m3u8(fresh) else None

def main():
    print("MIRTI68 ULUSAL BASLADI")
    header, old_blocks, old_channels = read_old_playlist()
    new_channels = {}
    for name, info in CHANNELS.items():
        s = scan_channel(name, info, old_channels)
        if s: new_channels[name] = s

    preserved = []
    for b in old_blocks:
        if GROUP in b[0]: continue
        preserved.append("\n".join(b).strip())

    # BURASI KRITIK: "a" DEGIL "w" OLACAK
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n\n")
        for name, stream in new_channels.items():
            logo = CHANNELS[name]["logo"]
            page = CHANNELS[name]["page"]
            f.write('#EXTINF:-1 tvg-name="{}" tvg-logo="{}" group-title="{}",{}\n'.format(name, logo, GROUP, name))
            f.write('#EXTVLCOPT:http-referrer={}\n'.format(page))
            f.write('#EXTVLCOPT:http-user-agent={}\n'.format(HEADERS["User-Agent"]))
            f.write(stream + "\n\n")
        for block in preserved:
            f.write(block + "\n\n")
    
    print("TAMAMLANDI - Bulunan: {}".format(len(new_channels)))

if __name__ == "__main__":
    main()
