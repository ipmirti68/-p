#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

# ==========================================
# MIRTI68 - İKİNCİ BAHAR 37 BÖLÜM ARŞİVİ
# YASAL VERSİYON: Sadece 【entity-RSS¦canonical_name=RSS】 + YouTube Embed
# HLS / yt-dlp YOK
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

def now_utc():
    return datetime.now(timezone.utc)

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
    for number in range(1, 38):
        episodes[number] = {
            "episode": number,
            "title": f"İkinci Bahar {number}. Bölüm",
            "youtube_url": None,
            "video_id": None,
            "embed_url": None,
            "status": "BEKLENİYOR",
        }

    # Eski kayıtları koru ama eski m3u8 varsa sil
    for item in old_data.get("episodes", []):
        try:
            number = int(item.get("episode"))
        except Exception:
            continue
        if 1 <= number <= 37:
            # eski hls alanlarını taşıma
            item.pop("m3u8_url", None)
            item.pop("hls_checked_at", None)
            item.pop("hls_status", None)
            episodes[number].update(item)

    return episodes

def get_channel_videos():
    print("RESMİ KANAL RSS KONTROLÜ")
    response = requests.get(RSS_URL, headers=HEADERS, timeout=30)
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

        match = re.search(r'(\d{1,2})\s*\.?\s*bölüm', title, re.IGNORECASE)
        if not match:
            continue

        number = int(match.group(1))
        if not 1 <= number <= 37:
            continue

        found.append({
            "episode": number,
            "title": title,
            "video_id": video_id,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
        })

    return found

def save_m3u(episodes):
    # Artık HLS değil, YouTube linki yazıyoruz.
    # IPTV player'lar bunu YouTube üzerinden açar.
    lines = ["#EXTM3U"]
    for n in range(1, 38):
        item = episodes[n]
        if not item.get("youtube_url"):
            continue
        lines.append(
            f'#EXTINF:-1 group-title="🎬 İKİNCİ BAHAR",'
            f'İkinci Bahar {n}. Bölüm'
        )
        lines.append(item["youtube_url"])

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    print("=" * 50)
    print("MIRTI68 - İKİNCİ BAHAR 37 BÖLÜM")
    print("=" * 50)

    old_data = load_json()
    episodes = prepare_37_episodes(old_data)

    try:
        videos = get_channel_videos()
        print("RSS İLE BULUNAN:", len(videos))
    except Exception as e:
        print("RSS HATASI:", str(e))
        videos = []

    for video in videos:
        number = video["episode"]
        current = episodes[number]
        current["title"] = video["title"]
        current["video_id"] = video["video_id"]
        current["youtube_url"] = video["youtube_url"]
        current["embed_url"] = video["embed_url"]
        current["status"] = "BULUNDU"

    result = {
        "series": "İkinci Bahar",
        "channel": "İkinci Bahar (Dizi)",
        "channel_id": CHANNEL_ID,
        "expected_episodes": 37,
        "updated_at": now_utc().isoformat(),
        "episodes": [episodes[n] for n in range(1, 38)],
    }

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    save_m3u(episodes)

    youtube_count = sum(1 for x in episodes.values() if x.get("youtube_url"))

    print("\n" + "=" * 50)
    print("İKİNCİ BAHAR ARŞİV SONUCU")
    print("=" * 50)
    print("Arşiv bölüm sayısı: 37")
    print("YouTube bağlantısı bulunan:", youtube_count)
    print("JSON:", JSON_FILE)
    print("M3U:", M3U_FILE)
    print("=" * 50)

if __name__ == "__main__":
    main()
