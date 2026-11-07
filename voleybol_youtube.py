
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

OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    },
}

DETAIL = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "skip_download": True,
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    },
}


# ==========================================
# VIDEO ID
# ==========================================

def get_id(v):

    m = re.search(
        r"([A-Za-z0-9_-]{11})",
        str(v.get("id") or "")
    )

    return m.group(1) if m else ""


# ==========================================
# HLS BUL
# ==========================================

def get_hls(info):

    for f in (info or {}).get("formats") or []:

        u = f.get("url") or ""

        proto = str(
            f.get("protocol") or ""
        ).lower()

        if (
            "m3u8" in u.lower()
            or "m3u8" in proto
            or "hls" in proto
        ):
            return u

    return ""


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

            pl = ydl.extract_info(
                CHANNEL_URL,
                download=False
            )

            if not pl:
                print("Kanal bilgisi alinamadi.")
                return None

            for entry in pl.get("entries") or []:

                if not entry:
                    continue

                vid = get_id(entry)

                if vid:
                    videos.append((vid, entry))

    except Exception as e:

        print(f"Kanal tarama hatasi: {e}")
        return None

    print(f"Bulunan video: {len(videos)}")

    results = []
    seen = set()

    with YoutubeDL(DETAIL) as ydl:

        for index, (vid, entry) in enumerate(videos, 1):

            print(
                f"\n[{index}/{len(videos)}] "
                f"Video kontrol: {vid}"
            )

            url = (
                f"https://www.youtube.com/watch?v={vid}"
            )

            try:

                info = ydl.extract_info(
                    url,
                    download=False
                ) or {}

            except Exception as e:

                print(f"Video atlandi: {e}")
                continue

            if not info:
                continue

            title = (
                info.get("title")
                or entry.get("title")
                or vid
            )

            low = title.lower()

            # İlgili voleybol yayınları
            keywords = (
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
                "nilüfer belediye",
                "aralarında",
            )

            if not any(k in low for k in keywords):
                continue

            status = (
                info.get("live_status")
                or entry.get("live_status")
                or ""
            )

            if status == "is_upcoming":
                print("Baslamamis yayin, atlandi.")
                continue

            hls = get_hls(info)

            if not hls:
                print("HLS bulunamadi.")
                continue

            if vid in seen:
                continue

            seen.add(vid)

            is_replay = (
                status == "was_live"
                or status == "not_live"
                or info.get("live_status") == "was_live"
                or info.get("live_status") == "not_live"
                or info.get("live_status") is None
            )

            print(
                f"{'TEKRAR' if is_replay else 'CANLI'}: {title}"
            )

            results.append({
                "id": vid,
                "name": title,
                "stream_url": hls,
                "is_replay": is_replay
            })

            time.sleep(0.5)

    print("\nTarama tamamlandi.")
    print(f"Bulunan yayin: {len(results)}")

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

        if group in (
            GROUP_LIVE,
            GROUP_REPLAY
        ):

            print(f"Eski voleybol grubu yenilenecek: {group}")
            continue

        keep_blocks.append(block)

    return preamble, keep_blocks


# ==========================================
# M3U KAYDET
# ==========================================

def save(items):

    # Tarama başarısızsa mevcut listeyi koru.
    if items is None:

        print("Tarama basarisiz. M3U korunuyor.")
        return

    # Hic HLS bulunamadiysa eski listeyi koru.
    if not items:

        print("Gecerli yayin bulunamadi.")
        print("Eski voleybol gruplari korundu.")
        return

    live = [
        i for i in items
        if not i.get("is_replay")
    ]

    replay = [
        i for i in items
        if i.get("is_replay")
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
        ) as f:

            old_lines = f.read().splitlines()

    else:

        old_lines = ["#EXTM3U"]

    # Eski voleybol gruplarini ayikla.
    preamble, keep_blocks = remove_old_groups(
        old_lines
    )

    final_lines = list(preamble)

    if not any(
        line.strip() == "#EXTM3U"
        for line in final_lines
    ):

        final_lines.insert(0, "#EXTM3U")

    # Diger kanallari koru.
    for block in keep_blocks:
        final_lines.extend(block)

    # Canli yayinlari ekle.
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

    # Eski maclari ekle.
    replay_seen = set()

    for item in replay[:MAX_VIDEOS]:

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

    # Ana M3U dosyasini guncelle.
    with open(
        MASTER_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(final_lines) + "\n"
        )

    # JSON dosyasini guncelle.
    with open(
        RESULT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            items,
            f,
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
