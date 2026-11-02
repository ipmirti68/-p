#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF VOLEYBOL YAYIN TARAMA

TVF resmi YouTube yayin sayfasini tarar.
Canli ve planlanmis yayinlari bulur.
Canli yayinlarda HLS adresini alir.
Planlanmis yayinlarda YouTube adresini kaydeder.
mirti68.m3u dosyasindaki diger kanallari korur.
"""

import os
import json
import shutil

from datetime import datetime, timezone
from yt_dlp import YoutubeDL


# =====================================
# AYARLAR
# =====================================

CHANNEL_URL = "https://www.youtube.com/@tvfvoleyboltv/streams"

OFFICIAL_CHANNEL_ID = "UCTgQ8Bfq3AUuo1vWULdvRKw"

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"

GROUP = "🏐 VOLEYBOL CANLI"

MAX_VIDEOS = 50
TIMEOUT = 30


# =====================================
# YOUTUBE AYARLARI
# =====================================

OPTIONS = {
    "quiet": True,
    "no_warnings": False,
    "skip_download": True,
    "ignoreerrors": False,
    "socket_timeout": TIMEOUT,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "noplaylist": False,
    "retries": 2,
    "extractor_retries": 2,
    "fragment_retries": 2,
    "cachedir": False,
}


# =====================================
# HLS ADRESI BUL
# =====================================

def get_hls(info):

    formats = info.get("formats") or []

    hls_formats = [
        fmt for fmt in formats
        if "m3u8" in str(fmt.get("protocol", "")).lower()
        and fmt.get("url")
    ]

    if not hls_formats:
        return None

    hls_formats.sort(
        key=lambda fmt: (
            fmt.get("height") or 0,
            fmt.get("tbr") or 0
        ),
        reverse=True
    )

    return hls_formats[0]["url"]


# =====================================
# VIDEO KONTROL
# =====================================

def scan_video(ydl, entry):

    video_id = entry.get("id")

    if not video_id:
        return None, True

    video_url = (
        entry.get("url")
        or entry.get("webpage_url")
        or f"https://www.youtube.com/watch?v={video_id}"
    )

    if not video_url.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:

        info = ydl.extract_info(
            video_url,
            download=False
        )

    except Exception as e:

        print("Video okunamadi:", video_id)
        print("Hata:", e)

        return None, False

    if not info:
        return None, False

    channel_id = (
        info.get("channel_id")
        or entry.get("channel_id")
    )

    if channel_id != OFFICIAL_CHANNEL_ID:

        print("Resmi olmayan kanal atlandi:", video_id)

        return None, True

    title = (
        info.get("title")
        or entry.get("title")
        or "TVF VOLEYBOL"
    )

    status = (
        info.get("live_status")
        or entry.get("live_status")
        or ""
    )

    is_live = (
        status == "is_live"
        or info.get("is_live") is True
    )

    is_upcoming = (
        status == "is_upcoming"
        or info.get("is_upcoming") is True
    )

    if not is_live and not is_upcoming:

        print("Canli veya planlanmis yayin degil:", title)

        return None, True

    youtube_url = (
        info.get("webpage_url")
        or f"https://www.youtube.com/watch?v={video_id}"
    )

    if is_live:

        stream_url = get_hls(info)

        if not stream_url:

            print("Canli yayin HLS bulunamadi:", title)

            return None, False

        state = "CANLI"

        print("CANLI YAYIN:", title)

    else:

        stream_url = youtube_url

        state = "YAYINA HAZIR"

        print("YAYINA HAZIR:", title)

    return {
        "video_id": video_id,
        "name": title,
        "title": title,
        "youtube_url": youtube_url,
        "stream_url": stream_url,
        "channel_id": channel_id,
        "live_status": status,
        "state": state,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }, True


# =====================================
# TVF YAYIN SAYFASINI TARA
# =====================================

def scan_channel():

    options = OPTIONS.copy()

    if os.path.exists("cookies.txt"):

        options["cookiefile"] = "cookies.txt"

        print("YouTube cookies kullaniliyor.")

    else:

        print("Cookies bulunamadi.")

    results = []
    scan_complete = True

    print("=" * 50)
    print("TVF VOLEYBOL TV TARANIYOR")
    print(CHANNEL_URL)
    print("=" * 50)

    try:

        with YoutubeDL(options) as ydl:

            channel_data = ydl.extract_info(
                CHANNEL_URL,
                download=False
            )

            if not channel_data:

                print("TVF sayfasi okunamadi.")

                return [], False

            entries = channel_data.get("entries") or []

            if not entries:

                print("Yayin sayfasinda video bulunamadi.")

                return [], False

            print("Bulunan video:", len(entries))

            seen = set()

            for entry in entries:

                if not entry:
                    continue

                video_id = entry.get("id")

                if not video_id or video_id in seen:
                    continue

                seen.add(video_id)

                print()
                print("Kontrol:", entry.get("title"))

                result, completed = scan_video(
                    ydl,
                    entry
                )

                if not completed:

                    scan_complete = False

                    continue

                if result:
                    results.append(result)

    except Exception as e:

        print("YOUTUBE TARAMA HATASI:", e)

        return [], False

    return results, scan_complete


# =====================================
# ESKI VOLEYBOL GRUBUNU TEMIZLE
# =====================================

def remove_old_group(lines):

    cleaned = []
    i = 0

    while i < len(lines):

        line = lines[i].strip()

        if line.startswith("#EXTINF:") and GROUP in line:

            i += 1

            while i < len(lines):

                current = lines[i].strip()

                # Sonraki kanal kaydina geldiysek onu koru.
                if current.startswith("#EXTINF:"):
                    break

                if not current or current.startswith("#"):
                    i += 1
                    continue

                # Eski kanal URL satiri atlandi.
                i += 1
                break

            continue

        cleaned.append(lines[i])
        i += 1

    return cleaned


# =====================================
# DOSYALARI GUVENLI KAYDET
# =====================================

def save_files(results):

    if not results:

        print("Yayin yok. Ana liste korunuyor.")

        return False

    if not os.path.exists(MASTER_FILE):

        print("Ana M3U bulunamadi:", MASTER_FILE)

        return False

    temp_file = MASTER_FILE + ".tmp"
    json_temp = RESULT_FILE + ".tmp"

    try:

        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as f:

            old_lines = f.readlines()

        if not old_lines:

            raise ValueError("Ana M3U bos!")

        if not old_lines[0].strip().startswith("#EXTM3U"):

            raise ValueError("M3U basligi gecersiz!")

        cleaned = remove_old_group(old_lines)

        new_lines = []
        added_ids = set()

        for item in results:

            video_id = item.get("video_id")
            stream_url = item.get("stream_url")

            if not video_id or video_id in added_ids:
                continue

            if not stream_url or not stream_url.startswith("http"):
                continue

            added_ids.add(video_id)

            name = str(
                item.get("name") or "TVF VOLEYBOL"
            )

            name = (
                name.replace(",", " ")
                .replace("\n", " ")
                .replace("\r", " ")
            )

            state = item.get("state", "")

            channel_name = f"{name} [{state}]"

            new_lines.append(
                f'#EXTINF:-1 group-title="{GROUP}",{channel_name}\n'
            )

            new_lines.append(stream_url + "\n")

        if not new_lines:

            raise ValueError("Eklenecek gecerli yayin yok!")

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

        # M3U kontrolu

        with open(
            temp_file,
            "r",
            encoding="utf-8"
        ) as f:

            check = f.read()

        if not check.startswith("#EXTM3U"):
            raise ValueError("M3U kontrolu basarisiz!")

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

        if os.path.exists(RESULT_FILE):

            shutil.copy2(
                RESULT_FILE,
                RESULT_FILE + ".bak"
            )

        # JSON kaydet

        os.replace(
            json_temp,
            RESULT_FILE
        )

        # Ana M3U kaydet

        try:

            os.replace(
                temp_file,
                MASTER_FILE
            )

        except Exception:

            if os.path.exists(MASTER_FILE + ".bak"):

                shutil.copy2(
                    MASTER_FILE + ".bak",
                    MASTER_FILE
                )

            if os.path.exists(RESULT_FILE + ".bak"):

                shutil.copy2(
                    RESULT_FILE + ".bak",
                    RESULT_FILE
                )

            raise

        print("=" * 45)
        print("MIRTI68 ANA LISTE GUNCELLENDI")
        print("Ana dosya:", MASTER_FILE)
        print("Voleybol grubu:", GROUP)
        print("Yayin sayisi:", len(added_ids))
        print("=" * 45)

        return True

    except Exception as e:

        print("KAYIT HATASI:", e)
        print("Ana liste korunmaya calisildi.")

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

    print("=" * 50)
    print("MIRTI68 TVF VOLEYBOL YAYIN TARAMA")
    print("=" * 50)

    results, scan_complete = scan_channel()

    print()
    print("Bulunan yayin:", len(results))

    if not scan_complete:

        print("Tarama eksik veya basarisiz.")
        print("mirti68.m3u korunuyor.")

        return

    if not results:

        print("Canli veya planlanmis yayin bulunamadi.")
        print("mirti68.m3u korunuyor.")

        return

    if save_files(results):

        print()
        print("VOLEYBOL GRUBU GUNCELLENDI.")

    print("=" * 45)
    print("Bulunan yayin:", len(results))
    print("Ana M3U:", MASTER_FILE)
    print("Grup:", GROUP)
    print("Diger kanallar korundu.")
    print("=" * 45)


if __name__ == "__main__":
    main()
