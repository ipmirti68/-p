import os
import re
import json
import tempfile
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from yt_dlp import YoutubeDL


# ==================================================
# MIRTI68 - KUZEYBORU HLS TARAMA
# ==================================================

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"

CHANNEL_URL = "https://www.youtube.com/@tvfvoleyboltv/streams"
OFFICIAL_CHANNEL_ID = "UCTgQ8Bfq3AUuo1vWULdvRKw"

GROUP = "🏐 KUZEYBORU"
OLD_GROUP = "🏐 VOLEYBOL CANLI"

ISTANBUL = ZoneInfo("Europe/Istanbul")

MAX_VIDEOS = 50

# Yalnızca bu takımlara ait maçları takip et.
PRIORITY_TEAMS = (
    "kuzeyboru maxi",
    "kuzeyboru",
)

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
# YARDIMCI FONKSİYONLAR
# ==================================================

def clean_title(value):
    if not value:
        return "Kuzeyboru Voleybol"

    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()[:250]


def normalize_text(value):
    value = str(value or "").lower()

    value = value.replace("ı", "i")
    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    return value


def is_priority_match(title):
    title = normalize_text(title)

    return any(
        normalize_text(team) in title
        for team in PRIORITY_TEAMS
    )


def get_video_id(entry):
    if not entry:
        return ""

    value = entry.get("id") or entry.get("url") or ""

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

    # YouTube görseli için standart yedek adres.
    if video_id:
        return (
            f"https://i.ytimg.com/vi/"
            f"{video_id}/hqdefault.jpg"
        )

    return ""


def get_match_time(info, entry):
    sources = [info or {}, entry or {}]

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

                    return dt.astimezone(
                        ISTANBUL
                    ).strftime("%d.%m.%Y %H:%M")

                except (ValueError, TypeError, OSError):
                    pass

    for source in sources:
        release_date = source.get("release_date")

        if release_date and re.fullmatch(
            r"\d{8}", str(release_date)
        ):
            try:
                dt = datetime.strptime(
                    str(release_date),
                    "%Y%m%d"
                )

                return dt.strftime(
                    "%d.%m.%Y"
                ) + " Saat bekleniyor"

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
# GERÇEK HLS ADRESİNİ BUL
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

    direct_url = info.get("url") or ""

    if "m3u8" in direct_url.lower():
        return direct_url

    return ""


# ==================================================
# YOUTUBE VİDEO DETAYI
# ==================================================

def scan_video(ydl, entry):
    video_id = get_video_id(entry)

    if not video_id:
        return None

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    entry_title = clean_title(
        entry.get("title")
    )

    # Önce başlıktan takım kontrolü.
    if not is_priority_match(entry_title):
        return None

    print("\n------------------------------------")
    print("Öncelikli maç:", entry_title)
    print("Video ID:", video_id)

    info = {}

    try:
        info = ydl.extract_info(
            youtube_url,
            download=False
        ) or {}

    except Exception as error:
        print(
            "YouTube detay bilgisi alınamadı:",
            str(error)[:200]
        )

    title = clean_title(
        info.get("title") or entry_title
    )

    # Gerçek başlık üzerinden tekrar kontrol.
    if not is_priority_match(title):
        print("Takım eşleşmesi bulunamadı.")
        return None

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
        print("Tamamlanmış maç atlandı.")
        return None

    if hls_url:
        hls_status = "HLS_BULUNDU"
        print("✅ Gerçek HLS adresi bulundu.")
    else:
        hls_status = "HLS_HENUZ_YOK"
        print("⏳ HLS adresi henüz alınamadı.")

    print("Maç:", title)
    print("Durum:", state)
    print("Tarih:", match_time)
    print("Görsel:", thumbnail or "Yok")

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
        "channel_id": OFFICIAL_CHANNEL_ID,
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ==================================================
# TVF YOUTUBE YAYINLARINI TARA
# ==================================================

def scan_channel():
    print("\n====================================")
    print("MIRTI68 KUZEYBORU TARAMASI")
    print("Kuzeyboru ve Kuzeyboru Maxi")
    print("====================================")

    results = []
    seen = set()

    options = dict(OPTIONS)
    detail_options = dict(DETAIL_OPTIONS)

    cookie_file = "cookies.txt"

    if os.path.isfile(cookie_file):
        options["cookiefile"] = cookie_file
        detail_options["cookiefile"] = cookie_file
        print("YouTube çerezleri kullanılıyor.")

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

            print("Toplam YouTube kaydı:", len(entries))

            with YoutubeDL(detail_options) as detail_ydl:
                for index, entry in enumerate(entries, start=1):
                    if not entry:
                        continue

                    video_id = get_video_id(entry)

                    if not video_id or video_id in seen:
                        continue

                    seen.add(video_id)

                    entry_title = clean_title(
                        entry.get("title")
                    )

                    if not is_priority_match(entry_title):
                        continue

                    print(
                        f"\n[{index}/{len(entries)}] "
                        "Öncelikli maç inceleniyor..."
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
                            "Tarama hatası:",
                            str(error)[:250]
                        )

    except Exception as error:
        print("\nYouTube tarama hatası:")
        print(str(error)[:500])

    # Önce Kuzeyboru Maxi, ardından Kuzeyboru;
    # aynı öncelik içinde canlı yayınlar önce.
    def sort_key(item):
        title = normalize_text(item["name"])

        if "kuzeyboru maxi" in title:
            team_priority = 0
        else:
            team_priority = 1

        live_priority = (
            0 if item["state"] == "CANLI" else 1
        )

        return team_priority, live_priority, item["match_time"]

    results.sort(key=sort_key)

    print("\nToplam öncelikli maç:", len(results))
    print(
        "HLS bulunan maç:",
        sum(1 for item in results if item["stream_url"])
    )

    return results


# ==================================================
# ESKİ VOLEYBOL GRUPLARINI TEMİZLE
# ==================================================

def remove_old_groups(lines):
    output = []
    skip_url = False

    groups_to_remove = (
        f'group-title="{GROUP}"',
        f'group-title="{OLD_GROUP}"',
    )

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#EXTINF:"):
            if any(
                group in stripped
                for group in groups_to_remove
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
# DOSYAYI GÜVENLİ KAYDET
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


# ==================================================
# M3U VE JSON KAYDET
# ==================================================

def save_files(items):
    print("\nDosyalar hazırlanıyor...")

    # JSON'da HLS bulunmayan maçlar da saklanır.
    json_content = json.dumps(
        {
            "channel": "TVF Voleybol TV",
            "channel_id": OFFICIAL_CHANNEL_ID,
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

    # HLS yoksa eski M3U kayıtlarını silme.
    if not hls_items:
        print(
            "⚠️ Gerçek HLS bulunamadı. "
            "Mevcut M3U korunuyor."
        )
        print("JSON güncellendi:", RESULT_FILE)
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

        hls_url = item["stream_url"]

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

        new_lines.append(hls_url + "\n")

    atomic_write(
        MASTER_FILE,
        "".join(new_lines)
    )

    print("\n✅ M3U güncellendi:", MASTER_FILE)
    print("✅ JSON güncellendi:", RESULT_FILE)
    print("✅ M3U'ya eklenen gerçek HLS:", len(hls_items))


# ==================================================
# ANA PROGRAM
# ==================================================

def main():
    print("====================================")
    print("MIRTI68 - KUZEYBORU HLS BOT")
    print("====================================")

    items = scan_channel()

    if not items:
        print(
            "\nÖncelikli Kuzeyboru maçı bulunamadı."
        )
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
