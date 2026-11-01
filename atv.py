
import os
import re
import time
import html
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup

# ==================================================
# ATV OTOMATIK SON 3 TAM BOLUM
# ==================================================

BASE = "https://www.atv.com.tr"

M3U_FILE = "atv_playlist.m3u"
MIRTI_FILE = "mirti68.m3u"

GROUP = "ATV Dizileri"
LIMIT = 3

SERIES = {
    "alti-ustu-istanbul": {
        "name": "Altı Üstü İstanbul",
        "url": f"{BASE}/alti-ustu-istanbul"
    },

    "gunesin-dogdugu-yer": {
        "name": "Güneşin Doğduğu Yer",
        "url": f"{BASE}/gunesin-dogdugu-yer"
    },

    "abi": {
        "name": "A.B.İ.",
        "url": f"{BASE}/abi"
    },

    "ask-ve-taht": {
        "name": "Aşk ve Taht",
        "url": f"{BASE}/ask-ve-taht"
    },

    "mercan-kosk": {
        "name": "Mercan Köşk",
        "url": f"{BASE}/mercan-kosk"
    }
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Safari/537.36"
    ),
    "Referer": BASE + "/"
}

scraper = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "windows",
        "desktop": True
    }
)

scraper.headers.update(HEADERS)


# ==================================================
# SAYFA OKU
# ==================================================

def get_page(url):

    try:
        r = scraper.get(url, timeout=30)
        r.raise_for_status()

        r.encoding = r.apparent_encoding

        return r.text

    except Exception as e:
        print(f"  SAYFA HATASI: {e}")
        return None


# ==================================================
# POSTER BUL
# ==================================================

def get_poster(series_url, slug, name):

    print("  POSTER ARANIYOR...")

    source = get_page(series_url)

    if not source:
        return ""

    soup = BeautifulSoup(source, "html.parser")

    candidates = []

    # SEO görselleri
    for meta in soup.find_all("meta"):

        prop = (
            str(meta.get("property", "")) + " " +
            str(meta.get("name", ""))
        ).lower()

        if "image" in prop:

            value = meta.get("content")

            if value:
                candidates.append(
                    urljoin(BASE, html.unescape(value))
                )

    # Diziye ait resimler
    for img in soup.find_all("img"):

        alt = img.get("alt", "").lower()

        for attr in [
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ]:

            value = img.get(attr)

            if not value:
                continue

            full = urljoin(BASE, html.unescape(value))

            if (
                slug in full.lower()
                or slug in alt
                or name.lower() in alt
            ):
                candidates.insert(0, full)

    # Tekrarları temizle
    unique = list(dict.fromkeys(candidates))

    for poster in unique:

        if not poster.startswith("https://"):
            continue

        if any(x in poster.lower() for x in [
            ".svg",
            "logo",
            "facebook",
            "placeholder"
        ]):
            continue

        try:

            r = scraper.get(
                poster,
                timeout=15,
                stream=True
            )

            content_type = r.headers.get(
                "Content-Type", ""
            ).lower()

            valid = (
                r.status_code == 200
                and content_type.startswith("image/")
            )

            r.close()

            if valid:

                print("  POSTER OK")
                print(" ", poster)

                return poster

        except Exception:
            pass

    print("  POSTER BULUNAMADI")

    return ""


# ==================================================
# GERCEK BOLUM LINKLERINI BUL
# ==================================================

def get_episode_links(series_url, slug, name):

    print("\n  BÖLÜMLER TARANIYOR...")

    source = get_page(series_url)

    if not source:
        return []

    soup = BeautifulSoup(source, "html.parser")

    episodes = {}

    skip_words = [
        "fragman",
        "kamera arkası",
        "kamera-arkasi",
        "foto galeri",
        "foto-galeri",
        "özel sahne",
        "ozel-sahne",
        "ön izleme",
        "on-izleme",
        "tanıtım",
        "tanitim"
    ]

    for a in soup.find_all("a", href=True):

        href = a["href"]

        full_url = urljoin(BASE, href)

        text = a.get_text(" ", strip=True)

        combined = (
            full_url + " " + text
        ).lower()

        # Yalnızca dizinin kendi bağlantıları
        if slug not in full_url.lower():
            continue

        # Gerçek bölüm izleme adresi
        if not re.search(
            r"/\d+-bolum/izle/?",
            full_url.lower()
        ):
            continue

        # Fragman ve diğer içerikler hariç
        if any(word in combined for word in skip_words):
            continue

        # Bölüm numarasını URL'den al
        match = re.search(
            r"/(\d+)-bolum/izle",
            full_url.lower()
        )

        if not match:
            continue

        number = int(match.group(1))

        if number <= 0:
            continue

        episodes[number] = full_url

    result = sorted(
        episodes.items(),
        key=lambda x: x[0],
        reverse=True
    )

    print(f"  Bulunan tam bölüm: {len(result)}")

    for number, link in result[:LIMIT]:

        print(f"  {number}. BÖLÜM")
        print(f"  {link}")

    return result[:LIMIT]


