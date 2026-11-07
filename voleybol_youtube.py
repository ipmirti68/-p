
import os
import re
import json
import time
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - VOLEYBOL CANLI + ESKI MACLAR
# ==========================================

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"

CHANNEL_URL = (
    "https://www.youtube.com/channel/"
    "UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
)

GROUP_LIVE = "🏐 VOLEYBOL HLS"
GROUP_REPLAY = "🏐 SULTANLAR LİGİ TEKRAR"

MAX_VIDEOS = 60
MAX_LIVE = 5
MAX_REPLAY = 60

KEYWORDS = (
    "sultanlar",
    "kuzeyboru",
    "voleybol",
    "tvf",
    "misli.com",
    "eczacıbaşı",
    "eczacibasi",
    "vakıfbank",
    "vakifbank",
    "fenerbahçe",
    "fenerbahce",
    "galatasaray",
    "nilüfer",
    "nilufer",
    "nilüfer belediye",
    "nilufer belediye",
    "voleybol ligi",
    "kadınlar ligi",
    "kadinlar ligi",
    "efeler ligi",
)

# ==========================================
# YOUTUBE AYARLARI
# ==========================================

OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"]
        }
    },
}

DETAIL = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": False,
    "skip_download": True,
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"]
        }
    },
}

# ==========================================
# VIDEO ID
# ==========================================

def get_id(video):

    vid = str(video.get("id") or "")

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return vid

    url = str(video.get("url") or "")

    match = re.search(
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        url
    )

    return match.group(1) if match else ""


# ==========================================
# HLS ADRESİ BUL
# ==========================================

def get_hls(info):

    if not info:
        return ""

    # Önce doğrudan manifest alanlarını kontrol et.
    for key in ("hls_manifest_url", "manifest_url"):

        value = info.get(key)

        if value and "m3u8" in str(value).lower():
            return value

    formats = info.get("formats") or []

    # HLS formatlarını bul.
    for fmt in formats:

        url = str(fmt.get("url") or "")
        protocol = str(fmt.get("protocol") or "").lower()
        ext = str(fmt.get("ext") or "").lower()

        if not url:
            continue

        if (
            "m3u8" in url.lower()
            or "m3u8" in protocol
            or "hls" in protocol
            or ext == "m3u8"
        ):
            return url

    # Bazı videolarda birleştirilmiş formatlar bulunabilir.
    for fmt in info.get("requested_formats") or []:

        url = str(fmt.get("url") or "")
        protocol = str(fmt.get("protocol") or "").lower()

        if url and (
            "m3u8" in url.lower()
            or "hls" in protocol
        ):
            return url

    return ""


# ==========================================
# YAYIN TÜRÜ
# ==========================================

def is_upcoming(info):

    status = info.get("live_status") or ""

    if status == "is_upcoming":
        return True

    release_time = info.get("release_timestamp")

    if release_time:

        if release_time > time.time():
            return True

    return False


def is_live_video(info):

    return (
        info.get("is_live") is True
        or info.get("live_status") == "is_live"
    )


# ==========================================
# VIDEO TARA
# ==========================================

def scan():

    print("====================================")
    print("MIRTI68 VOLEYBOL TARAMA")
    print("CANLI + ESKI MACLAR")
    print("====================================")

    videos = []

    try:

        with YoutubeDL(OPTIONS) as ydl:

            playlist = ydl.extract_info(
                CHANNEL_URL,
                download=False
            )

            if not playlist:
                print("Kanal bilgisi alinamadi.")
                return None

            for entry in playlist.get("entries") or []:

                if not entry:
                    continue

                vid = get_id(entry)

                if vid:
                    videos.append((vid, entry))

    except Exception as error:

        print(f"Kanal tarama hatasi: {error}")
        return None

    # Tekrarlanan video ID'lerini temizle.
    unique_videos = []
    playlist_seen = set()

    for vid, entry in videos:

        if vid not in playlist_seen:

            playlist_seen.add(vid)
            unique_videos.append((vid, entry))

    videos = unique_videos

    print(f"Bulunan video: {len(videos)}")

    if not videos:
        print("Video listesi bos.")
        return None

    results = []
    result_seen = set()

    with YoutubeDL(DETAIL) as ydl:

        for index, (vid, entry) in enumerate(videos, 1):

            print(
                f"\n[{index}/{len(videos)}] "
                f"Video kontrol: {vid}"
            )

            video_url = (
                f"https://www.youtube.com/watch?v={vid}"
            )

            try:

                info = ydl.extract_info(
                    video_url,
                    download=False
                )

            except Exception as error:

                print(f"Video atlandi: {error}")
                continue

            if not info:
                print("Video bilgisi alinamadi.")
                continue

            title = (
                info.get("title")
                or entry.get("title")
                or vid
            )

            # Başlık ve açıklamada voleybol kelimelerini ara.
            description = info.get("description") or ""

            search_text = (
                title + " " + description
            ).lower()

            if not any(
                keyword in search_text
                for keyword in KEYWORDS
            ):
                print("Voleybol anahtar kelimesi bulunamadi.")
                continue

            if is_upcoming(info):

                print("Baslamamis yayin, atlandi.")
                continue

            # HLS adresini bul.
            hls = get_hls(info)

            if not hls:

                print("HLS bulunamadi.")
                continue

            if vid in result_seen:
                continue

            result_seen.add(vid)

            live = is_live_video(info)

            # Canlı değilse ve başlamamış değilse tekrar kabul et.
            is_replay = not live

            clean_title = re.sub(
                r"[\r\n]+",
                " ",
                str(title)
            ).strip()

            print(
                f"{'CANLI' if live else 'TEKRAR'}: "
                f"{clean_title}"
            )

            results.append({
                "id": vid,
                "name": clean_title,
                "stream_url": hls,
                "is_replay": is_replay,
                "live_status": info.get("live_status"),
            })

            time.sleep(0.5)

    print("\n====================================")
    print("Tarama tamamlandi.")
    print(f"Bulunan yayin: {len(results)}")
    print("====================================")

    return results


