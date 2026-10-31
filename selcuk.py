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
    "selcukbeinsports1": "beIN SPORTS 1 Selcuk 🔴",
    "selcukbeinsports2": "beIN SPORTS 2 Selcuk 🔴",
    "selcukbeinsports3": "beIN SPORTS 3 Selcuk 🔴 ",
    "selcukbeinsports4": "beIN SPORTS 4 Selcuk 🔴",
    "selcukbeinsports5": "beIN SPORTS 5 Selcuk 🔴",
    "selcukbeinsportsmax1": "beIN SPORTS MAX 1 Selcuk 🔴",
    "selcukbeinsportsmax2": "beIN SPORTS MAX 2 Selcuk 🔴",
    "selcukbeinsportshaber": "beIN SPORTS Haber Selcuk 🔴",
    "selcukbeinconnect1": "beIN Con 1 Selcuk 🔴",
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
                f.write(f'#EXTINF:-1 group-title="{GROUP_NAME}" tvg-logo="https://i.ibb.co/mrrwmxDX/p-Lhc-Pi-Bn-400x400.jpg", {name}\n')
                f.write(f"#EXTVLCOPT:http-referrer={STREAM_REFERER}\n")
                f.write(f"{url}\n")
        print(f"✅ Yeni {OUTPUT_FILENAME} oluşturuldu")
        return

    with open(OUTPUT_FILENAME, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    header = lines[0].rstrip("\n") if lines else "#EXTM3U"
    if not header.startswith("#EXTM3U"):
        header = "#EXTM3U"

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        out.write(header + "\n")
        for l in lines[1:]:
            out.write(l if l.endswith("\n") else l + "\n")
        for name, url in new_entries:
            out.write(f'#EXTINF:-1 group-title="{GROUP_NAME}" tvg-logo="https://i.ibb.co/mrrwmxDX/p-Lhc-Pi-Bn-400x400.jpg", {name}\n')
            out.write(f"#EXTVLCOPT:http-referrer={STREAM_REFERER}\n")
            out.write(f"{url}\n")

    print(f"✅ Append tamam: {len(new_entries)} beIN mevcut {GROUP_NAME} grubuna eklendi")

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