# ==================================================
# YT-DLP ILE M3U8 ADRESI
# ==================================================

def get_m3u8(full_url):

    try:

        import yt_dlp

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": 25
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                full_url,
                download=False
            )

            if not info:
                return None

            formats = info.get("formats", [])

            # Önce HLS formatları
            hls_formats = []

            for fmt in formats:

                url = fmt.get("url", "")
                protocol = fmt.get("protocol", "")

                if not url:
                    continue

                if (
                    "m3u8" in url.lower()
                    or "m3u8" in protocol.lower()
                ):

                    hls_formats.append(fmt)

            # En iyi bulunan HLS formatını seç
            hls_formats.sort(
                key=lambda x: (
                    x.get("height") or 0,
                    x.get("tbr") or 0
                ),
                reverse=True
            )

            for fmt in hls_formats:

                stream = fmt.get("url", "")

                if stream.startswith("https://"):
                    return stream

            # Bazı extractor sonuçlarında doğrudan URL
            direct = info.get("url", "")

            if (
                direct.startswith("https://")
                and "m3u8" in direct.lower()
            ):
                return direct

    except Exception as e:

        print(f"  YT-DLP HATASI: {e}")

    return None


# ==================================================
# M3U KAYDI
# ==================================================

def make_entry(name, number, stream, poster):

    title = f"TR: {name} - {number}. Bölüm"

    title = title.replace('"', "'")

    return (
        f'#EXTINF:-1 tvg-name="{title}" '
        f'tvg-logo="{poster}" '
        f'group-title="{GROUP}",{title}\n'
        f'#EXTVLCOPT:http-referrer={BASE}/\n'
        f'{stream}'
    )


# ==================================================
# MIRTI LISTESINI KORU VE GUNCELLE
# ==================================================

def update_mirti(new_entries):

    old_entries = []

    if os.path.exists(MIRTI_FILE):

        with open(
            MIRTI_FILE,
            "r",
            encoding="utf-8-sig",
            errors="ignore"
        ) as f:

            content = f.read()

        blocks = re.findall(
            r"#EXTINF:[\s\S]*?(?=\n#EXTINF:|\Z)",
            content
        )

        for block in blocks:

            block = block.strip()

            if not block:
                continue

            # Yalnızca ATV grubunu yenile
            if f'group-title="{GROUP}"' in block:
                continue

            if re.search(
                r"https?://",
                block
            ):
                old_entries.append(block)

    # Tekrarlı kayıtları temizle
    unique = []
    seen = set()

    for block in old_entries:

        if block not in seen:
            seen.add(block)
            unique.append(block)

    # Yeni kayıtları ekle
    with open(
        MIRTI_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for block in unique + new_entries:

            f.write(block.strip() + "\n\n")

    print("\nMIRTI68 GÜNCELLENDİ")
    print(f"Yeni ATV kaydı: {len(new_entries)}")


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 55)
    print("ATV - GÜNCEL DİZİLER SON 3 BÖLÜM")
    print("=" * 55)

    all_entries = []

    for slug, info in SERIES.items():

        name = info["name"]
        series_url = info["url"]

        print("\n" + "=" * 45)
        print(name.upper())
        print("=" * 45)

        # Poster
        poster = get_poster(
            series_url,
            slug,
            name
        )

        # Gerçek bölüm bağlantıları
        episodes = get_episode_links(
            series_url,
            slug,
            name
        )

        if not episodes:

            print("  BÖLÜM BULUNAMADI")
            continue

        added = 0

        for number, episode_url in episodes:

            print(f"\n  {name} - {number}. BÖLÜM")

            print("  YAYIN ADRESİ ARANIYOR...")

            stream = get_m3u8(episode_url)

            if not stream:

                print("  M3U8 BULUNAMADI")
                time.sleep(1)
                continue

            entry = make_entry(
                name,
                number,
                stream,
                poster
            )

            all_entries.append(entry)

            added += 1

            print("  BAŞARILI!")
            time.sleep(1)

        print(
            f"\n{name}: {added} bölüm eklendi."
        )

    # Hiç yayın bulunmadıysa dosyaları koru
    if not all_entries:

        print("\nHİÇBİR YAYIN BULUNAMADI.")
        print("Mevcut M3U dosyaları korunuyor.")
        return

    # ATV M3U oluştur
    with open(
        M3U_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for entry in all_entries:

            f.write(entry.strip() + "\n\n")

    print("\n" + "=" * 55)

    print(
        f"{M3U_FILE}: "
        f"{len(all_entries)} KAYIT"
    )

    # MIRTI güncelle
    update_mirti(all_entries)

    print("\nİŞLEM TAMAMLANDI!")
    print("=" * 55)


if __name__ == "__main__":
    main()
