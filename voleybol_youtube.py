import os
import re
import json
import tempfile
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from yt_dlp import YoutubeDL


# ==================================================
# MIRTI68 - TVF VOLEYBOL HLS TARAMA
# ==================================================

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"

CHANNEL_URL = (
    "https://www.youtube.com/channel/"
    "UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
)

# Kullanıcının verdiği doğrudan yayın bağlantısı.
SEED_VIDEO_URLS = [
    "https://www.youtube.com/watch?v=cMM1VRfJlpI",
]

CHANNEL_ID = "UCTgQ8Bfq3AUuo1vWULdvRKw"

GROUP = "🏐 VOLEYBOL HLS"
OLD_GROUPS = (
    "🏐 VOLEYBOL CANLI",
    "🏐 KUZEYBORU",
    "🏐 VOLEYBOL HLS",
)

ISTANBUL = ZoneInfo("Europe/Istanbul")
MAX_VIDEOS = 50

PRIORITY_TEAMS = (
    "kuzeyboru maxi",
    "kuzeyboru",
)

# YouTube için özel mobil User-Agent kullanmıyoruz.
# yt-dlp kendi istemci başlıklarını yönetsin.

OPTIONS = {
    "quiet": True,
    "no_warnings": False,
    "ignoreerrors": True,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "socket_timeout": 30,
    "retries": 2,
    "extractor_retries": 2,
    "noplaylist": False,
}

DETAIL_OPTIONS = {
    "quiet": True,
    "no_warnings": False,
    "ignoreerrors": False,
    "skip_download": True,
    "socket_timeout": 30,
    "retries": 2,
    "extractor_retries": 2,
    "noplaylist": True,
}


# ==================================================
# YARDIMCILAR
# ==================================================

def clean_title(value):
    if not value:
        return "TVF Voleybol Yayını"

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()[:250]


def normalize_text(value):
    value = str(value or "").lower()
    value = value.replace("ı", "i")

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    return "".join(
        char for char in value
        if not unicodedata.combining(char)
    )


def team_priority(title):
    title = normalize_text(title)

    if "kuzeyboru maxi" in title:
        return 0

    if "kuzeyboru" in title:
        return 1

    return 2


def get_video_id(value):
    if isinstance(value, dict):
        value = (
            value.get("id")
            or value.get("url")
            or value.get("webpage_url")
            or ""
        )

    if not isinstance(value, str):
        return ""

    match = re.search(
        r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})",
        value
    )

    if match:
        return match.group(1)

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    return ""


