"""SLCK (SelcukSportsHD) spor kaynagi botu - APPEND MODU - AYRI GRUPLAR"""

import re
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
import urllib3
import warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

HOME_URL = "https://www.selcuksportshdfe44b96fcb.xyz/"
OUTPUT_FILENAME = "mirti68.m3u"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    "Referer": HOME_URL,
}

STREAM_DOMAINS = [
    "https://dga1op10s1u3lea.9e694e1c2ce7ac.click",
    "https://dga1op10s1u3leo.77b6de8e471484.click",
]

STREAM_REFERER = "https://main.uxsyplayer6859599e6c.click/"

PRETTY_NAMES = {
    "selcukbeinsports1": "beIN Sports 1",
    "selcukbeinsports2": "beIN Sports 2",
    "selcukbeinsports3": "beIN Sports 3",
    "selcukbeinsports4": "beIN Sports 4",
    "selcukbeinsports5": "beIN Sports 5",
    "selcukbeinsportsmax1": "beIN Sports Max 1",
    "selcukbeinsportsmax2": "beIN Sports Max 2",
    "selcukbeinsportshaber": "beIN Sports Haber",
    "selcukbeinconnect1": "beIN Connect 1",
    "selcukssport": "S Sport",
    "selcukssport2": "S Sport 2",
    "selcukssplus1": "S Sport Plus 1",
    "selcukssplus2": "S Sport Plus 2",
    "selcukssplus3": "S Sport Plus 3",
    "selcukssplus4": "S Sport Plus 4",
    "selcukssplus5": "S Sport Plus 5",
    "selcukssplus6": "S Sport Plus 6",
    "selcukssplus7": "S Sport Plus 7",
    "selcukssplus8": "S Sport Plus 8",
    "selcukssplus9": "S Sport Plus 9",
    "selcukssplus10": "S Sport Plus 10",
    "selcuksmartspor": "Smart Spor",
    "selcuksmartspor2": "Smart Spor 2",
    "selcuktivibuspor": "Tivibu Spor",
    "selcuktivibuspor1": "Tivibu Spor 1",
    "selcuktivibuspor2": "Tivibu Spor 2",
    "selcuktivibuspor3": "Tivibu Spor 3",
    "selcuktivibuspor4": "Tivibu Spor 4",
    "selcuktabiispor": "Tabii Spor",
    "selcuktabiispor1": "Tabii Spor 1",
    "selcuktabiispor2": "Tabii Spor 2",
    "selcuktabiispor3": "Tabii Spor 3",
    "selcuktabiispor4": "Tabii Spor 4",
    "selcuktabiispor5": "Tabii Spor 5",
    "selcuktabiispor6": "Tabii Spor 6",
    "selcuktabiispor7": "Tabii Spor 7",
}

def get_group(cid: str) -> str:
    c = cid.lower()
    if c.startswith("selcukbeinsports") or c.startswith("selcukbeinconnect"):
        return "🖥 WEB beIN SPORTS"
    elif c.startswith("selcukssport") or c.startswith("selcukssplus"):
        return "⚽ SSPORT"
    elif c.startswith("selcuktivibuspor"):
        return "⚽ TiViBU SPOR"
    elif c.startswith("selcuktabiispor"):
        return "⚽ TABii SPOR"
    elif c.startswith("selcuksmartspor"):
        return "⚽ SMART SPOR"
    else:
        return "🖥 WEB beIN SPORTS"

ALL_GROUPS = [
    "🖥 WEB beIN SPORTS",
    "⚽ SSPORT",
    "⚽ TiViBU SPOR",
    "⚽ TABii SPOR",
    "⚽ SMART SPOR",
]

def pretty(cid: str) -> str:
    return PRETTY_NAMES.get(cid.strip().lower(), cid.replace("selcuk", "").title())

def fetch_home():
    r = requests.get(HOME_URL, headers=HEADERS, timeout=25)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def parse_channel_ids(html):
    ids = re.findall(r"index\.php\?id=([A-Za-z0-9_\-]+)", html)
    out, seen = [], set()
    for cid in ids:
        if cid.lower() not in PRETTY_NAMES:
            continue
        if cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return out

