import cloudscraper
import re
import os
import json
import time
import html
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup

# ==================================================
# SHOW TV - SON 3 BÖLÜM OTOMATİK TARAMA
# ==================================================

BASE = "https://www.showtv.com.tr"

M3U = "showtv.m3u"
MIRTI = "mirti68.m3u"

GROUP = "SHOW Dizileri"
LIMIT = 3

SERIES = {
    "sevdan-bir-ates": {
        "name": "Sevdan Bir Ateş",
        "slug": "sevdan-bir-ates"
    },
    "kizilcik-serbeti": {
        "name": "Kızılcık Şerbeti",
        "slug": "kizilcik-serbeti"
    },
    "muhtemel-ask": {
        "name": "Muhtemel Aşk",
        "slug": "muhtemel-ask"
    }
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
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
# SAYFA İNDİRME
# ==================================================

def get_page(url):
    try:
        r = scraper.get(url, timeout=30)
        r.raise_for_status()

        if not r.encoding:
            r.encoding = r.apparent_encoding

        return r.text

    except Exception as e:
        print(f"  SAYFA HATASI: {e}")
        return None


# ==================================================
# DİZİ TANITIM SAYFASINI BUL
# ==================================================

def find_series_page(key, info):
    print(f"\nDİZİ ARANIYOR: {info['name']}")

    pages = [
        BASE + "/diziler",
        BASE + "/"
    ]

    for page_url in pages:
        source = get_page(page_url)

        if not source:
            continue

        soup = BeautifulSoup(source, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True).lower()
            full = urljoin(BASE, href)

            if (
                "/dizi/tanitim/" in full.lower()
                and (
                    info["name"].lower() in text
                    or info["slug"] in full.lower()
                )
            ):
                print(f"  TANITIM: {full}")
                return full

    print("  Tanıtım sayfası bulunamadı.")
    return None


# ==================================================
# BÖLÜM NUMARASINI BUL
# ==================================================

def get_episode_number(url, title=""):
    text = unquote(url + " " + title).lower()

    patterns = [
        r"bolum[-_ ](\d+)",
        r"(\d+)[-_. ]bolum",
        r"bölüm[-_ ](\d+)",
        r"(\d+)[-_. ]bölüm"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    return None


# ==================================================
# DİZİNİN BÖLÜM LİNKLERİNİ TOPLA
# ==================================================

def get_episode_links(series_url, info):
    source = get_page(series_url)

    if not source:
        return []

    soup = BeautifulSoup(source, "html.parser")
    links = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(BASE, href)
        lower_url = full.lower()

        if "/dizi/tum_bolumler/" not in lower_url:
            continue

        if info["slug"] not in lower_url:
            continue

        title = a.get_text(" ", strip=True)
        number = get_episode_number(full, title)

        if number is None:
            continue

        # Fragman ve kısa videoları alma
        excluded = [
            "fragman",
            "on-izleme",
            "sahne",
            "kamera-arkasi",
            "tanitim",
            "roportaj"
        ]

        if any(word in lower_url for word in excluded):
            continue

        if any(word in title.lower() for word in excluded):
            continue

        links[number] = full

    result = sorted(
        links.items(),
        key=lambda item: item[0],
        reverse=True
    )

    print(f"  Bulunan bölüm: {len(result)}")

    for number, url in result[:LIMIT]:
        print(f"  Bölüm {number}: {url}")

    return result[:LIMIT]


# ==================================================
# M3U8 ADRESİNİ ÇIKAR
# ==================================================

def extract_m3u8(source):
    if not source:
        return None

    source = html.unescape(source)
    source = source.replace("\\/", "/")
    source = source.replace("\\u0026", "&")

    soup = BeautifulSoup(source, "html.parser")

    # 1. data-hope-video JSON
    for tag in soup.find_all(attrs={"data-hope-video": True}):
        raw = tag.get("data-hope-video")

        try:
            data = json.loads(html.unescape(raw))

            media = data.get("media", {})
            videos = media.get("m3u8", [])

            if isinstance(videos, dict):
                videos = [videos]

            for video in videos:
                if isinstance(video, dict):
                    url = video.get("src")

                    if url and ".m3u8" in url.lower():
                        return url.replace("\\/", "/")

                elif isinstance(video, str):
                    if ".m3u8" in video.lower():
                        return video.replace("\\/", "/")

        except Exception:
            pass

    # 2. Sayfa içerisindeki M3U8 bağlantıları
    patterns = [
        r'https?://vmcdn\.ciner\.com\.tr/ht/[^"\'\s<>]+?\.m3u8[^"\'\s<>]*',
        r'https?://[^"\'\s<>]+\.m3u8(?:\?[^"\'\s<>]*)?'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, source, re.I)

        for url in matches:
            url = html.unescape(url)
            url = url.replace("\\/", "/")
            url = url.rstrip("\\)")

            if ".m3u8" in url.lower():
                return url

    return None


def get_vmcdn(episode_url):
    print("  M3U8 aranıyor...")

    source = get_page(episode_url)

    if not source:
        return None

    return extract_m3u8(source)


# ==================================================
# POSTER BUL
# ==================================================

def get_poster(series_url, slug):
    print("  POSTER ARANIYOR...")

    source = get_page(series_url)
    candidates = []

    if source:
        soup = BeautifulSoup(source, "html.parser")

        # 1. SEO görselleri
        for meta in soup.find_all("meta"):
            prop = (
                meta.get("property", "")
                + " "
                + meta.get("name", "")
            ).lower()

            if "og:image" in prop or "twitter:image" in prop:
                content = meta.get("content")

                if content:
                    candidates.append(urljoin(BASE, content))

        # 2. Sayfadaki resimler
        for img in soup.find_all("img"):
            for attr in [
                "src",
                "data-src",
                "data-original",
                "data-lazy-src"
            ]:
                value = img.get(attr)

                if value:
                    candidates.append(urljoin(BASE, value))

            # srcset
            srcset = img.get("srcset", "")

            for item in srcset.split(","):
                value = item.strip().split(" ")[0]

                if value:
                    candidates.append(urljoin(BASE, value))

        # 3. HTML içerisindeki görsel adresleri
        pattern = (
            r'https?://(?:mo\.ciner\.com\.tr|'
            r'im\.showtv\.com\.tr)/[^"\'\s<>]+\.(?:jpg|jpeg|png|webp)'
        )

        candidates.extend(re.findall(pattern, source, re.I))

    # 4. Bilinen Show TV afiş adresi biçimi
    candidates.append(
        f"https://mo.ciner.com.tr/showtv/iu/"
        f"1920x1080_6/{slug}.jpg"
    )

    # Tekrarları temizle
    unique = list(dict.fromkeys(
        html.unescape(url).replace("\\/", "/")
        for url in candidates
        if url
    ))

    # Dizi adına uygun görselleri öne al
    unique.sort(
        key=lambda url: slug.lower() not in url.lower()
    )

    # Görsel adresini doğrula
    for url in unique:
        try:
            r = scraper.get(
                url,
                timeout=15,
                stream=True
            )

            content_type = r.headers.get(
                "Content-Type", ""
            ).lower()

            valid = (
                r.status_code == 200
                and "image/" in content_type
            )

            r.close()

            if valid:
                print("  POSTER BULUNDU!")
                print(" ", url)
                return url

        except Exception:
            continue

    print("  POSTER BULUNAMADI!")
    return ""


# ==================================================
# M3U KAYIT OLUŞTUR
# ==================================================

def make_entry(name, number, stream, poster):
    title = f"TR: {name} - {number}. Bölüm"
    logo = poster or ""

    return (
        f'#EXTINF:-1 tvg-name="{title}" '
        f'tvg-logo="{logo}" '
        f'group-title="{GROUP}",{title}\n'
        f'{stream}'
    )


# ==================================================
# M3U BLOKLARINI OKU
# ==================================================

def read_m3u_blocks(path):
    blocks = []

    if not os.path.exists(path):
        return blocks

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        errors="ignore"
    ) as f:
        lines = f.read().splitlines()

    current = []

    for line in lines:
        if line.startswith("#EXTINF:"):
            if current:
                blocks.append(current)

            current = [line]

        elif current:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


# ==================================================
# MIRTI68.M3U İÇİNE TEKRARSIZ EKLE
# ==================================================

def update_mirti(new_entries):
    if not new_entries:
        print("Yeni kayıt yok. MIRTI korunuyor.")
        return

    old_blocks = read_m3u_blocks(MIRTI)

    # Yeni kayıtların başlıklarını belirle
    new_titles = set()

    for entry in new_entries:
        first_line = entry.splitlines()[0]

        if "," in first_line:
            new_titles.add(first_line.split(",", 1)[1].strip())

    preserved = []

    for block in old_blocks:
        first_line = block[0]

        # SHOW grubundaki eski kaydı kontrol et
        is_show = f'group-title="{GROUP}"' in first_line

        if is_show:
            old_title = (
                first_line.split(",", 1)[1].strip()
                if "," in first_line
                else ""
            )

            # Aynı bölümün eski kaydını yenisiyle değiştir.
            # Diğer eski SHOW bölümlerini koru.
            if old_title in new_titles:
                continue

        preserved.append("\n".join(block).strip())

    all_entries = preserved + new_entries

    with open(
        MIRTI,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("#EXTM3U\n")

        for entry in all_entries:
            f.write(entry.strip() + "\n\n")

    print(
        f"\nMIRTI GÜNCELLENDİ: "
        f"{len(new_entries)} yeni kayıt"
    )


# ==================================================
# ANA PROGRAM
# ==================================================

def main():
    print("=" * 50)
    print("SHOW TV - OTOMATİK SON 3 BÖLÜM")
    print("=" * 50)

    entries = []

    for key, info in SERIES.items():
        print("\n" + "=" * 40)
        print(info["name"])
        print("=" * 40)

        series_url = find_series_page(key, info)

        if not series_url:
            continue

        # DÜZELTİLDİ: slug parametresi de gönderiliyor.
        poster = get_poster(
            series_url,
            info["slug"]
        )

        episodes = get_episode_links(
            series_url,
            info
        )

        if not episodes:
            print("  Bölüm bulunamadı.")
            continue

        added = 0

        for number, episode_url in episodes:
            print(f"\n  {number}. BÖLÜM")

            stream = get_vmcdn(episode_url)

            if not stream:
                print("  M3U8 BULUNAMADI!")
                time.sleep(1)
                continue

            entry = make_entry(
                info["name"],
                number,
                stream,
                poster
            )

            entries.append(entry)
            added += 1

            print("  BAŞARILI!")
            time.sleep(1)

        print(
            f"\n{info['name']}: "
            f"{added} bölüm eklendi."
        )

    # Hiç kayıt yoksa eski listeleri koru
    if not entries:
        print("\nHİÇ YENİ YAYIN BULUNAMADI.")
        print("Mevcut M3U dosyaları korunuyor.")
        return

    # showtv.m3u
    with open(
        M3U,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("#EXTM3U\n")

        for entry in entries:
            f.write(entry.strip() + "\n\n")

    print("\n" + "=" * 50)
    print(f"{M3U}: {len(entries)} kayıt oluşturuldu.")

    # Ana listeye ekle
    update_mirti(entries)

    print("\nİŞLEM TAMAMLANDI!")
    print("=" * 50)


if __name__ == "__main__":
    main()
================================
# MIRTI68.M3U İÇİNE TEKRARSIZ EKLE
# ==================================================

def update_mirti(new_entries):
    if not new_entries:
        print("Yeni kayıt yok. MIRTI korunuyor.")
        return

    old_blocks = read_m3u_blocks(MIRTI)

    # Yeni kayıtların başlıklarını belirle
    new_titles = set()

    for entry in new_entries:
        first_line = entry.splitlines()[0]

        if "," in first_line:
            new_titles.add(first_line.split(",", 1)[1].strip())

    preserved = []

    for block in old_blocks:
        first_line = block[0]

        # SHOW grubundaki eski kaydı kontrol et
        is_show = f'group-title="{GROUP}"' in first_line

        if is_show:
            old_title = (
                first_line.split(",", 1)[1].strip()
                if "," in first_line
                else ""
            )

            # Aynı bölümün eski kaydını yenisiyle değiştir.
            # Diğer eski SHOW bölümlerini koru.
            if old_title in new_titles:
                continue

        preserved.append("\n".join(block).strip())

    all_entries = preserved + new_entries

    with open(
        MIRTI,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("#EXTM3U\n")

        for entry in all_entries:
            f.write(entry.strip() + "\n\n")

    print(
        f"\nMIRTI GÜNCELLENDİ: "
        f"{len(new_entries)} yeni kayıt"
    )


# ==================================================
# ANA PROGRAM
# ==================================================

def main():
    print("=" * 50)
    print("SHOW TV - OTOMATİK SON 3 BÖLÜM")
    print("=" * 50)

    entries = []

    for key, info in SERIES.items():
        print("\n" + "=" * 40)
        print(info["name"])
        print("=" * 40)

        series_url = find_series_page(key, info)

        if not series_url:
            continue

        # DÜZELTİLDİ: slug parametresi de gönderiliyor.
        poster = get_poster(
            series_url,
            info["slug"]
        )

        episodes = get_episode_links(
            series_url,
            info
        )

        if not episodes:
            print("  Bölüm bulunamadı.")
            continue

        added = 0

        for number, episode_url in episodes:
            print(f"\n  {number}. BÖLÜM")

            stream = get_vmcdn(episode_url)

            if not stream:
                print("  M3U8 BULUNAMADI!")
                time.sleep(1)
                continue

            entry = make_entry(
                info["name"],
                number,
                stream,
                poster
            )

            entries.append(entry)
            added += 1

            print("  BAŞARILI!")
            time.sleep(1)

        print(
            f"\n{info['name']}: "
            f"{added} bölüm eklendi."
        )

    # Hiç kayıt yoksa eski listeleri koru
    if not entries:
        print("\nHİÇ YENİ YAYIN BULUNAMADI.")
        print("Mevcut M3U dosyaları korunuyor.")
        return

    # showtv.m3u
    with open(
        M3U,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("#EXTM3U\n")

        for entry in entries:
            f.write(entry.strip() + "\n\n")

    print("\n" + "=" * 50)
    print(f"{M3U}: {len(entries)} kayıt oluşturuldu.")

    # Ana listeye ekle
    update_mirti(entries)

    print("\nİŞLEM TAMAMLANDI!")
    print("=" * 50)


if __name__ == "__main__":
    main()
  for block in old_entries:

        info = "\n".join(block)

        if f'group-title="{GROUP}"' not in info:
            preserved.append("\n".join(block).strip())

    # Yeni kayıtları ekle
    all_entries = preserved + new_entries

    with open(
        MIRTI,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for entry in all_entries:

            f.write(entry.strip() + "\n\n")

    print(
        f"\nMIRTI GÜNCELLENDİ: "
        f"{len(new_entries)} yeni kayıt"
    )


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 50)
    print("SHOW TV - OTOMATİK SON 3 BÖLÜM")
    print("=" * 50)

    entries = []

    for key, info in SERIES.items():

        print("\n" + "=" * 40)
        print(info["name"])
        print("=" * 40)

        series_url = find_series_page(key, info)

        if not series_url:
            continue

        poster = get_poster(series_url)

        episodes = get_episode_links(
            series_url,
            info
        )

        if not episodes:
            print("  Bölüm bulunamadı.")
            continue

        added = 0

        for number, episode_url in episodes:

            print(f"\n  {number}. BÖLÜM")

            stream = get_vmcdn(episode_url)

            if not stream:

                print("  M3U8 BULUNAMADI!")
                time.sleep(1)
                continue

            entry = make_entry(
                info["name"],
                number,
                stream,
                poster
            )

            entries.append(entry)

            added += 1

            print("  BAŞARILI!")

            time.sleep(1)

        print(
            f"\n{info['name']}: "
            f"{added} bölüm eklendi."
        )

    # Hiç kayıt yoksa eski listeleri koru
    if not entries:

        print("\nHİÇ YENİ YAYIN BULUNAMADI.")
        print("Mevcut M3U dosyaları korunuyor.")
        return

    # showtv.m3u
    with open(
        M3U,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for entry in entries:

            f.write(entry.strip() + "\n\n")

    print("\n" + "=" * 50)
    print(f"{M3U}: {len(entries)} kayıt oluşturuldu.")

    # Ana listeye ekle
    update_mirti(entries)

    print("\nİŞLEM TAMAMLANDI!")
    print("=" * 50)


if __name__ == "__main__":
    main()
