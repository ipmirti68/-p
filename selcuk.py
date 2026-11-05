
"""SLCK (SelcukSportsHD) spor kaynagi botu - SADECE beIN"""

import re
import sys
import requests
import urllib3
import warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

HOME_URL = "https://www.selcuksportshd14e17ba2ad.xyz/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    ),
    "Referer": HOME_URL,
}

STREAM_DOMAIN = "dga1op10s1u3lea.308aae467c3965.click"
STREAM_REFERER = "https://main.uxsyplayer6859599e6c.click/"

OUTPUT_FILENAME = "mirti68.m3u"
BEIN_GROUP = "🖥beINSPORTS"
SPORTS_GROUP = "🖥SPORTS"

LOGO = "https://i.ibb.co/mrrwmxDX/p-Lhc-Pi-Bn-400x400.jpg"

PRETTY_NAMES = {
    "selcukbeinsports1": "beIN SPORTS 1 Selcuk 1🔴",
    "selcukbeinsports2": "beIN SPORTS 2 Selcuk 1🔴",
    "selcukbeinsports3": "beIN SPORTS 3 Selcuk 1🔴",
    "selcukbeinsports4": "beIN SPORTS 4 Selcuk 1🔴",
    "selcukbeinsports5": "beIN SPORTS 5 Selcuk 1🔴",
    "selcukbeinsportsmax1": "beIN SPORTS MAX 1 Selcuk 1🔴",
    "selcukbeinsportsmax2": "beIN SPORTS MAX 2 Selcuk 1🔴",
    "selcukbeinsportshaber": "beIN SPORTS Haber Selcuk 1🔴",
    "selcukbeinconnect1": "beIN Con 1 Selcuk 1🔴",
}


def pretty(cid: str) -> str:
    return PRETTY_NAMES.get(
        cid.strip().lower(),
        cid.replace("selcuk", "").title()
    )


def fetch_home():
    r = requests.get(
        HOME_URL,
        headers=HEADERS,
        timeout=25
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_bein_ids(html):
    ids = re.findall(
        r"index\.php\?id=([A-Za-z0-9_\-]+)",
        html
    )

    out = []
    seen = set()

    for cid in ids:
        low = cid.lower()

        if low not in PRETTY_NAMES:
            continue

        if low in seen:
            continue

        seen.add(low)
        out.append(cid)

    return out


def append_to_mirti68(new_entries):

    if not new_entries:
        print("❌ Yeni kayıt bulunamadı.")
        return

    try:
        from m3u_manager import update_group
    except ImportError:
        print("❌ m3u_manager.py bulunamadı!")
        return

    formatted_entries = []

    for name, url in new_entries:
        entry = (
            f'#EXTINF:-1 tvg-logo="{LOGO}" '
            f'group-title="{BEIN_GROUP}",{name}\n'
            f'#EXTVLCOPT:http-referrer={STREAM_REFERER}\n'
            f'{url}'
        )

        formatted_entries.append(entry)

    try:
        update_group(
            BEIN_GROUP,
            formatted_entries,
            filename=OUTPUT_FILENAME
        )

        print(
            f"✅ {len(formatted_entries)} beIN kanalı "
            f"{BEIN_GROUP} grubunda güncellendi."
        )

    except Exception as e:
        print(f"❌ M3U güncelleme hatası: {e}")


def main():

    print("--- 🏟 SLCK (SelcukSportsHD) beIN taraniyor ---")

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

        entries.append((
            pretty(cid),
            url
        ))

        print(f"  ✅ {pretty(cid)}")

    entries.sort(key=lambda x: x[0].lower())

    append_to_mirti68(entries)


if __name__ == "__main__":
    main()
