
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF YOUTUBE CANLI YAYIN BULUCU

- voleybol_program.json dosyasini okur.
- Bugunun maclarini YouTube'da arar.
- Yalnizca TVF resmi kanalini kabul eder.
- Yalnizca gercekten canli yayinlari ekler.
- Onceki M3U dosyasini, yeni yayin bulunamazsa korur.
"""

import os
import re
import json
import unicodedata

from datetime import datetime
from zoneinfo import ZoneInfo
from yt_dlp import YoutubeDL


# =====================================
# AYARLAR
# =====================================

PROGRAM_FILE = "voleybol_program.json"
OUTPUT_FILE = "voleybol_canli.m3u"
RESULT_FILE = "voleybol_youtube.json"

OFFICIAL_CHANNEL_ID = "UCTgQ8Bfq3AUuo1vWULdvRKw"

GROUP = "🏐 VOLEYBOL CANLI"

MAX_SEARCH_RESULTS = 8


# =====================================
# YARDIMCI FONKSIYONLAR
# =====================================

def normalize(text):

    text = str(text or "").lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = text.replace("ı", "i")

    text = re.sub(
        r"[^a-z0-9 ]",
        " ",
        text
    )

    return re.sub(r"\s+", " ", text).strip()


def load_program():

    if not os.path.exists(PROGRAM_FILE):
        print("Program JSON bulunamadi!")
        return []

    try:
        with open(
            PROGRAM_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("Program dosyasi liste formatinda degil!")
            return []

        return data

    except Exception as e:
        print("Program okunamadi:", e)
        return []


def is_today(match):

    try:
        today = datetime.now(
            ZoneInfo("Europe/Istanbul")
        ).strftime("%d.%m.%Y")

        return match.get("date") == today

    except Exception:
        return False


def title_matches(title, match):

    title = normalize(title)

    home = normalize(match.get("home", ""))
    away = normalize(match.get("away", ""))

    ignored = {
        "spor", "belediye", "kulubu",
        "voleybol", "tvf", "spor",
        "genclik", "takim"
    }

    home_words = {
        word for word in home.split()
        if len(word) >= 3 and word not in ignored
    }

    away_words = {
        word for word in away.split()
        if len(word) >= 3 and word not in ignored
    }

    if not home_words or not away_words:
        return False

    home_found = any(
        word in title for word in home_words
    )

    away_found = any(
        word in title for word in away_words
    )

    return home_found and away_found


# =====================================
# YOUTUBE ARAMA
# =====================================

def search_match(ydl, match):

    home = match.get("home", "")
    away = match.get("away", "")

    query = (
        f"{home} {away} "
        "TVF Voleybol TV"
    )

    print("🔎 Araniyor:", query)

    try:

        search_result = ydl.extract_info(
            f"ytsearch{MAX_SEARCH_RESULTS}:{query}",
            download=False
        )

    except Exception as e:

        print("YouTube arama hatasi:", e)
        return None

    if not search_result:
        return None

    entries = search_result.get("entries") or []

    for entry in entries:

        if not entry:
            continue

        video_id = entry.get("id")

        if not video_id:
            continue

        video_url = (
            entry.get("webpage_url")
            or f"https://www.youtube.com/watch?v={video_id}"
        )

        try:

            info = ydl.extract_info(
                video_url,
                download=False
            )

        except Exception as e:

            print("Video kontrol edilemedi:", e)
            continue

        if not info:
            continue

        # Resmi kanal kontrolu
        channel_id = info.get("channel_id")

        if channel_id != OFFICIAL_CHANNEL_ID:

            print("⛔ Resmi olmayan kanal:", info.get("title"))
            continue

        # Mac adi kontrolu
        title = info.get("title", "")

        if not title_matches(title, match):

            print("⛔ Mac adi eslesmedi:", title)
            continue

        # Yalnizca su anda canli olan yayin
        if info.get("live_status") != "is_live":

            print("⏳ Yayin su anda canli degil:", title)
            continue

        if info.get("is_live") is not True:
            continue

        # HLS formatini bul
        formats = info.get("formats") or []

        hls_formats = [
            fmt for fmt in formats
            if "m3u8" in str(fmt.get("protocol", "")).lower()
            and fmt.get("url")
        ]

        if hls_formats:

            hls_formats.sort(
                key=lambda x: (
                    x.get("height") or 0,
                    x.get("tbr") or 0
                ),
                reverse=True
            )

            stream_url = hls_formats[0]["url"]

        else:

            stream_url = info.get("url")

        if not stream_url:
            print("Oynatilabilir adres bulunamadi.")
            continue

        return {
            "date": match.get("date"),
            "time": match.get("time"),
            "name": match.get("name"),
            "title": title,
            "video_id": info.get("id"),
            "youtube_url": info.get("webpage_url"),
            "stream_url": stream_url,
            "channel_id": channel_id,
            "live_status": info.get("live_status")
        }

    return None


# =====================================
# M3U OLUSTUR
# =====================================

def save_playlist(results):

    if not results:
        print("Yeni canli yayin yok.")
        print("Onceki M3U dosyasi korunuyor.")
        return False

    lines = ["#EXTM3U\n"]

    for item in results:

        name = (
            item["name"]
            .replace(",", " ")
        )

        lines.append(
            f'#EXTINF:-1 group-title="{GROUP}",'
            f'{name}\n'
        )

        lines.append(
            item["stream_url"] + "\n"
        )

    temp = OUTPUT_FILE + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:

        f.writelines(lines)

    os.replace(temp, OUTPUT_FILE)

    return True


# =====================================
# ANA PROGRAM
# =====================================

def main():

    print("=" * 45)
    print(" MIRTI68 - YOUTUBE VOLEYBOL TARAMA")
    print("=" * 45)

    matches = load_program()

    if not matches:
        print("Mac programi bulunamadi.")
        return

    today_matches = [
        match for match in matches
        if is_today(match)
    ]

    print("Bugunun mac sayisi:", len(today_matches))

    if not today_matches:
        print("Bugun icin mac bulunamadi.")
        print("Eski yayin listesi korunuyor.")
        return

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
        "socket_timeout": 25,
        "extract_flat": False,
        "playlistend": MAX_SEARCH_RESULTS
    }

    results = []

    try:

        with YoutubeDL(options) as ydl:

            for match in today_matches:

                print()
                print("🏐", match.get("name"))

                result = search_match(
                    ydl,
                    match
                )

                if result:

                    print("✅ CANLI YAYIN BULUNDU!")
                    print(result["title"])

                    results.append(result)

                else:

                    print("❌ Dogrulanmis canli yayin yok.")

    except Exception as e:

        print("YouTube tarama hatasi:", e)
        print("Onceki liste korunuyor.")
        return

    if not results:
        print("Gecerli canli yayin bulunamadi.")
        print("Onceki liste korunuyor.")
        return

    # JSON kaydet
    temp_json = RESULT_FILE + ".tmp"

    with open(
        temp_json,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_json,
        RESULT_FILE
    )

    # M3U kaydet
    if save_playlist(results):

        print()
        print("✅ VOLEYBOL CANLI LISTESI GUNCELLENDI.")

    print("=" * 45)
    print("Bulunan canli yayin:", len(results))
    print("M3U:", OUTPUT_FILE)
    print("JSON:", RESULT_FILE)
    print("Ana mirti68.m3u: DEGISTIRILMEDI")
    print("=" * 45)


if __name__ == "__main__":
    main()
