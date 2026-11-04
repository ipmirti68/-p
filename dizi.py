
#!/usr/bin/env python3
# MIRTI 68 - Resmi TV dizileri tarayici
# Yalnizca herkese acik medya adreslerini dener.
# DRM ve oturum korumalarini asmaz.

import os
import re
import time
import html
from urllib.parse import urljoin, urlparse, urldefrag

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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}

CHANNELS = [
    {
        "name": "SHOW TV",
        "group": "📺 SHOW TV Dizileri",
        "home": "https://www.showtv.com.tr/",
        "lists": ["https://www.showtv.com.tr/diziler"],
        "known": [
             ("Kızılcık Şerbeti", "https://www.showtv.com.tr/dizi/tanitim/kizilcik-serbeti/2875"),
            ("Muhtemel Aşk", "https://www.showtv.com.tr/dizi/tanitim/muhtemel-ask/3072"),
            ("Sevdan Bir Ateş", "https://www.showtv.com.tr/dizi/tanitim/sevdan-bir-ates/3087"),
        ],
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

EXCLUDED_WORDS = (
    "fragman", "fragmani", "teaser", "tanitim",
    "on izleme", "ozet", "son sahne", "sahne",
    "sahneler", "kamera arkasi", "cekim hatalari",
    "test", "testler", "ozel test", "galeri",
    "foto galeri", "oyuncu", "haber", "roportaj",
    "shorts", "incelemesi", "yorumlari",
    "set arkasi",
)

EXCLUDED_PATH_PARTS = (
    "fragman", "sahne", "test", "galeri",
    "foto", "haber", "oyuncu", "kamera-arkasi",
    "set-arkasi", "program", "yayin-akisi",
)


def normalize(value):
    value = html.unescape(value or "").lower()
    replacements = {
        "ı": "i", "ş": "s", "ğ": "g",
        "ü": "u", "ö": "o", "ç": "c",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value).strip()


def clean_text(value):
    return re.sub(
        r"\s+", " ", html.unescape(value or "")
    ).strip()


def valid_url(url):
    return urlparse(url).scheme in ("http", "https")


def same_host(url_a, url_b):
    host_a = (
        urlparse(url_a).hostname or ""
    ).lower().removeprefix("www.")

    host_b = (
        urlparse(url_b).hostname or ""
    ).lower().removeprefix("www.")

    return bool(host_a and host_a == host_b)


def forbidden_content(text, url):
    sample = normalize(clean_text(text) + " " + url)
    return any(
        normalize(word) in sample
        for word in EXCLUDED_WORDS
    )


def forbidden_path(url):
    path = normalize(urlparse(url).path)
    parts = [p for p in path.split("/") if p]

    return any(
        bad in part
        for part in parts
        for bad in EXCLUDED_PATH_PARTS
    )


def fetch_page(url):
    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        if response.status_code != 200:
            print(f"[HTTP {response.status_code}] {url}")
            return None, None

        final_url = urldefrag(response.url)[0]

        if not valid_url(final_url):
            return None, None

        if not same_host(url, final_url):
            print(f"[YONLENDIRME ATLANDI] {final_url}")
            return None, None

        if forbidden_path(final_url):
            return None, None

        response.encoding = (
            response.apparent_encoding or "utf-8"
        )

        soup = BeautifulSoup(
            response.text, "html.parser"
        )

        return response, soup

    except requests.RequestException as exc:
        print(f"[SAYFA HATASI] {url}: {exc}")
        return None, None


def get_soup(url):
    _, soup = fetch_page(url)
    return soup


def get_episode_number(text, url):
    sample = normalize(clean_text(text) + " " + url)

    patterns = (
        r"(\d{1,4})\s*\.?\s*bolum\b",
        r"\bbolum[-_/ ]*(\d{1,4})\b",
        r"\bepisode[-_/ ]*(\d{1,4})\b",
    )

    for pattern in patterns:
        match = re.search(pattern, sample)
        if match:
            return int(match.group(1))

    return None


def is_full_episode(text, url):
    if not valid_url(url):
        return False

    if forbidden_content(text, url):
        return False

    if forbidden_path(url):
        return False

    return get_episode_number(text, url) is not None


def discover_series(channel):
    found = {
        name: url
        for name, url in channel["known"]
    }

    roots = [channel["home"]] + channel["lists"]

    for root in roots:
        soup = get_soup(root)

        if not soup:
            continue

        for a in soup.find_all("a", href=True):
            title = clean_text(
                a.get_text(" ", strip=True)
            )

            href = urldefrag(
                urljoin(root, a["href"])
            )[0]

            if not title or not valid_url(href):
                continue

            if not same_host(channel["home"], href):
                continue

            if forbidden_content(title, href):
                continue

            if forbidden_path(href):
                continue

            path = urlparse(href).path.strip("/")
            parts = [p for p in path.split("/") if p]

            if not parts or len(parts) > 3:
                continue

            if get_episode_number(title, href):
                continue

            if any(
                word in normalize(path)
                for word in ("bolum", "episode", "video", "izle")
            ):
                continue

            if normalize(title) in (
                "detaylar", "izle", "tumu",
                "diziler", "dizi", "ana sayfa",
            ):
                continue

            found.setdefault(title, href)

    checked = []
    seen = set()

    for name, url in found.items():
        if url in seen:
            continue

        seen.add(url)
        response, _ = fetch_page(url)

        if response is not None:
            checked.append((name, response.url))

        time.sleep(0.2)

    return checked


def find_episodes(series_url):
    response, soup = fetch_page(series_url)

    if not soup:
        return []

    candidates = {}
    base_url = response.url

    def add_candidate(title, href):
        href = urldefrag(
            urljoin(base_url, href)
        )[0]

        if not valid_url(href):
            return

        if not same_host(base_url, href):
            return

        if href.rstrip("/") == base_url.rstrip("/"):
            return

        if not is_full_episode(title, href):
            return

        number = get_episode_number(title, href)

        if number is None:
            return

        candidates[number] = href

    for a in soup.find_all("a", href=True):
        add_candidate(
            clean_text(a.get_text(" ", strip=True)),
            a["href"],
        )

    for option in soup.find_all("option"):
        add_candidate(
            clean_text(option.get_text(" ", strip=True)),
            option.get("value", ""),
        )

    valid_candidates = []

    for number, url in sorted(
        candidates.items(),
        key=lambda item: item[0],
        reverse=True,
    ):
        page_response, _ = fetch_page(url)

        if page_response is None:
            continue

        final_url = urldefrag(
            page_response.url
        )[0]

        if forbidden_content("", final_url):
            continue

        if forbidden_path(final_url):
            continue

        valid_candidates.append((number, final_url))

        if len(valid_candidates) >= MAX_EPISODES_PER_SERIES:
            break

        time.sleep(0.2)

    return valid_candidates


def extract_direct_media(page_url):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": REQUEST_TIMEOUT,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                page_url,
                download=False,
            )

        if not info:
            return ""

        formats = info.get("formats") or []

        formats.sort(
            key=lambda f: (
                "m3u8" in str(
                    f.get("protocol", "")
                ).lower(),
                f.get("height") or 0,
            ),
            reverse=True,
        )

        for fmt in formats:
            media_url = fmt.get("url") or ""

            if valid_url(media_url):
                return media_url

        media_url = info.get("url") or ""

        if valid_url(media_url):
            return media_url

    except Exception as exc:
        print(f"[MEDYA YOK/KORUMALI] {str(exc)[:180]}")

    return ""


def safe_filename(value):
    value = re.sub(
        r"[^\w.-]+",
        "_",
        value,
        flags=re.UNICODE,
    )

    return value.strip("_") or "kanal"


def read_master_blocks():
    if not os.path.exists(MASTER_FILE):
        return []

    try:
        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig",
        ) as file:
            content = file.read()

    except OSError as exc:
        print(f"[ANA LISTE OKUNAMADI] {exc}")
        return []

    blocks = re.findall(
        r"(?m)^#EXTINF:[\s\S]*?(?=^#EXTINF:|\Z)",
        content,
    )

    owned_groups = [
        channel["group"]
        for channel in CHANNELS
    ]

    kept = []

    for block in blocks:
        if any(group in block for group in owned_groups):
            continue

        if re.search(r"(?m)^https?://", block):
            kept.append(block.strip())

    return kept