def get_thumbnail(info, entry, video_id):
    for source in (info or {}, entry or {}):
        thumbnails = source.get("thumbnails") or []

        valid = [
            item for item in thumbnails
            if isinstance(item, dict)
            and item.get("url")
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

        if source.get("thumbnail"):
            return source["thumbnail"]

    if video_id:
        return (
            f"https://i.ytimg.com/vi/"
            f"{video_id}/hqdefault.jpg"
        )

    return ""


def get_match_time(info, entry):
    for source in (info or {}, entry or {}):
        for field in (
            "release_timestamp",
            "scheduled_start_time",
            "timestamp",
            "release_timestamp_estimate",
        ):
            value = source.get(field)

            if value:
                try:
                    dt = datetime.fromtimestamp(
                        float(value),
                        timezone.utc
                    )

                    return dt.astimezone(
                        ISTANBUL
                    ).strftime("%d.%m.%Y %H:%M")

                except (ValueError, TypeError, OSError):
                    pass

        release_date = source.get("release_date")

        if release_date and re.fullmatch(
            r"\d{8}",
            str(release_date)
        ):
            try:
                dt = datetime.strptime(
                    str(release_date),
                    "%Y%m%d"
                )

                return (
                    dt.strftime("%d.%m.%Y")
                    + " Saat bekleniyor"
                )

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


# ==================================================
# HLS ADRESİNİ BUL
# ==================================================

def get_hls_url(info):
    info = info or {}

    candidates = []

    for item in info.get("formats") or []:
        if not isinstance(item, dict):
            continue

        url = item.get("url") or ""

        if not url:
            continue

        protocol = str(
            item.get("protocol") or ""
        ).lower()

        ext = str(
            item.get("ext") or ""
        ).lower()

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

        return candidates[0].get("url", "")

    # Bazı yt-dlp sonuçlarında doğrudan manifest_url gelebilir.
    manifest_url = info.get("manifest_url") or ""

    if "m3u8" in manifest_url.lower():
        return manifest_url

    direct_url = info.get("url") or ""

    if "m3u8" in direct_url.lower():
        return direct_url

    return ""


# ==================================================
# VİDEOYU İNCELE
# ==================================================

def scan_video(ydl, video_id, entry=None):
    entry = entry or {}

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print("\n------------------------------------")
    print("Video:", youtube_url)

    info = {}

    try:
        info = ydl.extract_info(
            youtube_url,
            download=False
        ) or {}

    except Exception as error:
        print(
            "Video bilgisi alınamadı:",
            str(error)[:300]
        )

    title = clean_title(
        info.get("title")
        or entry.get("title")
        or video_id
    )

    state = get_state(info, entry)

    thumbnail = get_thumbnail(
        info,
        entry,
        video_id
    )

    match_time = get_match_time(
        info,
        entry
    )

    hls_url = get_hls_url(info)

    if state == "TAMAMLANDI":
        print("Tamamlanmış yayın.")
        return None

    if hls_url:
        hls_status = "HLS_BULUNDU"
        print("✅ HLS bulundu.")
    else:
        hls_status = "HLS_HENUZ_YOK"
        print("⏳ HLS bulunamadı.")

    print("Maç:", title)
    print("Tarih:", match_time)
    print("Durum:", state)
    print("Görsel:", thumbnail or "Bulunamadı")

    return {
        "video_id": video_id,
        "name": title,
        "title": title,
        "youtube_url": youtube_url,
        "stream_url": hls_url,
        "thumbnail": thumbnail,
        "match_time": match_time,
        "state": state,
        "hls_status": hls_status,
        "priority": team_priority(title),
        "channel_id": CHANNEL_ID,
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ==================================================
# KANAL VE DOĞRUDAN VİDEO TARAMASI
# ==================================================

def scan_channel():
    print("\n====================================")
    print("MIRTI68 - TÜM VOLEYBOL HLS TARAMA")
    print("Kuzeyboru ve Kuzeyboru Maxi öncelikli")
    print("====================================")

    entries = []
    video_ids = []
    seen = set()

    # 1. Önce kullanıcının verdiği doğrudan videolar.
    for url in SEED_VIDEO_URLS:
        video_id = get_video_id(url)

        if video_id and video_id not in seen:
            seen.add(video_id)
            video_ids.append(video_id)

    # 2. Ardından resmî TVF kanalındaki yayınlar.
    channel_options = dict(OPTIONS)

    cookie_file = "cookies.txt"

    if os.path.isfile(cookie_file):
        channel_options["cookiefile"] = cookie_file

    try:
        with YoutubeDL(channel_options) as ydl:
            playlist = ydl.extract_info(
                CHANNEL_URL,
                download=False
            )

            if playlist:
                entries = playlist.get("entries") or []

                print(
                    "Kanal sayfasındaki kayıt:",
                    len(entries)
                )

                for entry in entries:
                    if not entry:
                        continue

                    video_id = get_video_id(entry)

                    if video_id and video_id not in seen:
                        seen.add(video_id)
                        video_ids.append(video_id)

            else:
                print(
                    "⚠️ Kanal sekmesi okunamadı. "
                    "Doğrudan video kontrolüne devam ediliyor."
                )

    except Exception as error:
        print(
            "⚠️ Kanal sekmesi hatası:",
            str(error)[:300]
        )

    print("\nKontrol edilecek video:", len(video_ids))

    results = []

    detail_options = dict(DETAIL_OPTIONS)

    if os.path.isfile(cookie_file):
        detail_options["cookiefile"] = cookie_file

    with YoutubeDL(detail_options) as detail_ydl:
        for index, video_id in enumerate(
            video_ids,
            start=1
        ):
            print(
                f"\n[{index}/{len(video_ids)}] "
                "Video inceleniyor..."
            )

            entry = next(
                (
                    item for item in entries
                    if get_video_id(item) == video_id
                ),
                {}
            )

            try:
                item = scan_video(
                    detail_ydl,
                    video_id,
                    entry
                )

                if item:
                    results.append(item)

            except Exception as error:
                print(
                    "Video hatası:",
                    str(error)[:300]
                )

    # Kuzeyboru Maxi önce, Kuzeyboru sonra,
    # diğer maçlar en son.
    results.sort(
        key=lambda item: (
            item["priority"],
            0 if item["state"] == "CANLI" else 1,
            item["match_time"]
        )
    )

    print("\nToplam incelenen sonuç:", len(results))

    print(
        "HLS bulunan:",
        sum(
            1 for item in results
            if item["stream_url"]
        )
    )

    return results


# ==================================================
# ESKİ VOLEYBOL GRUPLARINI TEMİZLE
# ==================================================

def remove_old_groups(lines):
    output = []
    skip_url = False

    group_markers = [
        f'group-title="{group}"'
        for group in OLD_GROUPS
    ]

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#EXTINF:"):
            if any(
                marker in stripped
                for marker in group_markers
            ):
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
# DOSYA KAYDET
# ==================================================

def atomic_write(path, content):
    directory = os.path.dirname(path) or "."

    fd, temp_path = tempfile.mkstemp(
        prefix="mirti68_",
        suffix=".tmp",
        dir=directory
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as file:
            file.write(content)

        os.replace(temp_path, path)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)

        raise


def save_files(items):
    # JSON: HLS olmayan maçlar da kaydedilir.
    json_content = json.dumps(
        {
            "channel": "TVF Voleybol TV",
            "channel_id": CHANNEL_ID,
            "channel_url": CHANNEL_URL,
            "priority_teams": list(PRIORITY_TEAMS),
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total": len(items),
            "hls_total": sum(
                1 for item in items
                if item.get("stream_url")
            ),
            "matches": items
        },
        ensure_ascii=False,
        indent=2
    )

    atomic_write(
        RESULT_FILE,
        json_content
    )

    hls_items = [
        item for item in items
        if item.get("stream_url")
        and "m3u8" in item["stream_url"].lower()
    ]

    # HLS bulunmadıysa mevcut listeyi koru.
    if not hls_items:
        print(
            "\n⚠️ HLS bulunamadı. "
            "Mevcut M3U değiştirilmedi."
        )
        return

    if os.path.isfile(MASTER_FILE):
        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as file:
            old_lines = file.readlines()
    else:
        old_lines = ["#EXTM3U\n"]

    base_lines = remove_old_groups(old_lines)

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

    for item in hls_items:
        name = clean_title(item["name"])

        match_time = item.get(
            "match_time",
            "Tarih bekleniyor"
        )

        state = item.get("state", "CANLI")

        thumbnail = str(
            item.get("thumbnail") or ""
        ).replace('"', "%22")

        logo_tag = (
            f' tvg-logo="{thumbnail}"'
            if thumbnail else ""
        )

        channel_name = (
            f"🏐 {name} | {match_time} | {state}"
        )

        new_lines.append(
            f'#EXTINF:-1{logo_tag} '
            f'group-title="{GROUP}",{channel_name}\n'
        )

        new_lines.append(
            item["stream_url"] + "\n"
        )

    atomic_write(
        MASTER_FILE,
        "".join(new_lines)
    )

    print("\n✅ M3U güncellendi:", MASTER_FILE)
    print("✅ JSON güncellendi:", RESULT_FILE)
    print("✅ M3U'ya eklenen HLS:", len(hls_items))


# ==================================================
# ANA PROGRAM
# ==================================================

def main():
    print("====================================")
    print("MIRTI68 VOLEYBOL HLS BOT")
    print("====================================")

    items = scan_channel()

    if not items:
        print("İncelenecek video bulunamadı.")
        return

    save_files(items)

    print("\n====================================")
    print("TARAMA TAMAMLANDI")
    print("====================================")

    for item in items:
        print(
            item["hls_status"],
            "|",
            item["match_time"],
            "|",
            item["name"]
        )


if __name__ == "__main__":
    main()
