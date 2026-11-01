
import os
import re
import json
import time
import html
import cloudscraper

from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup

# ==========================================
# KANAL D - OTOMATIK SON 3 BOLUM
# ==========================================

BASE = "https://www.kanald.com.tr"

WORKER = "https://mak.sadecenjoy.workers.dev"


M3U = "mirti68.m3u"

GROUP = "KANALD Dizileri"
LIMIT = 3

DIZILER = {
    "daha-17": "Daha 17",
    "uzak-sehir": "Uzak Şehir",
    "haysiyet": "Haysiyet",
    "guller-ve-gunahlar": "Güller ve Günahlar"
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


# ==========================================
# SAYFA OKU
# ==========================================

def get_page(url):

    try:
        r = scraper.get(url, timeout=30)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text

    except Exception as e:
        print(f"  SAYFA HATA: {e}")
        return None


# ==========================================
# BOLUM NUMARASI
# ==========================================

def get_number(text):

    text = html.unescape(text)

    patterns = [
        r'(\d+)\s*\.?\s*bölüm',
        r'(\d+)\s*[-_]\s*bolum',
        r'bolum[-_ ](\d+)'
    ]

    for pattern in patterns:

        m = re.search(pattern, text, re.I)

        if m:
            return int(m.group(1))

    return None


# ==========================================
# POSTER BUL
# ==========================================

def get_poster(slug, series_url):

    source = get_page(series_url)

    if not source:
        return ""

    soup = BeautifulSoup(source, "html.parser")

    for prop in ["og:image", "twitter:image"]:

        tag = soup.find(
            "meta",
            attrs={"property": prop}
        )

        if not tag:
            tag = soup.find(
                "meta",
                attrs={"name": prop}
            )

        if tag and tag.get("content"):

            poster = urljoin(
                BASE,
                html.unescape(tag["content"])
            )

            print("  POSTER:", poster)

            return poster

    # Diziye ait görseller
    for img in soup.find_all("img"):

        for attr in [
            "src",
            "data-src",
            "data-original"
        ]:

            value = img.get(attr)

            if value and slug in value.lower():

                poster = urljoin(BASE, value)

                print("  POSTER:", poster)

                return poster

    print("  POSTER BULUNAMADI")

    return ""


# ==========================================
# GERCEK BOLUM LINKLERI
# ==========================================

def get_bolum_links(slug):

    url = f"{BASE}/{slug}/bolumler"

    print(f"\n  BÖLÜM SAYFASI: {url}")

    source = get_page(url)

    if not source:
        return []

    soup = BeautifulSoup(source, "html.parser")

    episodes = {}

    skip = [
        "fragman",
        "ön izleme",
        "on izleme",
        "on-izleme",
        "kamera arkası",
        "kamera-arkasi",
        "fotoğraf",
        "foto galeri",
        "sahne",
        "tanıtım",
        "tanitim"
    ]

    # Resmi bölüm bağlantılarını tara
    for a in soup.find_all("a", href=True):

        href = a["href"]

        full = urljoin(BASE, href)

        title = a.get_text(" ", strip=True)

        combined = (title + " " + full).lower()

        # Yalnızca ilgili dizinin bölüm sayfası
        if f"/{slug}/bolumler/" not in full.lower():
            continue

        # Fragman ve özel içerikleri çıkar
        if any(x in combined for x in skip):
            continue

        # Numara URL yerine görünen başlıktan alınır
        number = get_number(title)

        if number is None:
            number = get_number(full)

        # Son bölüm URL'sinde numara yoksa detay sayfasından al
        if number is None:

            detail_source = get_page(full)

            if detail_source:

                detail_soup = BeautifulSoup(
                    detail_source,
                    "html.parser"
                )

                heading = detail_soup.find("h1")

                detail_title = (
                    heading.get_text(" ", strip=True)
                    if heading else ""
                )

                number = get_number(
                    detail_title + " " + detail_source[:12000]
                )

        if number is None:
            continue

        episodes[number] = full

    # En yeni bölümleri seç
    result = sorted(
        episodes.items(),
        key=lambda x: x[0],
        reverse=True
    )[:LIMIT]

    print(f"  {len(result)} BÖLÜM BULUNDU")

    for number, link in result:
        print(f"  {number}. Bölüm -> {link}")

    return result


# ==========================================
# M3U8 BUL
# ==========================================

def find_m3u8(text):

    if not text:
        return None

    text = html.unescape(text)
    text = text.replace("\\/", "/")
    text = text.replace("\\u0026", "&")

    patterns = [
        r'https?://[^"\'\s<>]+\.m3u8(?:\?[^"\'\s<>]*)?',
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.I
        )

        for url in matches:

            url = url.rstrip("),;")

            if url.startswith("https://"):
                return url

    return None


# ==========================================
# EMBED ADRESI BUL
# ==========================================

def get_embed(source):

    soup = BeautifulSoup(source, "html.parser")

    # Meta embedURL
    tag = soup.find(
        attrs={"itemprop": "embedURL"}
    )

    if tag:

        value = (
            tag.get("content")
            or tag.get("href")
            or tag.get("src")
        )

        if value:
            return urljoin(BASE, value)

    # Iframe
    for iframe in soup.find_all("iframe"):

        src = iframe.get("src", "")

        if "dailymotion.com" in src.lower():

            return urljoin(BASE, src)

    return None


# ==========================================
# VIDEO ADRESI
# ==========================================

def get_m3u8(bolum_url):

    try:

        source = get_page(bolum_url)

        if not source:
            return None

        # Önce doğrudan sayfada ara
        direct = find_m3u8(source)

        if direct:
            print("  DIREKT M3U8 BULUNDU")
            return direct

        # Embed bul
        embed = get_embed(source)

        if not embed:
            print("  EMBED BULUNAMADI")
            return None

        print("  EMBED:", embed)

        # Dailymotion embed için mevcut Worker
        if "dailymotion.com" in embed.lower():

            try:

                response = scraper.get(
                    WORKER,
                    params={"url": embed},
                    timeout=25
                )

                response.raise_for_status()

                result = find_m3u8(response.text)

                if result:
                    print("  WORKER M3U8 BULDU")
                    return result

            except Exception as e:

                print("  WORKER HATA:", e)

        # Son olarak yt-dlp dene
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
                    embed,
                    download=False
                )

                if info:

                    formats = info.get("formats", [])

                    formats.sort(
                        key=lambda f: (
                            f.get("height") or 0,
                            f.get("tbr") or 0
                        ),
                        reverse=True
                    )

                    for fmt in formats:

                        stream = fmt.get("url", "")

                        if (
                            stream.startswith("https://")
                            and "m3u8" in stream.lower()
                        ):
                            return stream

        except Exception as e:

            print("  YT-DLP:", e)

    except Exception as e:

        print("  M3U8 HATA:", e)

    return None


