
import os
import re
import time
import html
import codecs
import shutil
import unicodedata
import requests

from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ==================================================
# MIRTI68 - KANAL D SON 3 BÖLÜM OTOMATİK GÜNCELLEYİCİ
# TAMAMEN BAĞIMSIZ M3U DOSYASI
# ==================================================

BASE = "https://www.kanald.com.tr"
WORKER = "https://mak.sadecenjoy.workers.dev"

M3U = "kanalddizi.m3u"

GROUP = "🟪◆  KANAL D DİZİ 📺⭕"

LIMIT = 3

DIZILER = {
    "daha-17": "Daha 17",
    "uzak-sehir": "Uzak Şehir",
    "haysiyet": "Haysiyet",
    "guller-ve-gunahlar": "Güller ve Günahlar",
    "susuz-yaz": "Susuz Yaz",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Safari/537.36"
    ),
    "Referer": BASE + "/",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


# ==================================================
# METİN YARDIMCILARI
# ==================================================

def temizle(value):
    return html.unescape(str(value or "")).strip()


def guvenli(value):
    return (
        temizle(value)
        .replace('"', "'")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def normalize(value):
    value = temizle(value).casefold()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )

    return re.sub(r"\s+", " ", value).strip()


# ==================================================
# SAYFA OKU
# ==================================================

def get_page(url):

    for deneme in range(2):

        try:

            response = session.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            response.encoding = (
                response.apparent_encoding or "utf-8"
            )

            return response.text

        except Exception as e:

            print(
                f"  SAYFA HATA ({deneme + 1}): {e}"
            )

            time.sleep(2)

    return None


# ==================================================
# BÖLÜM NUMARASI
# ==================================================

def get_number(text):

    text = temizle(text)

    patterns = [
        r'(\d+)\s*\.?\s*bölüm',
        r'(\d+)\s*[-_]\s*bolum',
        r'bolum[-_ ](\d+)',
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:
            return int(match.group(1))

    return None


# ==================================================
# POSTER BUL
# ==================================================

def get_poster(slug, series_url):

    source = get_page(series_url)

    if not source:
        return ""

    soup = BeautifulSoup(
        source,
        "html.parser"
    )

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
                temizle(tag["content"])
            )

            print("  POSTER:", poster)

            return poster

    for img in soup.find_all("img"):

        for attr in [
            "src",
            "data-src",
            "data-original"
        ]:

            value = img.get(attr)

            if value and slug in value.lower():

                poster = urljoin(
                    BASE,
                    value
                )

                print("  POSTER:", poster)

                return poster

    print("  POSTER BULUNAMADI")

    return ""


# ==================================================
# GERÇEK BÖLÜM LİNKLERİ
# ==================================================

def get_bolum_links(slug):

    url = f"{BASE}/{slug}/bolumler"

    print(f"\n  BÖLÜM SAYFASI: {url}")

    source = get_page(url)

    if not source:
        return []

    low = source.lower()

    if (
        "fragmanlar" in low[:8000]
        and "/bolumler/" not in low[:15000]
    ):

        print(
            "  UYARI: Sayfa fragmanlara yönlenmiş, "
            "bölüm yok - ATLANIYOR"
        )

        return []

    soup = BeautifulSoup(
        source,
        "html.parser"
    )

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
        "tanitim",
    ]

    for a in soup.find_all("a", href=True):

        href = a["href"]

        full = urljoin(
            BASE,
            href
        )

        title = a.get_text(
            " ",
            strip=True
        )

        combined = (
            title + " " + full
        ).lower()

        if f"/{slug}/bolumler/" not in full.lower():
            continue

        if "fragman" in full.lower():
            continue

        if any(x in combined for x in skip):
            continue

        number = get_number(title)

        if number is None:
            number = get_number(full)

        if number is None:
            continue

        episodes[number] = full

    result = sorted(
        episodes.items(),
        key=lambda x: x[0],
        reverse=True
    )[:LIMIT]

    print(
        f"  {len(result)} BÖLÜM BULUNDU"
    )

    for number, link in result:

        print(
            f"  {number}. Bölüm -> {link}"
        )

    return result


# ==================================================
# M3U8 BUL
# ==================================================

def find_m3u8(text):

    if not text:
        return None

    text = html.unescape(text)

    text = (
        text
        .replace("\\/", "/")
        .replace("\\u0026", "&")
    )

    matches = re.findall(
        r'https?://[^"\'\s<>]+?\.m3u8'
        r'(?:\?[^"\'\s<>]*)?',
        text,
        re.I
    )

    for url in matches:

        url = url.rstrip("),;")

        if url.startswith("https://"):
            return url

    return None


# ==================================================
# EMBED ADRESİ BUL
# ==================================================

