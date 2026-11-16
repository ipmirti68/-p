
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - İKİNCİ BAHAR 37 BÖLÜM ARŞİVİ
# ==========================================

CHANNEL_ID = "UC8Nnnhuc9V5YUiYBa4Qdr6A"

RSS_URL = (
    "https://www.youtube.com/feeds/videos.xml"
    f"?channel_id={CHANNEL_ID}"
)

JSON_FILE = "ikinci_bahar_kaynaklar.json"
M3U_FILE = "ikinci_bahar.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

# Her çalışmada en fazla bir yeni HLS denemesi
MAX_HLS_TEST = 1

# ==========================================
# TARİH
# ==========================================

def now_utc():
    return datetime.now(timezone.utc)


def parse_date(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


# ==========================================
# ESKİ JSON KAYITLARINI KORU
# ==========================================

def load_json():
    if not os.path.exists(JSON_FILE):
        return {}

    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def prepare_37_episodes(old_data):
    episodes = {}

    # 37 bölümün tamamı için boş kayıt oluştur
    for number in range(1, 38):
        episodes[number] = {
            "episode": number,
            "title": f"İkinci Bahar {number}. Bölüm",
            "youtube_url": None,
            "m3u8_url": None,
            "hls_checked_at": None,
            "hls_status": "BEKLENİYOR",
        }

    # Önceki kayıtları koru
    for item in old_data.get("episodes", []):
        try:
            number = int(item.get("episode"))
        except Exception:
            continue

        if 1 <= number <= 37:
            episodes[number].update(item)

    return episodes


# ==========================================
# RESMİ KANAL RSS
# ==========================================

def get_channel_videos():
    print("RESMİ KANAL RSS KONTROLÜ")

    response = requests.get(
        RSS_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)

    found = []

    for entry in root.findall("atom:entry", NS):
        title_node = entry.find("atom:title", NS)
        id_node = entry.find("yt:videoId", NS)

        if title_node is None or id_node is None:
            continue

        title = html.unescape(title_node.text or "").strip()
        video_id = (id_node.text or "").strip()

        if not video_id:
            continue

        match = re.search(
            r'(\d{1,2})\s*\.?\s*bölüm',
            title,
            re.IGNORECASE
        )

        if not match:
            continue

        number = int(match.group(1))

        if not 1 <= number <= 37:
            continue

        found.append({
            "episode": number,
            "title": title,
            "youtube_url": (
                f"https://www.youtube.com/watch?v={video_id}"
            ),
        })

    return found


# ==========================================
# YOUTUBE HLS TESTİ
# ==========================================

def find_hls(video_url):
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(
            video_url,
            download=False
        )

    formats = info.get("formats", [])
    candidates = []

    for fmt in formats:
        protocol = (fmt.get("protocol") or "").lower()
        url = fmt.get("url") or ""

        if (
            "m3u8" in protocol
            and url.startswith("https://")
        ):
            candidates.append(fmt)

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x.get("height") or 0,
            x.get("tbr") or 0
        ),
        reverse=True
    )

    return candidates[0]["url"]


# ==========================================
# M3U KAYITLARINI KORU
# ==========================================

def save_m3u(new_entries):
    lines = []

    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    if not lines or lines[0].strip() != "#EXTM3U":
        lines.insert(0, "#EXTM3U")

    existing_urls = set(
        line.strip()
        for line in lines
        if line.strip().startswith("http")
    )

    for number, url in new_entries:
        if not url or url in existing_urls:
            continue

        lines.append(
            f'#EXTINF:-1 group-title="🎬 İKİNCİ BAHAR",'
            f'İkinci Bahar {number}. Bölüm'
        )
        lines.append(url)

        existing_urls.add(url)

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ==========================================
# ANA PROGRAM
# ==========================================

def main():
    print("=" * 50)
    print("MIRTI68 - İKİNCİ BAHAR 37 BÖLÜM")
    print("=" * 50)

    old_data = load_json()
    episodes = prepare_37_episodes(old_data)

    # RSS bağlantılarını al
    try:
        videos = get_channel_videos()
        print("RSS İLE BULUNAN:", len(videos))
    except Exception as e:
        print("RSS HATASI:", str(e))
        videos = []

    # Yeni videoları arşive ekle
    for video in videos:
        number = video["episode"]
        current = episodes[number]

        current["title"] = video["title"]
        current["youtube_url"] = video["youtube_url"]

    # HLS denemesi
    new_hls = []
    tested = 0

    for number in range(1, 38):
        item = episodes[number]

        video_url = item.get("youtube_url")

        if not video_url:
            continue

        if item.get("m3u8_url"):
            continue

        checked_at = parse_date(
            item.get("hls_checked_at") or ""
        )

        if checked_at and now_utc() - checked_at < timedelta(days=7):
            continue

        if tested >= MAX_HLS_TEST:
            break

        tested += 1

        print(
            f"\nBÖLÜM {number}: "
            f"{item.get('title')}"
        )

        item["hls_checked_at"] = now_utc().isoformat()

        try:
            hls = find_hls(video_url)

            if hls:
                item["m3u8_url"] = hls
                item["hls_status"] = "HLS_BULUNDU"

                new_hls.append((number, hls))

                print("M3U8 BULUNDU!")
            else:
                item["hls_status"] = "HLS_YOK"
                print("M3U8 bulunamadı.")

        except Exception as e:
            item["hls_status"] = "ERİŞİM_ENGELİ"
            print("HLS ERİŞİM HATASI:", str(e)[:300])

    # JSON kaydet
    result = {
        "series": "İkinci Bahar",
        "channel": "İkinci Bahar (Dizi)",
        "channel_id": CHANNEL_ID,
        "expected_episodes": 37,
        "updated_at": now_utc().isoformat(),
        "episodes": [
            episodes[n]
            for n in range(1, 38)
        ],
    }

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    # Yalnızca HLS bulunanları M3U'ya ekle
    save_m3u(new_hls)

    youtube_count = sum(
        1 for x in episodes.values()
        if x.get("youtube_url")
    )

    hls_count = sum(
        1 for x in episodes.values()
        if x.get("m3u8_url")
    )

    print("\n" + "=" * 50)
    print("İKİNCİ BAHAR ARŞİV SONUCU")
    print("=" * 50)
    print("Arşiv bölüm sayısı: 37")
    print("YouTube bağlantısı bulunan:", youtube_count)
    print("M3U8 bulunan:", hls_count)
    print("Yeni HLS testi:", tested)
    print("JSON:", JSON_FILE)
    print("M3U:", M3U_FILE)
    print("=" * 50)


if __name__ == "__main__":
    main()
        
