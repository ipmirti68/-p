
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF VOLEYBOL YAYIN TARAMA

Canli ve planlanmis TVF yayinlarini tarar.
Canli yayinlarda HLS adresini alir.
Planlanmis yayinlarda YouTube adresini kaydeder.
Diger M3U kanallarini korur.
"""

import os
import re
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
    "no_warnings": True,
    "skip_download": True,
    "ignoreerrors": True,
    "socket_timeout": TIMEOUT,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "noplaylist": False,
    "retries": 2,
    "extractor_retries": 2,
    "cachedir": False,
}

# =====================================
# YOUTUBE URL
# =====================================

def youtube_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


# =====================================
# BASLIK TEMIZLE
# =====================================

def clean_title(title):
    title = str(title or "TVF VOLEYBOL")
    title = re.sub(r"[\r\n,]+", " ", title)
    return title.strip()


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
# VIDEO BILGISI ISLE
# =====================================

def scan_video(ydl, entry):

    video_id = entry.get("id")

    if not video_id:
        return None, True

    url = youtube_url(video_id)

    title = clean_title(entry.get("title"))

    channel_id = (
        entry.get("channel_id")
        or entry.get("uploader_id")
    )

    # Resmi kanal bilgisi yoksa video detayini kontrol et.
    info = None
    extraction_error = None

    try:
        info = ydl.extract_info(
            url,
            download=False
        )

    except Exception as e:
        extraction_error = str(e)
        print("Video detay bilgisi alinamadi:", video_id)
        print("Hata:", extraction_error)

    if info:

        channel_id = (
            info.get("channel_id")
            or info.get("channel")
            or channel_id
        )

        title = clean_title(
            info.get("title") or title
        )

    # Kanal doğrulaması yapılmadan kayıt ekleme.
    if channel_id != OFFICIAL_CHANNEL_ID:

        print("Resmi kanal dogrulanamadi:", video_id)

        return None, True

    status = ""

    if info:
        status = (
            info.get("live_status")
            or ""
        )

    if not status:
        status = (
            entry.get("live_status")
            or ""
        )

    is_live = (
        status == "is_live"
        or (info and info.get("is_live") is True)
    )

    is_upcoming = (
        status == "is_upcoming"
        or (info and info.get("is_upcoming") is True)
    )

    # YouTube planlanmış yayın hatası:
    # Başlık ve kanal bilgisi doğrulandıysa yaklaşan yayın kabul et.
    if (
        not info
        and extraction_error
        and "This live event will begin" in extraction_error
        and channel_id == OFFICIAL_CHANNEL_ID
    ):
        is_upcoming = True

    if not is_live and not is_upcoming:

        print("Canli veya planlanmis yayin degil:", title)

        return None, True

    if is_live:

        stream_url = get_hls(info) if info else None

        if not stream_url:

            print("Canli yayin HLS bulunamadi:", title)

            return None, False

        state = "CANLI"

    else:

        stream_url = url
        state = "YAYINA HAZIR"

    print(state + ":", title)

    return {
        "video_id": video_id,
        "name": title,
        "title": title,
        "youtube_url": url,
        "stream_url": stream_url,
        "channel_id": channel_id,
        "live_status": status or (
            "is_upcoming" if is_upcoming else "is_live"
        ),
        "state": state,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }, True


# =====================================
# TVF KANALINI TARA
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

                if current.startswith("#EXTINF:"):
                    break

                if not current or current.startswith("#"):
                    i += 1
                    continue

                i += 1
                break

            continue

        cleaned.append(lines[i])
        i += 1

    return cleaned


# =====================================
# M3U VE JSON KAYDET
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

            name = clean_title(item.get("name"))
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

        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)

        with open(temp_file, "r", encoding="utf-8") as f:
            check = f.read()

        if not check.startswith("#EXTM3U"):
            raise ValueError("M3U kontrolu basarisiz!")

        if GROUP not in check:
            raise ValueError("Voleybol grubu bulunamadi!")

        with open(json_temp, "w", encoding="utf-8") as f:
            json.dump(
                results,
                f,
                ensure_ascii=False,
                indent=2
            )

        # Yedekler
        shutil.copy2(MASTER_FILE, MASTER_FILE + ".bak")

        if os.path.exists(RESULT_FILE):
            shutil.copy2(RESULT_FILE, RESULT_FILE + ".bak")

        # M3U önce kaydedilir.
        os.replace(temp_file, MASTER_FILE)

        # JSON kaydedilir.
        os.replace(json_temp, RESULT_FILE)

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

        if os.path.exists(MASTER_FILE + ".bak"):
            try:
                shutil.copy2(
                    MASTER_FILE + ".bak",
                    MASTER_FILE
                )
            except Exception:
                pass

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
        print("VOLEYBOL GRUBU GUNCELLENDI.")

    print("=" * 45)
    print("Bulunan yayin:", len(results))
    print("Ana M3U:", MASTER_FILE)
    print("Grup:", GROUP)
    print("Diger kanallar korundu.")
    print("=" * 45)


if __name__ == "__main__":
    main()
        print("🏐 Voleybol grubu:", GROUP)
        print("Yayin sayisi:", len(added_ids))
        print("=" * 45)

        return True

    except Exception as e:

        print("KAYIT HATASI:", e)
        print("Ana liste korunmaya calisildi.")

        if os.path.exists(MASTER_FILE + ".bak"):
            try:
                shutil.copy2(
                    MASTER_FILE + ".bak",
                    MASTER_FILE
                )
            except Exception:
                pass

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
        print("VOLEYBOL GRUBU GUNCELLENDI.")

    print("=" * 45)
    print("Bulunan yayin:", len(results))
    print("Ana M3U:", MASTER_FILE)
    print("Grup:", GROUP)
    print("Diger kanallar korundu.")
    print("=" * 45)


if __name__ == "__main__":
    main()
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