# ==========================================
# ESKI GRUPLARI TEMIZLE
# DIGER KANALLARI KORU
# ==========================================

def remove_old_groups(old_lines):

    preamble = []
    blocks = []
    current = None

    for line in old_lines:

        if line.startswith("#EXTINF:"):

            if current is not None:
                blocks.append(current)

            current = [line]

        elif current is not None:

            current.append(line)

        else:

            preamble.append(line)

    if current is not None:
        blocks.append(current)

    keep_blocks = []

    for block in blocks:

        extinf = block[0]

        match = re.search(
            r'group-title="([^"]*)"',
            extinf
        )

        group = match.group(1) if match else ""

        if group in (GROUP_LIVE, GROUP_REPLAY):

            print(
                f"Eski voleybol grubu yenilenecek: {group}"
            )

            continue

        keep_blocks.append(block)

    return preamble, keep_blocks


# ==========================================
# M3U KAYDET
# ==========================================

def save(items):

    # Tarama başarısızsa listeye dokunma.
    if items is None:

        print("Tarama basarisiz. M3U korunuyor.")
        return

    # HLS bulunamadıysa eski kayıtları koru.
    if not items:

        print("Gecerli yayin bulunamadi.")
        print("Eski voleybol gruplari korundu.")
        return

    live = [
        item for item in items
        if not item.get("is_replay")
    ]

    replay = [
        item for item in items
        if item.get("is_replay")
    ]

    print("\n====================================")
    print(f"CANLI: {len(live)}")
    print(f"TEKRAR: {len(replay)}")
    print("====================================")

    # Ana listeyi oku.
    if os.path.isfile(MASTER_FILE):

        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as file:

            old_lines = file.read().splitlines()

    else:

        old_lines = ["#EXTM3U"]

    # Sadece kendi gruplarımızı ayıkla.
    preamble, keep_blocks = remove_old_groups(
        old_lines
    )

    final_lines = list(preamble)

    if not any(
        line.strip() == "#EXTM3U"
        for line in final_lines
    ):

        final_lines.insert(0, "#EXTM3U")

    # Diğer kanalları koru.
    for block in keep_blocks:
        final_lines.extend(block)

    # CANLI YAYINLAR
    live_seen = set()

    for item in live[:MAX_LIVE]:

        vid = item["id"]

        if vid in live_seen:
            continue

        live_seen.add(vid)

        final_lines.append(
            f'#EXTINF:-1 group-title="{GROUP_LIVE}",'
            f'{item["name"]} | CANLI'
        )

        final_lines.append(
            item["stream_url"]
        )

    # ESKİ MAÇLAR / TEKRARLAR
    replay_seen = set()

    for item in replay[:MAX_REPLAY]:

        vid = item["id"]

        if vid in replay_seen:
            continue

        replay_seen.add(vid)

        final_lines.append(
            f'#EXTINF:-1 group-title="{GROUP_REPLAY}",'
            f'{item["name"]} | TEKRAR'
        )

        final_lines.append(
            item["stream_url"]
        )

    # Ana M3U dosyasını güncelle.
    with open(
        MASTER_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(final_lines) + "\n"
        )

    # JSON dosyasını güncelle.
    with open(
        RESULT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            items,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\n====================================")
    print("MIRTI68 VOLEYBOL GUNCELLENDI")
    print("====================================")
    print(f"Canli yayin: {len(live_seen)}")
    print(f"Tekrar yayin: {len(replay_seen)}")
    print(f"Ana liste: {MASTER_FILE}")
    print(f"JSON: {RESULT_FILE}")
    print("Diger kanallar: KORUNDU")
    print("Yedek dosya: YOK")
    print("====================================")


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    items = scan()
    save(items)


if __name__ == "__main__":
    main()
