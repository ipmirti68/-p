
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

BASE = "https://www.viki.com"
CATEGORY = BASE + "/categories/country/korea/genre/all?type=series"

OUTPUT = "hanim_viki_kore.m3u"
GROUP = "🇰🇷 HANIM VIKI DİZİLERİ ⭕"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def main():
    print("[BASLA] Viki Kore dizileri kontrol ediliyor...")

    r = requests.get(CATEGORY, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    found = {}

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        name = a.get_text(" ", strip=True)

        if not name or not re.match(r"^/tv/", href):
            continue

        url = urljoin(BASE, href)

        if url in found:
            continue

        image = a.select_one("img")
        poster = ""

        if image:
            poster = (
                image.get("src")
                or image.get("data-src")
                or ""
            )

        found[url] = {
            "name": name,
            "poster": poster
        }

    lines = ["#EXTM3U"]

    for url, item in found.items():
        name = item["name"]
        poster = item["poster"]

        lines.append(
            f'#EXTINF:-1 tvg-logo="{poster}" '
            f'group-title="{GROUP}",{name} - 1. BÖLÜM'
        )
        lines.append(url)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("[SONUC] Bulunan dizi:", len(found))
    print("[DOSYA]", OUTPUT)

if __name__ == "__main__":
    main()
