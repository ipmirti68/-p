"""SLCK (SelcukSportsHD) spor kaynagi botu - SADECE beIN"""

import re
import sys
import os

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

STREAM_DOMAIN = "https://dga1op10s1u3lea.9e694e1c2ce7ac.click"
STREAM_REFERER = "https://main.uxsyplayer6859599e6c.click/"
GROUP_NAME = "🖥beINSPORTS"

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
}

def pretty(cid: str) -> str:
    return PRETTY_NAMES.get(cid.strip().lower(), cid.replace("selcuk", "").title())

def fetch_home():
    r = requests.get(HOME_URL, headers=HEADERS, timeout=25)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def parse_bein_ids(html):
    ids = re.findall(r"index\.php\?id=([A-Za-z0-9_\-]+)", html)
    out, seen = [], set()
    for cid in ids:
        low = cid.lower()
        if low not in PRETTY_NAMES:
            continue
        if cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return out

def append_to_mirti68(new_entries):
    if not os.path.exists(OUTPUT_FILENAME):
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for name, url in new_entries:
                f.write(f'#EXTINF:-1 group-title="{GROUP_NAME}", {name}\n')
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
    skip_next = 0
    for line in lines[1:]:
        if line.startswith("#EXTINF"):
            if f'group-title="{GROUP_NAME}"' in line:
                skip_next = 2
                continue
            kept_lines.append(line)
            skip_next = 0
        elif skip_next > 0:
            skip_next -= 1
            continue
        else:
            kept_lines.append(line)

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        out.write(header + "\n")
        for l in kept_lines:
            out.write(l if l.endswith("\n") else l + "\n")
        for name, url in new_entries:
            out.write(f'#EXTINF:-1 group-title="{GROUP_NAME}", {name}\n')
            out.write(f"#EXTVLCOPT:http-referrer={STREAM_REFERER}\n")
            out.write(f"{url}\n")

    print(f"✅ Tamam: eski {GROUP_NAME} silindi, {len(new_entries)} yeni eklendi")

def main():
    print("--- 🏟  SLCK (SelcukSportsHD) beIN taraniyor ---")
    try:
        html = fetch_home()
    except Exception as e:
        print(f"❌ Ana sayfa erisilemiyor: {e}")
        sys.exit(1)

    ids = parse_bein_ids(html)
    print(f"✅ {len(ids)} beIN kanali bulundu")
    if not ids:
        print("❌ beIN KANAL YOK")
        sys.exit(1)

    entries = []
    for cid in ids:
        url = f"{STREAM_DOMAIN}/live/{cid}/playlist.m3u8"
        entries.append((pretty(cid), url))
        print(f"  ✅ {pretty(cid)}")

    entries.sort(key=lambda x: x[0].lower())
    append_to_mirti68(entries)

if __name__ == "__main__":
    main()
