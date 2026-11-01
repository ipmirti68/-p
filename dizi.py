#!/usr/bin/env python3
# MIRTI 68 - Resmi TV dizileri bolum tarayici
# Yalnizca herkese acik/resmi sayfalardaki dogrudan medya adreslerini dener.
# DRM, oturum veya erisim korumalarini asmaya calismaz.

import os
import re
import time
import html
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import yt_dlp

MASTER_FILE = "mirti68.m3u"
OUTPUT_DIR = "mirti68_kanallar"
MAX_EPISODES_PER_SERIES = 3
REQUEST_TIMEOUT = 25
PAUSE_SECONDS = 0.7

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}

# Dizi sayfalari resmi liste sayfalarindan otomatik bulunur.
CHANNELS = [
    {
        "name": "SHOW TV",
        "group": "📺 SHOW TV Dizileri",
        "home": "https://www.showtv.com.tr/",
        "lists": ["https://www.showtv.com.tr/diziler"],
        "known": [],
    },
    {
        "name": "STAR TV",
        "group": "📺 STAR TV Dizileri",
        "home": "https://www.startv.com.tr/",
        "lists": ["https://www.startv.com.tr/dizi"],
        "known": [],
    },
    {
        "name": "ATV",
        "group": "📺 ATV Dizileri",
        "home": "https://www.atv.com.tr/",
        "lists": ["https://www.atv.com.tr/diziler"],
        "known": [],
    },
    {
        "name": "KANAL D",
        "group": "📺 KANAL D Dizileri",
        "home": "https://www.kanald.com.tr/",
        "lists": ["https://www.kanald.com.tr/diziler"],
        "known": [
            ("Uzak Şehir", "https://www.kanald.com.tr/uzak-sehir"),
            ("Haysiyet", "https://www.kanald.com.tr/haysiyet"),
            ("Güller ve Günahlar", "https://www.kanald.com.tr/guller-ve-gunahlar"),
            ("Daha 17", "https://www.kanald.com.tr/daha-17"),
        ],
    },
    {
        "name": "TRT 1",
        "group": "📺 TRT 1 Dizileri",
        "home": "https://www.trt1.com.tr/",
        "lists": ["https://www.trt1.com.tr/diziler?archive=false"],
        "known": [
            ("Gönül Dağı", "https://www.trt1.com.tr/diziler/gonul-dagi"),
            ("Teşkilat", "https://www.trt1.com.tr/diziler/teskilat"),
            ("Mehmed: Fetihler Sultanı", "https://www.trt1.com.tr/diziler/mehmed-fetihler-sultani"),
            ("Taşacak Bu Deniz", "https://www.trt1.com.tr/diziler/tasacak-bu-deniz"),
            ("Evlilik Güzeldir", "https://www.trt1.com.tr/diziler/evlilik-guzeldir"),
            ("Kod Adı Kırlangıç", "https://www.trt1.com.tr/diziler/kod-adi-kirlangic"),
        ],
    },
    {
        "name": "NOW TV",
        "group": "📺 NOW TV Dizileri",
        "home": "https://www.nowtv.com.tr/",
        "lists": ["https://www.nowtv.com.tr/"],
        "known": [
            ("Sevdam Karadeniz", "https://www.nowtv.com.tr/Sevdam-Karadeniz"),
            ("Anne Yarısı", "https://www.nowtv.com.tr/Anne-Yarisi"),
            ("Yeraltı", "https://www.nowtv.com.tr/Yeralti"),
            ("Halef: Köklerin Çağrısı", "https://www.nowtv.com.tr/Halef-Koklerin-Cagrisi"),
            ("Ömür Usta", "https://www.nowtv.com.tr/Omur-Usta"),
        ],
    },
]

session = requests.Session()
session.headers.update(HEADERS)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def get_soup(url):
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        print(f"  [SAYFA HATASI] {url} -> {exc}")
        return None