def get_embed(source):

    soup = BeautifulSoup(
        source,
        "html.parser"
    )

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

    for iframe in soup.find_all("iframe"):

        src = iframe.get("src", "")

        if "dailymotion.com" in src.lower():
            return urljoin(BASE, src)

    return None


# ==================================================
# VİDEO ADRESİ
# ==================================================

def get_m3u8(bolum_url):

    try:

        source = get_page(bolum_url)

        if not source:
            return None

        direct = find_m3u8(source)

        if direct:

            print("  DİREKT M3U8 BULUNDU")

            return direct

        embed = get_embed(source)

        if not embed:

            print("  EMBED BULUNAMADI")

            return None

        print("  EMBED:", embed)

        # DAILYMOTION WORKER

        if "dailymotion.com" in embed.lower():

            try:

                response = session.get(
                    WORKER,
                    params={"url": embed},
                    timeout=25
                )

                response.raise_for_status()

                result = find_m3u8(
                    response.text
                )

                if result:

                    print("  WORKER M3U8 BULDU")

                    return result

            except Exception as e:

                print("  WORKER HATA:", e)

        # YT-DLP

        try:

            import yt_dlp

            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "socket_timeout": 25,
            }

            with yt_dlp.YoutubeDL(options) as ydl:

                info = ydl.extract_info(
                    embed,
                    download=False
                )

                if info:

                    formats = info.get(
                        "formats",
                        []
                    )

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


# ==================================================
# M3U KAYDI OLUŞTUR
# ==================================================

def make_entry(name, number, stream, poster):

    title = (
        f"TR: {name} - {number}. Bölüm"
    )

    title = guvenli(title)
    poster = guvenli(poster)

    return [
        (
            f'#EXTINF:-1 '
            f'tvg-name="{title}" '
            f'tvg-logo="{poster}" '
            f'group-title="{GROUP}",'
            f'{title}'
        ),
        f'#EXTVLCOPT:http-referrer={BASE}/',
        stream,
    ]


# ==================================================
# M3U GRUP VE KAYIT YARDIMCILARI
# ==================================================

def grup_bul(record_lines):

    for line in record_lines:

        if line.startswith("#EXTINF:"):

            match = re.search(
                r'group-title="([^"]*)"',
                line
            )

            return match.group(1) if match else ""

    return ""


def kanal_adi(record_lines):

    for line in record_lines:

        if line.startswith("#EXTINF:"):

            return line.split(
                ",",
                1
            )[-1].strip()

    return ""


def kayitlari_ayir(lines):

    records = []
    current = []

    for line in lines:

        if line.startswith("#EXTINF:") and current:

            records.append(current)
            current = []

        current.append(line)

    if current:
        records.append(current)

    return records


# ==================================================
# ESKİ KAYIT HANGİ DİZİYE AİT?
# ==================================================

def dizi_eslesiyor(record, isim):

    ad = normalize(
        kanal_adi(record)
    )

    hedef = normalize(isim)

    if not ad or not hedef:
        return False

    # TR: ve bölüm bilgisinden bağımsız eşleştirme
    if hedef in ad:
        return True

    return False


# ==================================================
# M3U DOSYASINI OKU
# ==================================================

def m3u_oku():

    if not os.path.exists(M3U):

        print(
            f"[YENİ DOSYA] {M3U} ilk başarılı taramada oluşturulacak."
        )

        return (
            False,
            "\n",
            ["#EXTM3U"],
            []
        )

    with open(M3U, "rb") as f:
        raw = f.read()

    bom = raw.startswith(codecs.BOM_UTF8)

    metin = raw.decode(
        "utf-8-sig",
        errors="replace"
    )

    newline = (
        "\r\n"
        if "\r\n" in metin
        else "\n"
    )

    satirlar = metin.splitlines()

    ilk_extinf = next(
        (
            i for i, satir in enumerate(satirlar)
            if satir.startswith("#EXTINF:")
        ),
        len(satirlar)
    )

    baslik = satirlar[:ilk_extinf]

    if not baslik:
        baslik = ["#EXTM3U"]

    govde = satirlar[ilk_extinf:]

    records = kayitlari_ayir(govde)

    return (
        bom,
        newline,
        baslik,
        records
    )


# ==================================================
# BAĞIMSIZ KANAL D M3U GÜNCELLE
# ==================================================

