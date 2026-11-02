
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF YOUTUBE CANLI YAYIN BULUCU

- Günün maçlarını JSON dosyasından okur.
- YouTube'da TVF resmi kanalını arar.
- Yalnızca doğrulanmış canlı yayınları kabul eder.
- YouTube bot hatasında eski listeyi korur.
- Yeni yayın bulunana kadar eski M3U ve JSON dosyalarını silmez.
- Boş veya hatalı listeyi kaydetmez.
"""

import os
import re
import json
import unicodedata
import shutil

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

TIMEOUT = 25


# =====================================
# YARDIMCI FONKSIYONLAR
# =====================================

def normalize(text):

    text = str(text or "").lower()

    text = unicodedata.normalize("NFKD", text)

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
        "spor",
        "belediye",
        "kulubu",
        "voleybol",
        "tvf",
        "genclik",
        "takim"
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

        print("❌ YouTube arama hatasi:", e)

        # Tarama tamamlanamadi
        return None, False

    if not search_result:

        return None, True

    entries = search_result.get("entries") or []

    if not entries:

        print("Arama sonucu bulunamadi.")

        return None, True

    scan_error = False

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

            print("⚠️ Video kontrol hatasi:", e)

            scan_error = True
            continue

        if not info:

            continue

        # Resmi kanal kontrolu

        channel_id = info.get("channel_id")

        if channel_id != OFFICIAL_CHANNEL_ID:

            print(
                "⛔ Resmi olmayan kanal:",
                info.get("title")
            )

            continue

        # Mac adi kontrolu

        title = info.get("title", "")

        if not title_matches(title, match):

            print("⛔ Mac adi eslesmedi:", title)

            continue

        # Canli yayin kontrolu

        if info.get("live_status") != "is_live":

            print("⏳ Yayin canli degil:", title)

            continue

        if info.get("is_live") is not True:

            continue

        # HLS adresi bul

        formats = info.get("formats") or []

        hls_formats = [
            fmt for fmt in formats
            if "m3u8" in str(
                fmt.get("protocol", "")
            ).lower()
            and fmt.get("url")
        ]

        if not hls_formats:

            print("⚠️ HLS adresi bulunamadi:", title)

            continue

        hls_formats.sort(
            key=lambda x: (
                x.get("height") or 0,
                x.get("tbr") or 0
            ),
            reverse=True
        )

        stream_url = hls_formats[0]["url"]

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
        }, True

    # Bazı videolar kontrol edilemediyse
    # tarama eksik sayılır.
    if scan_error:

        print("⚠️ Tarama tamamlanamadi.")

        return None, False

    return None, True


# =====================================
# GUVENLI DOSYA KAYDI
# =====================================

def save_files(results):

    if not results:

        print("⚠️ Yeni canli yayin yok.")
        print("✅ Eski dosyalar korundu.")

        return False

    # M3U icerigi hazirla

    lines = ["#EXTM3U\n"]

    for item in results:

        stream_url = item.get("stream_url", "")

        if not stream_url.startswith("http"):
            print("Gecersiz yayin adresi!")
            return False

        name = str(
            item.get("name") or item.get("title") or "VOLEYBOL"
        ).replace(",", " ")

        lines.append(
            f'#EXTINF:-1 group-title="{GROUP}",{name}\n'
        )

        lines.append(stream_url + "\n")

    m3u_content = "".join(lines)

    if len(results) == 0:
        return False

    # JSON icerigi hazirla

    json_content = json.dumps(
        results,
        ensure_ascii=False,
        indent=2
    )

    temp_m3u = OUTPUT_FILE + ".tmp"
    temp_json = RESULT_FILE + ".tmp"

    try:

        # Once gecici dosyalara yaz

        with open(
            temp_m3u,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(m3u_content)

        with open(
            temp_json,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(json_content)

        # Gecici dosyalarin bos olmadigini kontrol et

        if os.path.getsize(temp_m3u) <= len("#EXTM3U"):
            raise ValueError("M3U dosyasi bos!")

        if os.path.getsize(temp_json) == 0:
            raise ValueError("JSON dosyasi bos!")

        # Eski dosyalari yedekle

        old_m3u = None
        old_json = None

        if os.path.exists(OUTPUT_FILE):

            shutil.copy2(
                OUTPUT_FILE,
                OUTPUT_FILE + ".bak"
            )

            with open(OUTPUT_FILE, "rb") as f:
                old_m3u = f.read()

        if os.path.exists(RESULT_FILE):

            shutil.copy2(
                RESULT_FILE,
                RESULT_FILE + ".bak"
            )

            with open(RESULT_FILE, "rb") as f:
                old_json = f.read()

        # Yeni dosyalari devreye al

        os.replace(temp_m3u, OUTPUT_FILE)

        try:

            os.replace(temp_json, RESULT_FILE)

        except Exception:

            # JSON kaydi basarisizsa M3U'yu geri al

            if old_m3u is not None:

                with open(OUTPUT_FILE, "wb") as f:
                    f.write(old_m3u)

            else:

                if os.path.exists(OUTPUT_FILE):
                    os.remove(OUTPUT_FILE)

            raise

        print("✅ M3U ve JSON guvenli sekilde kaydedildi.")

        return True

    except Exception as e:

        print("❌ Dosya kayit hatasi:", e)
        print("✅ Onceki dosyalar korunuyor.")

        return False

    finally:

        for temp in (temp_m3u, temp_json):

            if os.path.exists(temp):

                try:
                    os.remove(temp)
                except OSError:
                    pass


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
        print("Eski liste korunuyor.")

        return

    today_matches = [
        match for match in matches
        if is_today(match)
    ]

    print(
        "Bugunun mac sayisi:",
        len(today_matches)
    )

    if not today_matches:

        print("Bugun icin mac bulunamadi.")
        print("Eski liste korunuyor.")

        return

    options = {

        "quiet": True,
        "no_warnings": False,

        "skip_download": True,

        # Hatalari yakalayabilmek icin
        "ignoreerrors": False,

        "socket_timeout": TIMEOUT,

        "extract_flat": False,

        "playlistend": MAX_SEARCH_RESULTS,

        "noplaylist": True,

        "retries": 2,

        "extractor_retries": 2,

        "fragment_retries": 2,

        "cachedir": False,

    }

    results = []

    scan_complete = True

    try:

        with YoutubeDL(options) as ydl:

            for match in today_matches:

                print()
                print("🏐", match.get("name"))

                result, completed = search_match(
                    ydl,
                    match
                )

                if not completed:

                    scan_complete = False

                if result:

                    print("✅ CANLI YAYIN BULUNDU!")

                    print(result["title"])

                    results.append(result)

                else:

                    print("❌ Dogrulanmis canli yayin yok.")

    except Exception as e:

        print()
        print("❌ YOUTUBE TARAMA HATASI:", e)
        print("✅ ESKI LISTE KORUNDU.")

        return

    # Eksik tarama varsa listeyi degistirme

    if not scan_complete:

        print()
        print("⚠️ YouTube taramasi eksik kaldi.")
        print("✅ Eski M3U ve JSON korunuyor.")

        return

    # Hic canli yayin yoksa eski listeyi koru

    if not results:

        print()
        print("Gecerli canli yayin bulunamadi.")
        print("✅ Onceki liste korunuyor.")

        return

    # Yeni listeyi kaydet

    if save_files(results):

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