def clean_text(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def valid_url(url):
    return url.startswith("https://") or url.startswith("http://")


def discover_series(channel):
    found = {name: url for name, url in channel["known"]}
    roots = [channel["home"]] + channel["lists"]

    for root in roots:
        soup = get_soup(root)
        if not soup:
            continue

        for a in soup.find_all("a", href=True):
            title = clean_text(a.get_text(" ", strip=True))
            href = urljoin(root, a["href"].split("#")[0])

            if not title or not valid_url(href):
                continue

            low = (title + " " + href).lower()
            if any(word in low for word in (
                "fragman", "fragmani", "ön-izleme", "on-izleme",
                "ozel-sahne", "özel-sahne", "haber", "oyuncu",
                "foto", "galeri", "canli-yayin", "yayin-akisi",
                "programlar", "arsiv", "archive"
            )):
                continue

            host = urlparse(channel["home"]).netloc
            if urlparse(href).netloc not in ("", host):
                continue

            path = urlparse(href).path.strip("/")
            parts = [p for p in path.split("/") if p]
            if not parts:
                continue

            # Liste sayfalarindan bulunan dizi sayfalari genellikle tek/iki slug derinligindedir.
            if len(parts) > 2:
                continue

            if any(x in path.lower() for x in (
                "/bolum", "/episode", "/video", "/izle/"
            )):
                continue

            if title.lower() in ("detaylar", "izle", "tümü", "diziler", "dizi"):
                continue

            found.setdefault(title, href)

    # Bilinen URL'leri de kontrol et; sayfa gercekten acilmiyorsa yine sonraki adimda atlanir.
    return list(found.items())


def get_episode_number(text, url):
    sample = (clean_text(text) + " " + url).lower()
    sample = sample.replace("ü", "u").replace("ö", "o").replace("ş", "s")
    patterns = [
        r"(\d{1,4})\s*\.?\s*bolum",
        r"bolum[-_/ ]*(\d{1,4})",
        r"episode[-_/ ]*(\d{1,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, sample)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
    return None


def is_full_episode(text, url):
    value = (clean_text(text) + " " + url).lower()
    value = value.replace("ı", "i").replace("ü", "u").replace("ö", "o")
    excluded = (
        "fragman", "teaser", "on izleme", "ön izleme",
        "ozet", "özet", "son sahne", "sahne", "kamera arkasi",
        "kamera arkası", "foto", "galeri", "shorts", "d shorts",
        "oyuncu", "haber", "tanitim", "tanıtım"
    )
    if any(word in value for word in excluded):
        return False
    return get_episode_number(text, url) is not None


def find_episodes(series_url):
    soup = get_soup(series_url)
    if not soup:
        return []

    candidates = {}
    base_host = urlparse(series_url).netloc

    # Dizi sayfasindaki bolum listesi linkleri.
    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        href = urljoin(series_url, a["href"].split("#")[0])

        if not valid_url(href) or urlparse(href).netloc != base_host:
            continue
        if href.rstrip("/") == series_url.rstrip("/"):
            continue
        if not is_full_episode(title, href):
            continue

        number = get_episode_number(title, href)
        if number is not None:
            candidates[number] = href

    # Bazı sitelerde bolum linkleri select option icinde olabilir.
    for option in soup.find_all("option"):
        title = clean_text(option.get_text(" ", strip=True))
        href = option.get("value", "")
        href = urljoin(series_url, href)
        if is_full_episode(title, href):
            number = get_episode_number(title, href)
            if number is not None:
                candidates[number] = href

    return sorted(candidates.items(), key=lambda item: item[0], reverse=True)[:MAX_EPISODES_PER_SERIES]


def extract_direct_media(page_url):
    # yt-dlp sadece sayfanin herkese acik medya bilgisini okumayi dener.
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": REQUEST_TIMEOUT,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(page_url, download=False)

        if not info:
            return ""

        formats = info.get("formats") or []
        # HLS tercih edilir; sonra en yuksek cozunurluk.
        formats.sort(
            key=lambda f: (
                "m3u8" in str(f.get("protocol", "")).lower(),
                f.get("height") or 0
            ),
            reverse=True
        )
        for fmt in formats:
            media_url = fmt.get("url") or ""
            if valid_url(media_url):
                return media_url

        media_url = info.get("url") or ""
        if valid_url(media_url):
            return media_url

    except Exception as exc:
        print(f"    [MEDYA YOK/KORUMALI] {str(exc)[:150]}")

    return ""


def safe_filename(value):
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    return value.strip("_") or "kanal"


def read_master_blocks():
    if not os.path.exists(MASTER_FILE):
        return []
    try:
        with open(MASTER_FILE, "r", encoding="utf-8-sig") as file:
            content = file.read()
    except Exception:
        return []

    blocks = re.findall(r"(?m)^#EXTINF:[\s\S]*?(?=^#EXTINF:|\Z)", content)
    owned_groups = [channel["group"] for channel in CHANNELS]
    kept = []
    for block in blocks:
        if any(group in block for group in owned_groups):
            continue
        if re.search(r"(?m)^https?://", block):
            kept.append(block.strip())
    return kept


def scan_channel(channel):
    print("\n" + "=" * 58)
    print(f"{channel['name']} taraniyor")
    print("=" * 58)

    series_list = discover_series(channel)
    print(f"Bulunan dizi adayi: {len(series_list)}")

    entries = []
    for series_name, series_url in series_list:
        print(f"\n[DIZI] {series_name}")
        episode_list = find_episodes(series_url)

        if not episode_list:
            print("  Bolum linki bulunamadi.")
            continue

        for number, episode_url in episode_list:
            print(f"  {number}. bolum -> medya kontrolu")
            media_url = extract_direct_media(episode_url)

            if not media_url:
                print("    M3U'ya eklenmedi (dogrudan medya bulunamadi).")
                continue

            title = f"{series_name} - {number}. Bölüm"
            title = title.replace('"', "'")
            entries.append(
                f'#EXTINF:-1 tvg-name="{title}" group-title="{channel["group"]}",{title}\n'
                f"{media_url}\n"
            )
            time.sleep(PAUSE_SECONDS)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(
        OUTPUT_DIR,
        safe_filename(channel["name"].lower()) + ".m3u"
    )

    if entries:
        with open(out_file, "w", encoding="utf-8") as file:
            file.write("#EXTM3U\n")
            file.writelines(entries)
        print(f"\n{out_file}: {len(entries)} medya kaydi")
    else:
        print("\nBu kanalda dogrudan oynatilabilir medya bulunamadi.")

    return entries


def main():
    print("MIRTI 68 - 6 KANAL RESMI DIZI TARAMA")
    print("Son 3 tam bolum | Fragmanlar haric")
    print("DRM/oturum korumasi asilmadan dogrudan medya aranir.")

    all_new_entries = []
    for channel in CHANNELS:
        try:
            all_new_entries.extend(scan_channel(channel))
        except KeyboardInterrupt:
            print("\nKullanici tarafindan durduruldu.")
            break
        except Exception as exc:
            print(f"\n[KANAL HATASI] {channel['name']}: {exc}")
            continue

    if not all_new_entries:
        print("\nYeni dogrudan medya kaydi bulunamadi.")
        print("Mevcut ana M3U dosyasi degistirilmedi.")
        return

    old_blocks = read_master_blocks()
    temp_file = MASTER_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")
        for block in old_blocks:
            file.write(block + "\n")
        for entry in all_new_entries:
            file.write(entry)

    os.replace(temp_file, MASTER_FILE)
    print("\nBitti!")
    print(f"Ana liste: {MASTER_FILE}")
    print(f"Eklenen yeni kayit: {len(all_new_entries)}")
    print("Kanal bazli M3U dosyalari:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
