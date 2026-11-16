
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - İKİNCİ BAHAR RESMİ KAYNAK BOTU
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

# ==========================================
# ESKİ M3U KAYITLARINI KORU
# ==========================================

def load_old_m3u():
    if not os.path.exists(M3U_FILE):
        return []

    with open(M3U_FILE, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def save_m3u(old_lines, new_entries):
    lines = old_lines[:]

    if not lines or lines[0].strip() != "#EXTM3U":
        lines.insert(0, "#EXTM3U")

    existing = set(lines)

    for title, url in new_entries:
        extinf = (
            f'#EXTINF:-1 group-title="🎬 İKİNCİ BAHAR",'
            f'{title}'
        )

        if extinf not in existing:
            lines.append(extinf)
            lines.append(url)
            existing.add(extinf)

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ==========================================
# RESMİ KANAL RSS
# ==========================================

def get_channel_videos():
    print("\nRESMİ KANAL RSS KONTROLÜ")

    response = requests.get(
        RSS_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)
    videos = []

    for entry in root.findall("atom:entry", NS):
        title_node = entry.find("atom:title", NS)
        id_node = entry.find("yt:videoId", NS)

        if title_node is None or id_node is None:
            continue

        title = title_node.text or ""
        video_id = id_node.text or ""

        if not video_id:
            continue

        # Sadece bölüm başlıklarını al
        match = re.search(
            r'(\d{1,2})\s*\.?\s*bölüm',
            title,
            re.IGNORECASE
        )

        if not match:
            continue

        episode = int(match.group(1))

        if not 1 <= episode <= 37:
            continue

        videos.append({
            "episode": episode,
            "title": title,
            "video_id": video_id,
            "youtube_url": (
                f"https://www.youtube.com/watch?v={video_id}"
            ),
            "m3u8_url": None,
        })

    videos.sort(key=lambda x: x["episode"])

    return videos


# ==========================================
# GERÇEK HLS ADRESİNİ KONTROL ET
# ==========================================

def find_hls(video):
    print(
        f"\nBölüm {video['episode']} kontrol ediliyor: "
        f"{video['title']}"
    )

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                video["youtube_url"],
                download=False
            )

        formats = info.get("formats", [])

        hls_formats = []

        for fmt in formats:
            protocol = (fmt.get("protocol") or "").lower()
            url = fmt.get("url") or ""

            if (
                "m3u8" in protocol
                and url.startswith("http")
            ):
                hls_formats.append(fmt)

        if not hls_formats:
            print("M3U8 bulunamadı.")
            return None

        # En yüksek çözünürlüklü HLS formatını seç
        hls_formats.sort(
            key=lambda x: (
                x.get("height") or 0,
                x.get("tbr") or 0
            ),
            reverse=True
        )

        selected = hls_formats[0]

        print("GERÇEK HLS FORMATI BULUNDU!")

        return selected["url"]

    except Exception as e:
        print("HLS erişim hatası:", str(e)[:350])
        return None


# ==========================================
# ANA PROGRAM
# ==========================================

def main():
    print("=" * 50)
    print("MIRTI68 - İKİNCİ BAHAR 37 BÖLÜM BOTU")
    print("=" * 50)

    old_lines = load_old_m3u()

    try:
        videos = get_channel_videos()
    except Exception as e:
        print("RSS HATASI:", str(e))
        videos = []

    print("\nRSS İLE BULUNAN BÖLÜM:", len(videos))

    old_data = {}

    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        except Exception:
            old_data = {}

    # Önceki kayıtları koru
    saved = {}

    if isinstance(old_data, dict):
        for item in old_data.get("episodes", []):
            if isinstance(item, dict):
                saved[item.get("episode")] = item

    for video in videos:
        saved[video["episode"]] = video

    new_hls = []

    for episode in sorted(saved):
        video = saved[episode]

        # Daha önce HLS bulunduysa tekrar deneme
        hls_url = video.get("m3u8_url")

        if not hls_url and video.get("youtube_url"):
            hls_url = find_hls(video)

        if hls_url:
            video["m3u8_url"] = hls_url

            title = f"İkinci Bahar {episode}. Bölüm"

            new_hls.append((title, hls_url))

    # JSON kaynak arşivini kaydet
    result = {
        "series": "İkinci Bahar",
        "channel_id": CHANNEL_ID,
        "total_expected": 37,
        "episodes": [
            saved[n]
            for n in sorted(saved)
        ]
    }

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    # Eski M3U kayıtlarını silmeden yeni HLS ekle
    save_m3u(old_lines, new_hls)

    print("\n" + "=" * 50)
    print("MIRTI68 İKİNCİ BAHAR SONUÇ")
    print("=" * 50)
    print("Bulunan bölüm:", len(saved))
    print("HLS bulunan:", len(new_hls))
    print("Beklenen bölüm: 37")
    print("JSON:", JSON_FILE)
    print("M3U:", M3U_FILE)
    print("=" * 50)


if __name__ == "__main__":
    main()
