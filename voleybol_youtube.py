
import os
import re
import json
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - KUZEYBORU / SULTANLAR LIGI
# CANLI + TEKRAR YAYIN TARAMA
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
# HLS LINK BUL
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
# YOUTUBE KANAL TARA
# ==========================================

def scan():

    print("========================================")
    print("MIRTI68 - VOLEYBOL TARAMA")
    print("CANLI + SULTANLAR LIGI TEKRAR")
    print("========================================")

    vids = []

    try:

        with YoutubeDL(OPTIONS) as ydl:

            pl = ydl.extract_info(
                CHANNEL_URL,
                download=False
            )

            if not pl:
                print("Kanal bilgisi alinamadi.")
                return []

            for e in (pl.get("entries") or []):

                if not e:
                    continue

                vid = get_id(e)

                if vid:
                    vids.append((vid, e))

    except Exception as e:

        print(f"Kanal hatasi: {e}")
        return []

    print(f"Bulunan video: {len(vids)}")

    results = []
    seen = set()

    with YoutubeDL(DETAIL) as ydl:

        for vid, entry in vids:

            url = (
                f"https://www.youtube.com/watch?v={vid}"
            )

            try:

                info = ydl.extract_info(
                    url,
                    download=False
                ) or {}

            except Exception as e:

                print(f"Video atlandi: {vid} - {e}")
                continue

            title = (
                info.get("title")
                or entry.get("title")
                or vid
            )

            low = title.lower()

            if (
                "sultanlar" not in low
                and "kuzeyboru" not in low
            ):
                continue

            status = (
                info.get("live_status")
                or entry.get("live_status")
                or ""
            )

            if status == "is_upcoming":
                continue

            hls = get_hls(info)

            if not hls:
                continue

            if vid in seen:
                continue

            seen.add(vid)

            is_replay = (
                status == "was_live"
                or info.get("live_status") == "was_live"
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

    print("----------------------------------------")
    print(f"Tarama sonucu: {len(results)}")
    print("----------------------------------------")

    return results


# ==========================================
# ESKI M3U GRUPLARINI AYIKLA
# DIGER KANALLARA DOKUNMA
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

            print(f"Eski grup kaldirildi: {group}")
            continue

        keep_blocks.append(block)

    return preamble, keep_blocks


# ==========================================
# YENI YAYINLARI KAYDET
# ==========================================

def save(items):

    live = [
        i for i in items
        if not i.get("is_replay")
    ]

    replay = [
        i for i in items
        if i.get("is_replay")
    ]

    print("========================================")
    print(f"Canli: {len(live)}")
    print(f"Tekrar: {len(replay)}")
    print("========================================")

    # Hic yayin bulunamazsa eski listeyi koru.
    if not items:

        print("Yeni yayin bulunamadi.")
        print("Mevcut M3U korunuyor.")
        return

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

    # Eski voleybol gruplarini kaldir.
    preamble, keep_blocks = remove_old_groups(
        old_lines
    )

    # Yeni M3U icerigi.
    final_lines = []

    final_lines.extend(preamble)

    if not any(
        line.strip() == "#EXTM3U"
        for line in final_lines
    ):

        final_lines.insert(0, "#EXTM3U")

    # Eski diger kanallari koru.
    for block in keep_blocks:

        final_lines.extend(block)

    # Yeni canli yayinlar.
    live_seen = set()

    for it in live[:MAX_LIVE]:

        stream = it["stream_url"]

        if stream in live_seen:
            continue

        live_seen.add(stream)

        final_lines.append(
            f'#EXTINF:-1 group-title="{GROUP_LIVE}",'
            f'{it["name"]} | CANLI'
        )

        final_lines.append(stream)

    # Yeni tekrar yayinlari.
    replay_seen = set()

    for it in replay[:MAX_VIDEOS]:

        stream = it["stream_url"]

        if stream in replay_seen:
            continue

        replay_seen.add(stream)

        final_lines.append(
            f'#EXTINF:-1 group-title="{GROUP_REPLAY}",'
            f'{it["name"]} | TEKRAR'
        )

        final_lines.append(stream)

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

    print("")
    print("========================================")
    print("MIRTI68 VOLEYBOL GUNCELLENDI")
    print("========================================")
    print(f"Canli yayin: {len(live_seen)}")
    print(f"Tekrar yayin: {len(replay_seen)}")
    print(f"Ana liste: {MASTER_FILE}")
    print(f"JSON: {RESULT_FILE}")
    print("Eski diger kanallar: KORUNDU")
    print("Duplicate: TEMIZLENDI")
    print("Yedek dosya: YOK")
    print("========================================")


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    items = scan()

    save(items)


if __name__ == "__main__":

    main()