def update_mirti(new_entries, basarisiz):

    bom, newline, baslik, records = m3u_oku()

    # Sadece bu dosyanın Kanal D kayıtları kullanılır.
    eski_kanald = [
        r for r in records
        if grup_bul(r) == GROUP
    ]

    # Başarısız dizilerin eski kayıtlarını koru.
    korunan = []

    for record in eski_kanald:

        ad = kanal_adi(record)

        for isim in basarisiz:

            if dizi_eslesiyor(record, isim):

                korunan.append(record)

                print(
                    f"  KORUNDU (ESKİ): {ad}"
                )

                break

    # Yeni kayıtları satır listesine çevir.
    yeni_records = []

    for entry in new_entries:

        if isinstance(entry, str):

            lines = [
                line
                for line in entry.strip().splitlines()
                if line.strip()
            ]

        else:

            lines = [
                line
                for line in entry
                if line.strip()
            ]

        if lines:
            yeni_records.append(lines)

    # Dosyada yalnızca Kanal D kayıtları bulunacak.
    # Başka gruplar veya başka kanal kayıtları taşınmaz.
    son_records = yeni_records + korunan

    if not son_records:

        print(
            "[UYARI] Yazılacak Kanal D kaydı yok."
        )

        print("Dosya değiştirilmedi.")

        return False

    # Mevcut dosya varsa yedekle.
    if os.path.exists(M3U):

        shutil.copy2(
            M3U,
            M3U + ".bak"
        )

        print(
            "[YEDEK]",
            M3U + ".bak"
        )

    # Yeni M3U oluştur.
    sonuc = list(baslik)

    if not sonuc:
        sonuc = ["#EXTM3U"]

    for record in son_records:
        sonuc.extend(record)

    yeni_metin = (
        newline.join(sonuc)
        + newline
    )

    temp = M3U + ".tmp"

    encoding = (
        "utf-8-sig"
        if bom
        else "utf-8"
    )

    with open(temp, "wb") as f:

        f.write(
            yeni_metin.encode(encoding)
        )

    os.replace(
        temp,
        M3U
    )

    print("\n===================================")
    print("KANAL D M3U GÜNCELLEMESİ TAMAMLANDI")
    print("===================================")
    print("Dosya:", M3U)
    print("Grup:", GROUP)
    print("Yeni bölüm kaydı:", len(new_entries))
    print("Korunan eski kayıt:", len(korunan))
    print("Başka M3U dosyası: KULLANILMADI")
    print("Başka kanal grupları: EKLENMEDİ")

    if os.path.exists(M3U + ".bak"):
        print("Yedek:", M3U + ".bak")

    print("===================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 50)
    print("KANAL D - SON 3 BÖLÜM TARAMASI")
    print("=" * 50)

    entries = []
    basarili = []
    basarisiz = []

    for slug, name in DIZILER.items():

        print("\n" + "=" * 40)
        print(name.upper())
        print("=" * 40)

        try:

            series_url = f"{BASE}/{slug}"

            poster = get_poster(
                slug,
                series_url
            )

            episodes = get_bolum_links(
                slug
            )

            if not episodes:

                print(
                    "BÖLÜM BULUNAMADI - "
                    "ESKİ KAYIT KORUNACAK"
                )

                basarisiz.append(name)

                continue

            added = 0

            for number, link in episodes:

                print(f"\n{number}. BÖLÜM")

                print(
                    "YAYIN ADRESİ ARANIYOR..."
                )

                try:

                    stream = get_m3u8(link)

                except Exception as e:

                    print(
                        f"  BÖLÜM HATA, ATLANIYOR: {e}"
                    )

                    continue

                if not stream:

                    print(
                        "M3U8 BULUNAMADI - "
                        "BU BÖLÜM ATLANIYOR"
                    )

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

            if added > 0:

                basarili.append(name)

                print(
                    f"\n{name}: {added} kayıt"
                )

            else:

                print(
                    f"\n{name}: Hiç yayın bulunamadı, "
                    "eski kayıt korunacak"
                )

                basarisiz.append(name)

        except Exception as e:

            print(
                f"\n{name} HATA VERDİ, ATLANIYOR: {e}"
            )

            basarisiz.append(name)

            continue

    print("\n" + "=" * 50)

    print(
        "BAŞARILI:",
        ", ".join(basarili) if basarili else "YOK"
    )

    if basarisiz:

        print(
            "ATLANAN:",
            ", ".join(basarisiz)
        )

    print("=" * 50)

    # Hiçbir yeni yayın bulunamadıysa mevcut listeye dokunma.
    if not entries:

        print("\nHİÇ YENİ YAYIN BULUNAMADI.")

        print(
            "MEVCUT M3U DOSYASI KORUNDU."
        )

        print(
            "Dosyada herhangi bir değişiklik yapılmadı."
        )

        return

    update_mirti(
        entries,
        basarisiz
    )

    print("\nTARAMA TAMAMLANDI!")
    print("=" * 50)


if __name__ == "__main__":
    main()
    

        
