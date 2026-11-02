
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF YOUTUBE VOLEYBOL CANLI YAYIN BULUCU

- Günün maçlarını JSON dosyasından okur.
- YouTube'da TVF resmi kanalını arar.
- Yalnızca doğrulanmış canlı yayınları kabul eder.
- YouTube bot hatasında eski listeyi korur.
- Doğrudan mirti68.m3u dosyasına VOLEYBOL grubu ekler.
- Eski kanallara dokunmaz.
- Önceki voleybol grubunu yeni yayınlarla değiştirir.
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

MASTER_FILE = "mirti68.m3u"

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

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


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

            print("Program JSON liste formatinda degil!")

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


# =====================================
# MAC ADI KONTROLU
# =====================================

def title_matches(title, match):

    title = normalize(title)

    home = normalize(
        match.get("home", "")
    )

    away = normalize(
        match.get("away", "")
    )

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
        word in title
        for word in home_words
    )

    away_found = any(
        word in title
        for word in away_words
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

            print(
                "⛔ Mac adi eslesmedi:",
                title
            )

            continue

        # Canli yayin kontrolu

        if info.get("live_status") != "is_live":

            print(
                "⏳ Yayin su anda canli degil:",
                title
            )

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

            print(
                "⚠️ HLS adresi bulunamadi:",
                title
            )

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

    if scan_error:

        print("⚠️ Tarama tamamlanamadi.")

        return None, False

    return None, True


# =====================================
# ANA M3U GUNCELLEME
# =====================================

def save_files(results):

    if not results:

        print("Yeni yayin yok.")

        print("Eski mirti68.m3u korunuyor.")

        return False

    if not os.path.exists(MASTER_FILE):

        print("❌ Ana liste bulunamadi:", MASTER_FILE)

        return False

    temp_file = MASTER_FILE + ".tmp"

    json_temp = RESULT_FILE + ".tmp"

    try:

        # Ana listeyi oku

        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as f:

            old_lines = f.readlines()

        if not old_lines or not old_lines[0].strip().startswith("#EXTM3U"):

            raise ValueError("Ana M3U dosyasi gecersiz!")

        # Eski voleybol grubunu temizle

        cleaned = []

        skip_url = False

        for line in old_lines:

            stripped = line.strip()

            if stripped.startswith("#EXTINF:"):

                if GROUP in stripped:

                    skip_url = True

                    continue

                skip_url = False

            if skip_url:

                if stripped and not stripped.startswith("#"):

                    skip_url = False

                    continue

                if not stripped:

                    continue

            cleaned.append(line)

        # Yeni yayinlari hazirla

        new_lines = []

        added_ids = set()

        for item in results:

            stream_url = item.get("stream_url", "")

            if not stream_url.startswith("http"):

                raise ValueError("Gecersiz yayin adresi!")

            video_id = item.get("video_id")

            if video_id in added_ids:

                continue

            added_ids.add(video_id)

            name = str(
                item.get("name")
                or item.get("title")
                or "VOLEYBOL"
            ).replace(",", " ")

            new_lines.append(
                f'#EXTINF:-1 group-title="{GROUP}",{name}\n'
            )

            new_lines.append(
                stream_url + "\n"
            )

        if not new_lines:

            raise ValueError("Eklenecek yayin bulunamadi!")

        # Ana listenin sonuna ekle

        content = "".join(cleaned)

        if not content.endswith("\n"):

            content += "\n"

        content += "".join(new_lines)

        # Gecici M3U dosyasi

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(content)

        # Dosyayi kontrol et

        with open(
            temp_file,
            "r",
            encoding="utf-8"
        ) as f:

            check = f.read()

        if not check.startswith("#EXTM3U"):

            raise ValueError("M3U baslik hatasi!")

        if GROUP not in check:

            raise ValueError("Voleybol grubu bulunamadi!")

        # JSON gecici dosyasi

        with open(
            json_temp,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                results,
                f,
                ensure_ascii=False,
                indent=2
            )

        # Eski ana listeyi yedekle

        shutil.copy2(
            MASTER_FILE,
            MASTER_FILE + ".bak"
        )

        # Ana listeyi guncelle

        os.replace(
            temp_file,
            MASTER_FILE
        )

        # JSON yedegi

        if os.path.exists(RESULT_FILE):

            shutil.copy2(
                RESULT_FILE,
                RESULT_FILE + ".bak"
            )

        try:

            os.replace(
                json_temp,
                RESULT_FILE
            )

        except Exception:

            # JSON kaydi basarisizsa ana listeyi geri al

            shutil.copy2(
                MASTER_FILE + ".bak",
                MASTER_FILE
            )

            raise

        print("=" * 45)

        print("✅ MIRTI68 ANA LISTE GUNCELLENDI")

        print("Ana dosya:", MASTER_FILE)

        print("Grup:", GROUP)

        print("Yayin sayisi:", len(new_lines) // 2)

        print("Yedek:", MASTER_FILE + ".bak")

        print("=" * 45)

        return True

    except Exception as e:

        print("❌ Kayit hatasi:", e)

        print("✅ Onceki ana liste korunuyor.")

        return False

    finally:

        for path in (temp_file, json_temp):

            if os.path.exists(path):

                try:

                    os.remove(path)

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

        print("Ana liste korunuyor.")

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

        print("Ana liste korunuyor.")

        return

    options = {

        "quiet": True,

        "no_warnings": False,

        "skip_download": True,

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

        print("✅ ANA LISTE KORUNDU.")

        return

    # Eksik tarama varsa kaydetme

    if not scan_complete:

        print()

        print("⚠️ YouTube taramasi eksik kaldi.")

        print("✅ mirti68.m3u korunuyor.")

        return

    # Yayin yoksa kaydetme

    if not results:

        print()

        print("Gecerli canli yayin bulunamadi.")

        print("✅ mirti68.m3u korunuyor.")

        return

    # Dogrulanmis yayinlari ana listeye ekle

    if save_files(results):

        print()

        print("✅ VOLEYBOL GRUBU BASARIYLA GUNCELLENDI.")

    print("=" * 45)

    print("Bulunan canli yayin:", len(results))

    print("Ana M3U:", MASTER_FILE)

    print("Voleybol grubu:", GROUP)

    print("Ana liste diger kanallari korundu.")

    print("=" * 45)


if __name__ == "__main__":

    main()
