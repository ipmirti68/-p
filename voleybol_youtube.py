import os
import re
import json
import shutil
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote

from yt_dlp import YoutubeDL


# ==================================================
# MIRTI68 - TVF VOLEYBOL YOUTUBE TARAMA
# ==================================================

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"
BACKUP_FILE = "mirti68.m3u.bak"
JSON_BACKUP = "voleybol_youtube.json.bak"

GROUP = "🏐 VOLEYBOL CANLI"

CHANNEL_URL = "https://www.youtube.com/@tvfvoleyboltv/streams"
OFFICIAL_CHANNEL_ID = "UCTgQ8Bfq3AUuo1vWULdvRKw"

ISTANBUL = ZoneInfo("Europe/Istanbul")

MAX_VIDEOS = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Mobile Safari/537.36"
    )
}


# ==================================================
# YOUTUBE AYARLARI
# ==================================================

OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "nocheckcertificate": True,
    "http_headers": HEADERS,
    "socket_timeout": 25,
    "retries": 2,
    "extractor_retries": 2,
    "noplaylist": False,
}

DETAIL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "http_headers": HEADERS,
    "socket_timeout": 25,
    "retries": 2,
    "extractor_retries": 2,
    "noplaylist": True,
}


# ==================================================
# GENEL YARDIMCILAR
# ==================================================

def clean_title(value):
    if not value:
        return "TVF Voleybol Yayını"

    value = str(value)
    value = re.sub(r"\s+", " ", value)
    value = value.replace("\n", " ").strip()

    return value[:250]


def get_video_id(entry):
    if not entry:
        return ""

    video_id = entry.get("id")

    if not video_id:
        video_id = entry.get("url", "")

    if isinstance(video_id, str):
        match = re.search(
            r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})",
            video_id
        )

        if match:
            return match.group(1)

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return video_id

    return ""


def get_thumbnail(info, entry):
    sources = [info or {}, entry or {}]

    for source in sources:
        thumbnails = source.get("thumbnails") or []

        valid = [
            item for item in thumbnails
            if isinstance(item, dict) and item.get("url")
        ]

        if valid:
            valid.sort(
                key=lambda item: (
                    item.get("width") or 0,
                    item.get("height") or 0
                ),
                reverse=True
            )

            return valid[0]["url"]

        thumbnail = source.get("thumbnail")

        if thumbnail:
            return thumbnail

    return ""


def get_match_time(info, entry):
    sources = [info or {}, entry or {}]

    # Önce yaklaşan yayın için planlanan zamanı kontrol et.
    fields = (
        "release_timestamp",
        "scheduled_start_time",
        "timestamp",
        "release_timestamp_estimate",
    )

    for source in sources:
        for field in fields:
            value = source.get(field)

            if value:
                try:
                    dt = datetime.fromtimestamp(
                        float(value),
                        tz=timezone.utc
                    )

                    dt = dt.astimezone(ISTANBUL)

                    return dt.strftime("%d.%m.%Y %H:%M")

                except (ValueError, TypeError, OSError):
                    pass

    # Bazı YouTube kayıtlarında tarih metin olarak gelebilir.
    for source in sources:
        release_date = source.get("release_date")

        if release_date and re.fullmatch(r"\d{8}", str(release_date)):
            try:
                dt = datetime.strptime(
                    str(release_date),
                    "%Y%m%d"
                )

                return dt.strftime("%d.%m.%Y") + " Saat bekleniyor"

            except ValueError:
                pass

    return "Tarih bekleniyor"


def get_state(info, entry):
    info = info or {}
    entry = entry or {}

    status = (
        info.get("live_status")
        or entry.get("live_status")
        or ""
    )

    if info.get("is_live") or status == "is_live":
        return "CANLI"

    if info.get("is_upcoming") or status == "is_upcoming":
        return "YAKLAŞAN"

    if status == "was_live":
        return "TAMAMLANDI"

    return "YAYIN"