# ==========================================
# M3U KAYDI
# ==========================================

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


# ==========================================
# MIRTI LISTESINI KORU
# ==========================================

def update_mirti(new_entries):

    old_entries = []

    if os.path.exists(MIRTI):

        with open(
            MIRTI,
            "r",
            encoding="utf-8-sig",
            errors="ignore"
        ) as f:

            content = f.read()

        blocks = re.findall(
            r'#EXTINF:[\s\S]*?(?=\n#EXTINF:|\Z)',
            content
        )

        for block in blocks:

            block = block.strip()

            if not block:
                continue

            # Sadece eski Kanal D grubunu yenile
            if f'group-title="{GROUP}"' in block:
                continue

            if re.search(r'https?://', block):
                old_entries.append(block)

    # Tekrar temizle
    result = []
    seen = set()

    for block in old_entries + new_entries:

        if block not in seen:
            seen.add(block)
            result.append(block)

    with open(
        MIRTI,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for block in result:
            f.write(block.strip() + "\n\n")

    print("MIRTI68 GÜNCELLENDİ")


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    print("=" * 50)
    print("KANAL D - SON 3 BÖLÜM TARAMASI")
    print("=" * 50)

    entries = []

    for slug, name in DIZILER.items():

        print("\n" + "=" * 40)
        print(name.upper())
        print("=" * 40)

        series_url = f"{BASE}/{slug}"

        poster = get_poster(
            slug,
            series_url
        )

        episodes = get_bolum_links(slug)

        if not episodes:
            print("BÖLÜM BULUNAMADI")
            continue

        added = 0

        for number, link in episodes:

            print(f"\n{number}. BÖLÜM")
            print("YAYIN ADRESİ ARANIYOR...")

            stream = get_m3u8(link)

            if not stream:

                print("M3U8 BULUNAMADI")
                time.sleep(1)
                continue

            entries.append(
                make_entry(
                    name,
                    number,
                    stream,
                    poster
                )
            )

            print("BAŞARILI!")
            added += 1

            time.sleep(1)

        print(f"\n{name}: {added} kayıt")

    # Boş dosya oluşturma ve eski listeyi silme
    if not entries:

        print("\nHİÇ YAYIN BULUNAMADI.")
        print("MEVCUT M3U DOSYALARI KORUNDU.")
        return

    # Geçici dosyaya yaz
    temp_file = M3U + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for entry in entries:
            f.write(entry + "\n\n")

    os.replace(temp_file, M3U)

    print(f"\n{M3U}: {len(entries)} KAYIT")

    update_mirti(entries)

    print("\nTARAMA TAMAMLANDI!")
    print("=" * 50)


if __name__ == "__main__":
    main()
            