def scan_channel(channel):
    print("\n" + "=" * 55)
    print(f"{channel['name']} taraniyor")
    print("=" * 55)

    series_list = discover_series(channel)

    print(
        f"Bulunan dizi sayfasi: {len(series_list)}"
    )

    entries = []

    for series_name, series_url in series_list:
        print(f"\n[DIZI] {series_name}")

        episode_list = find_episodes(series_url)

        if not episode_list:
            print("Bolum adayi bulunamadi.")
            continue

        for number, episode_url in episode_list:
            print(f"{number}. bolum medya kontrolu")

            media_url = extract_direct_media(
                episode_url
            )

            if not media_url:
                print("Dog rudan medya bulunamadi, atlandi.")
                continue

            title = (
                f"{series_name} - {number}. Bölüm"
            )

            title = title.replace('"', "'").replace(
                "\n", " "
            )

            entries.append(
                f'#EXTINF:-1 tvg-name="{title}" '
                f'group-title="{channel["group"]}",'
                f'{title}\n'
                f'{media_url}\n'
            )

            time.sleep(PAUSE_SECONDS)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    out_file = os.path.join(
        OUTPUT_DIR,
        safe_filename(
            channel["name"].lower()
        ) + ".m3u",
    )

    if entries:
        with open(
            out_file,
            "a",
            encoding="utf-8",
        ) as file:
            file.write("#EXTM3U\n")
            file.writelines(entries)

        print(f"{out_file}: {len(entries)} kayit")

    else:
        print("Oynatilabilir medya bulunamadi.")

    return entries


def main():
    print("MIRTI 68 - 6 KANAL DIZI TARAMA")
    print("Dizi basina en fazla 3 bolum")
    print("DRM ve oturum korumasi asilmaz.")

    all_new_entries = []

    for channel in CHANNELS:
        try:
            entries = scan_channel(channel)
            all_new_entries.extend(entries)

        except KeyboardInterrupt:
            print("Tarama durduruldu.")
            break

        except Exception as exc:
            print(
                f"[KANAL HATASI] "
                f"{channel['name']}: {exc}"
            )

    if not all_new_entries:
        print("Yeni medya kaydi bulunamadi.")
        print("Ana M3U degistirilmedi.")
        return

    old_blocks = read_master_blocks()
    temp_file = MASTER_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8",
    ) as file:
        file.write("#EXTM3U\n")

        for block in old_blocks:
            file.write(block + "\n")

        for entry in all_new_entries:
            file.write(entry)

    os.replace(temp_file, MASTER_FILE)

    print("Tarama tamamlandi.")
    print(f"Ana liste: {MASTER_FILE}")
    print(f"Yeni kayit: {len(all_new_entries)}")
    print(f"Kanal dosyalari: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