def probe_media(playlist_url):
    r = requests.get(playlist_url, headers=HEADERS, timeout=12)
    if r.status_code != 200:
        return None
    text = r.text.lstrip()
    if not text.startswith("#EXTM3U"):
        return None
    base = playlist_url
    for _ in range(2):
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            url = urljoin(base, line)
            if url.endswith(".m3u8") or ".m3u8?" in url:
                rr = requests.get(url, headers=HEADERS, timeout=12)
                if rr.status_code != 200:
                    return None
                text, base = rr.text.lstrip(), url
                break
            rs = requests.get(url, headers=HEADERS, timeout=12, stream=True)
            if rs.status_code != 200:
                return None
            head = next(rs.iter_content(16), b"")
            if head[:1] == b"\x47" or b"ftyp" in head[:12]:
                return playlist_url
            return None
        else:
            return None
    return None

def resolve(cid):
    for domain in STREAM_DOMAINS:
        try:
            url = probe_media(f"{domain}/live/{cid}/playlist.m3u8")
        except Exception:
            url = None
        if url:
            return cid, url
    return cid, None

def append_to_mirti68(new_entries):
    if not os.path.exists(OUTPUT_FILENAME):
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for name, url, grp in new_entries:
                f.write(f'#EXTINF:-1 group-title="{grp}", {name}\n')
                f.write(f"#EXTVLCOPT:http-referrer={STREAM_REFERER}\n")
                f.write(f"{url}\n")
        print(f"✅ Yeni {OUTPUT_FILENAME} oluşturuldu")
        return

    with open(OUTPUT_FILENAME, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    header = lines[0].rstrip("\n") if lines else "#EXTM3U"
    if not header.startswith("#EXTM3U"):
        header = "#EXTM3U"

    kept_lines = []
    skip_next_url = False
    skip_next_vlc = False
    
    for line in lines[1:]:
        if line.startswith("#EXTINF"):
            if any(f'group-title="{g}"' in line for g in ALL_GROUPS):
                skip_next_url = True
                skip_next_vlc = True
                continue
            kept_lines.append(line)
            skip_next_url = False
            skip_next_vlc = False
        elif line.startswith("#EXTVLCOPT:http-referrer=") and skip_next_vlc:
            skip_next_vlc = False
            continue
        elif line.startswith("http") and skip_next_url:
            skip_next_url = False
            continue
        else:
            kept_lines.append(line)

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        out.write(header + "\n")
        for l in kept_lines:
            out.write(l if l.endswith("\n") else l + "\n")
        for name, url, grp in new_entries:
            out.write(f'#EXTINF:-1 group-title="{grp}", {name}\n')
            out.write(f"#EXTVLCOPT:http-referrer={STREAM_REFERER}\n")
            out.write(f"{url}\n")

    print(f"✅ Append tamam: eski satırlar korundu + {len(new_entries)} Selçuk eklendi (ayrı gruplar)")

def main():
    print("--- 🏟  SLCK (SelcukSportsHD) taraniyor ---")
    try:
        html = fetch_home()
    except Exception as e:
        print(f"❌ Ana sayfa erisilemiyor: {e}")
        print("❌ mirti68.m3u DEGISTIRILMIYOR")
        sys.exit(1)

    ids = parse_channel_ids(html)
    print(f"✅ {len(ids)} spor kanali bulundu")
    if not ids:
        print("❌ HIC KANAL YOK - mirti68.m3u DEGISTIRILMIYOR")
        sys.exit(1)

    entries = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(resolve, cid): cid for cid in ids}
        for fut in as_completed(futures):
            cid, url = fut.result()
            if url:
                grp = get_group(cid)
                entries.append((pretty(cid), url, grp))
                print(f"  ✅ {pretty(cid)} -> {grp}")
            else:
                print(f"  ❌ {pretty(cid)} ({cid}): erisilemedi")

    if not entries:
        print("\n❌ HIC CALISAN YAYIN YOK - mirti68.m3u DEGISTIRILMIYOR")
        sys.exit(1)

    entries.sort(key=lambda x: (x[2], x[0].lower()))
    append_to_mirti68(entries)

if __name__ == "__main__":
    main()
