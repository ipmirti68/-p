
import re
import os
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

BASE = "https://www.atv.com.tr"
OUTPUT = "atv_playlist.m3u"
MIRTI = "mirti68.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
}

# ATV'nin resmi RSS sayfasında yayımlanan dizi video akışları.
SLUGS = [
    "alti-ustu-istanbul",
    "gunesin-dogdugu-yer",
    "abi",
    "ask-ve-taht",
    "mercan-kosk",
    "kor-nokta",
    "kurulus-osman",
    "sahipsizler",
    "karadut",
    "kardeslerim",
    "hercai",
    "bir-kucuk-gun-isigi",
    "destan",
    "kader-oyunlari",
    "eskiya-dunyaya-hukumdar-olmaz",
]

session = requests.Session()
session.headers.update(HEADERS)


def get(url):
    response = session.get(url, timeout=25)
    response.raise_for_status()
    return response


def get_video_feeds():
    """Resmi ATV RSS sayfasından dizi video RSS adreslerini bul."""
    feeds = set()

    try:
        html = get(BASE + "/rss-bilgi").text
        pattern = r'https?://www\.atv\.com\.tr/rss/[^"\'<>\s]+/video\.xml'
        feeds.update(re.findall(pattern, html, re.I))
    except requests.RequestException as exc:
        print("RSS dizin sayfası alınamadı:", exc)

    # RSS dizininden bulunamayan diziler için yedek adresler.
    for slug in SLUGS:
        feeds.add(f"{BASE}/rss/diziler/{slug}/video.xml")
        feeds.add(f"{BASE}/rss/klasik-diziler/{slug}/video.xml")

    return sorted(feeds)


def get_episode_pages(feed_url):
    """RSS içindeki bölüm başlıklarını ve sayfa adreslerini al."""
    try:
        response = get(feed_url)
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as exc:
        print("RSS okunamadı:", feed_url, str(exc))
        return []

    episodes = []

    for item in root.iter():
        if item.tag.split("}")[-1].lower() != "item":
            continue

        title = ""
        page_url = ""

        for child in item:
            tag = child.tag.split("}")[-1].lower()

            if tag == "title":
                title = (child.text or "").strip()

            elif tag == "link":
                page_url = (child.text or "").strip()

            elif tag == "enclosure":
                # Yalnızca enclosure gerçekten bir video URL'si veriyorsa.
                candidate = child.attrib.get("url", "")
                if candidate:
                    page_url = page_url or candidate

        if title and page_url:
            episodes.append((title, urljoin(BASE, page_url)))

    return episodes


def get_stream(page_url):
    """Bölüm sayfasındaki açık HLS bağlantılarını ara."""
    try:
        html = get(page_url).text
    except requests.RequestException as exc:
        print("Bölüm sayfası alınamadı:", page_url, str(exc))
        return ""

    html = html.replace("\\/", "/").replace("\\u0026", "&")

    patterns = [
        r'https?://[^"\'\s<>]+?\.m3u8(?:\?[^"\'\s<>]*)?',
        r'"(?:videoUrl|streamUrl|file|src)"\s*:\s*"([^"]+\.m3u8[^"]*)"',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, html, re.I):
            candidate = match.strip().rstrip("\\")
            if candidate.startswith("http"):
                return candidate

    return ""


def make_playlist():
    entries = []
    seen = set()
    feeds = get_video_feeds()

    print("Kontrol edilecek RSS sayısı:", len(feeds))

    for feed in feeds:
        episodes = get_episode_pages(feed)

        if episodes:
            print(f"RSS: {feed} -> {len(episodes)} kayıt")

        for title, page_url in episodes:
            if page_url in seen:
                continue

            seen.add(page_url)
            stream = get_stream(page_url)

            if stream:
                entries.append({
                    "title": title,
                    "page": page_url,
                    "stream": stream,
                })
                print("OK:", title)
            else:
                print("Yayın adresi bulunamadı:", title)

            time.sleep(0.3)

    if not entries:
        print("HATA: Oynatılabilir yayın adresi bulunamadı.")
        print("Mevcut M3U dosyaları korunuyor.")
        return False

    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")

        for entry in entries:
            title = entry["title"].replace('"', "'")
            file.write(
                f'#EXTINF:-1 tvg-name="{title}" '
                f'group-title="ATV Dizileri",{title}\n'
            )
            file.write(entry["stream"] + "\n")

    print(f"{OUTPUT} oluşturuldu: {len(entries)} bölüm")
    return True


def read_blocks(content):
    lines = content.splitlines()
    header = next(
        (line for line in lines if line.startswith("#EXTM3U")),
        "#EXTM3U"
    )

    blocks = []
    current = []

    for line in lines:
        if line.startswith("#EXTM3U"):
            continue

        if line.startswith("#EXTINF"):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)

    if current:
        blocks.append(current)

    return header, blocks


def append_to_mirti():
    if not os.path.exists(MIRTI):
        print(f"{MIRTI} bulunamadı; yalnızca {OUTPUT} hazırlandı.")
        return

    with open(OUTPUT, encoding="utf-8") as file:
        new_content = file.read()

    with open(MIRTI, encoding="utf-8", errors="replace") as file:
        old_content = file.read()

    header, old_blocks = read_blocks(old_content)
    _, new_blocks = read_blocks(new_content)

    # Yalnızca önceki ATV Dizileri grubunu yenile.
    kept = [
        block for block in old_blocks
        if not any("ATV Dizileri" in line for line in block)
    ]

    # Aynı yayın adresini iki kere ekleme.
    urls = {
        line.strip()
        for block in kept
        for line in block
        if line.strip().startswith(("http://", "https://"))
    }

    added = 0

    for block in new_blocks:
        block_urls = [
            line.strip() for line in block
            if line.strip().startswith(("http://", "https://"))
        ]

        if block_urls and not any(url in urls for url in block_urls):
            kept.append(block)
            urls.update(block_urls)
            added += 1

    with open(MIRTI, "w", encoding="utf-8", newline="\n") as file:
        file.write(header + "\n")
        for block in kept:
            file.write("\n".join(block).rstrip() + "\n\n")

    print(f"{MIRTI}: {added} yeni ATV bölümü eklendi.")


if __name__ == "__main__":
    if make_playlist():
        append_to_mirti()