def get_stream_url(info, youtube_url, state):
    info = info or {}

    # Yaklaşan yayınlarda henüz oynatılabilir HLS adresi olmayabilir.
    if state == "YAKLAŞAN":
        return youtube_url

    formats = info.get("formats") or []

    candidates = []

    for item in formats:
        url = item.get("url", "")

        if not url:
            continue

        protocol = str(item.get("protocol", "")).lower()
        ext = str(item.get("ext", "")).lower()

        if (
            "m3u8" in protocol
            or "m3u8" in url.lower()
            or ext == "m3u8"
        ):
            candidates.append(item)

    if candidates:
        candidates.sort(
            key=lambda item: (
                item.get("height") or 0,
                item.get("tbr") or 0
            ),
            reverse=True
        )

        return candidates[0].get("url", youtube_url)

    # Bazı durumlarda yt-dlp doğrudan HLS adresi verebilir.
    direct_url = info.get("url", "")

    if direct_url and "m3u8" in direct_url.lower():
        return direct_url

    return youtube_url


# ==================================================
# YOUTUBE VİDEO DETAYI
# ==================================================

def scan_video(ydl, entry):
    video_id = get_video_id(entry)

    if not video_id:
        return None

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    print("\n------------------------------------")
    print("YouTube video:", video_id)

    info = {}

    try:
        info = ydl.extract_info(
            youtube_url,
            download=False
        ) or {}

    except Exception as error:
        error_text = str(error).lower()

        print("Detay bilgisi:", str(error)[:250])

        # Yaklaşan yayın bazı durumlarda henüz açılmadığı
        # için yt-dlp ayrıntıları alamayabilir.
        if (
            "will begin" in error_text
            or "upcoming" in error_text
            or "not started" in error_text
        ):
            info = {}
        else:
            info = {}

    title = clean_title(
        info.get("title")
        or entry.get("title")
        or "TVF Voleybol Yayını"
    )

    state = get_state(info, entry)

    thumbnail = get_thumbnail(info, entry)

    match_time = get_match_time(info, entry)

    stream_url = get_stream_url(
        info,
        youtube_url,
        state
    )

    print("Maç:", title)
    print("Durum:", state)
    print("Maç tarihi:", match_time)
    print("Maç görseli:", thumbnail or "Bulunamadı")

    if state == "TAMAMLANDI":
        print("Tamamlanmış yayın, listeye eklenmedi.")
        return None

    return {
        "video_id": video_id,
        "name": title,
        "title": title,
        "youtube_url": youtube_url,
        "stream_url": stream_url,
        "thumbnail": thumbnail,
        "match_time": match_time,
        "channel_id": OFFICIAL_CHANNEL_ID,
        "live_status": (
            info.get("live_status")
            or entry.get("live_status")
            or state.lower()
        ),
        "state": state,
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ==================================================
# RESMÎ TVF YAYINLARINI TARA
# ==================================================

def scan_channel():
    print("\n====================================")
    print("🏐 MIRTI68 TVF VOLEYBOL TARAMA")
    print("Resmî YouTube yayınları kontrol ediliyor")
    print("====================================")

    results = []
    seen = set()

    cookie_file = "cookies.txt"

    options = dict(OPTIONS)

    if os.path.isfile(cookie_file):
        options["cookiefile"] = cookie_file
        print("YouTube cookies.txt kullanılıyor.")

    try:
        with YoutubeDL(options) as ydl:
            playlist = ydl.extract_info(
                CHANNEL_URL,
                download=False
            )

            if not playlist:
                print("YouTube yayın sayfası okunamadı.")
                return results

            entries = playlist.get("entries") or []

            print("Bulunan video:", len(entries))

            detail_options = dict(DETAIL_OPTIONS)

            if os.path.isfile(cookie_file):
                detail_options["cookiefile"] = cookie_file

            with YoutubeDL(detail_options) as detail_ydl:
                for index, entry in enumerate(entries, start=1):
                    if not entry:
                        continue

                    video_id = get_video_id(entry)

                    if not video_id or video_id in seen:
                        continue

                    seen.add(video_id)

                    print(
                        f"\n[{index}/{len(entries)}] "
                        "Yayın kontrol ediliyor..."
                    )

                    try:
                        item = scan_video(
                            detail_ydl,
                            entry
                        )

                        if item:
                            results.append(item)

                    except Exception as error:
                        print(
                            "Video tarama hatası:",
                            str(error)[:250]
                        )

    except Exception as error:
        print("\nYouTube kanal tarama hatası:")
        print(str(error)[:500])

    # Canlı yayınlar önce, yaklaşanlar sonra.
    results.sort(
        key=lambda item: (
            0 if item["state"] == "CANLI" else 1,
            item.get("match_time", "")
        )
    )

    print("\nToplam bulunan yayın:", len(results))

    return results


# ==================================================
# ESKİ VOLEYBOL GRUBUNU M3U'DAN ÇIKAR
# ==================================================

def remove_old_group(lines):
    output = []
    skip_url = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#EXTINF:"):
            if f'group-title="{GROUP}"' in stripped:
                skip_url = True
                continue

            skip_url = False
            output.append(line)
            continue

        if skip_url:
            if stripped and not stripped.startswith("#"):
                skip_url = False
                continue

            if stripped.startswith("#"):
                continue

        output.append(line)

    return output


# ==================================================
# M3U VE JSON DOSYALARINI GÜVENLİ KAYDET
# ==================================================

def atomic_write(path, content):
    directory = os.path.dirname(path) or "."

    fd, temp_path = tempfile.mkstemp(
        prefix="mirti68_",
        suffix=".tmp",
        dir=directory
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

        os.replace(temp_path, path)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def save_files(items):
    print("\n====================================")
    print("Dosyalar hazırlanıyor...")
    print("====================================")

    if os.path.isfile(MASTER_FILE):
        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as file:
            old_lines = file.readlines()

        shutil.copy2(
            MASTER_FILE,
            BACKUP_FILE
        )

    else:
        old_lines = ["#EXTM3U\n"]

    # Eski voleybol grubunu temizle.
    base_lines = remove_old_group(old_lines)

    if not base_lines:
        base_lines = ["#EXTM3U\n"]

    if not any(
        line.strip() == "#EXTM3U"
        for line in base_lines
    ):
        base_lines.insert(0, "#EXTM3U\n")

    new_lines = list(base_lines)

    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    # Yeni voleybol yayınlarını ekle.
    for item in items:
        name = clean_title(item.get("name"))

        state = item.get("state", "YAYIN")

        match_time = item.get(
            "match_time",
            "Tarih bekleniyor"
        )

        thumbnail = item.get("thumbnail", "")

        stream_url = item.get("stream_url", "")

        if not stream_url:
            continue

        # M3U içindeki tırnakları temizle.
        thumbnail = str(thumbnail).replace('"', "%22")

        thumbnail_tag = (
            f' tvg-logo="{thumbnail}"'
            if thumbnail else ""
        )

        channel_name = (
            f"🏐 {name} | {match_time} | {state}"
        )

        new_lines.append(
            f'#EXTINF:-1{thumbnail_tag} '
            f'group-title="{GROUP}",{channel_name}\n'
        )

        new_lines.append(stream_url + "\n")

    m3u_content = "".join(new_lines)

    # JSON çıktısı.
    json_content = json.dumps(
        {
            "channel": "TVF Voleybol TV",
            "channel_id": OFFICIAL_CHANNEL_ID,
            "channel_url": CHANNEL_URL,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total": len(items),
            "matches": items
        },
        ensure_ascii=False,
        indent=2
    )

    # Önceki JSON yedeği.
    if os.path.isfile(RESULT_FILE):
        shutil.copy2(
            RESULT_FILE,
            JSON_BACKUP
        )

    atomic_write(
        MASTER_FILE,
        m3u_content
    )

    atomic_write(
        RESULT_FILE,
        json_content
    )

    print("\n✅ M3U güncellendi:", MASTER_FILE)
    print("✅ JSON güncellendi:", RESULT_FILE)
    print("✅ Yedek:", BACKUP_FILE)
    print("✅ Bulunan voleybol yayını:", len(items))


# ==================================================
# ANA PROGRAM
# ==================================================

def main():
    print("====================================")
    print("MIRTI68 - TVF VOLEYBOL GÜNCELLEME")
    print("====================================")

    items = scan_channel()

    if not items:
        print(
            "\n⚠️ Yeni yayın bulunamadı. "
            "Mevcut M3U dosyası korunuyor."
        )
        return

    save_files(items)

    print("\n====================================")
    print("🏐 VOLEYBOL GÜNCELLEMESİ TAMAMLANDI")
    print("====================================")

    for item in items:
        print(
            item["state"],
            "|",
            item["match_time"],
            "|",
            item["name"]
        )


if __name__ == "__main__":
    main()
