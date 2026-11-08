#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - VOLEYBOL YOUTUBE BOT
# ==========================================

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"

TVF_CHANNEL = (
    "https://www.youtube.com/channel/"
    "UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
)

KUZEYBORU_CHANNEL = os.getenv("KUZEYBORU_CHANNEL_URL", "").strip()

GROUP_LIVE = "🏐 VOLEYBOL HLS"
GROUP_KUZEYBORU = "🏐 KUZEYBORU CANLI"
GROUP_REPLAY = "🏐 SULTANLAR LİGİ TEKRAR"

MAX_VIDEOS = 60
MAX_LIVE = 5
MAX_KUZEYBORU = 10
MAX_REPLAY = 60

GROUPS = (
    GROUP_LIVE,
    GROUP_KUZEYBORU,
    GROUP_REPLAY,
)

LIMITS = {
    GROUP_LIVE: MAX_LIVE,
    GROUP_KUZEYBORU: MAX_KUZEYBORU,
    GROUP_REPLAY: MAX_REPLAY,
}

KEYWORDS = (
    "voleybol",
    "sultanlar ligi",
    "kuzeyboru",
    "tvf",
    "eczacıbaşı",
    "eczacibasi",
    "vakıfbank",
    "vakifbank",
    "fenerbahçe",
    "fenerbahce",
    "galatasaray",
    "nilüfer",
    "nilufer",
    "efeler ligi",
    "kadınlar ligi",
    "kadinlar ligi",
    "voleybol tv",
)

OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": False,
    "extract_flat": "in_playlist",
    "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "socket_timeout": 25,
    "extractor_retries": 2,
    "retries": 2,
    "sleep_interval_requests": 1,
}

DETAIL = {
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": False,
    "skip_download": True,
    "socket_timeout": 25,
    "extractor_retries": 2,
    "retries": 2,
}


def get_id(video):
    """Playlist girdisinden 11 karakterli YouTube video ID'sini al."""
    vid = str(video.get("id") or "")
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return vid

    url = str(video.get("url") or "")
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else ""


def get_hls(info):
    """Video bilgisinde bulunan HLS/m3u8 adresini bul."""
    if not info:
        return ""

    for key in ("hls_manifest_url", "manifest_url"):
        value = info.get(key)
        if value and "m3u8" in str(value).lower():
            return str(value)

    formats = info.get("formats") or []
    for fmt in formats:
        url = str(fmt.get("url") or "")
        protocol = str(fmt.get("protocol") or "").lower()
        if url and (
            "m3u8" in url.lower()
            or "m3u8" in protocol
            or "hls" in protocol
        ):
            return url

    for fmt in info.get("requested_formats") or []:
        url = str(fmt.get("url") or "")
        protocol = str(fmt.get("protocol") or "").lower()
        if url and ("m3u8" in url.lower() or "hls" in protocol):
            return url

    return ""


def is_live(info):
    return (
        info.get("is_live") is True
        or info.get("live_status") == "is_live"
    )


def is_upcoming(info):
    if info.get("live_status") == "is_upcoming":
        return True

    release = info.get("release_timestamp")
    try:
        if release and float(release) > time.time():
            return True
    except (TypeError, ValueError):
        pass

    return False


def classify(info):
    title = str(info.get("title") or "")
    description = str(info.get("description") or "")
    text_value = (title + " " + description).casefold()

    if not any(word.casefold() in text_value for word in KEYWORDS):
        return ""

    if is_upcoming(info):
        return ""

    if is_live(info):
        if "kuzeyboru" in text_value:
            return GROUP_KUZEYBORU
        return GROUP_LIVE

    return GROUP_REPLAY


def scan():
    print("=" * 45)
    print("MIRTI68 VOLEYBOL YOUTUBE BOT")
    print("=" * 45)

    sources = [TVF_CHANNEL]
    if KUZEYBORU_CHANNEL:
        sources.append(KUZEYBORU_CHANNEL)

    videos = []
    seen = set()
    errors = []

    for source in sources:
        print("\nKaynak:", source)
        try:
            with YoutubeDL(OPTIONS) as ydl:
                playlist = ydl.extract_info(source, download=False)

            if not playlist:
                raise RuntimeError("Kanal listesi alınamadı")

            for entry in playlist.get("entries") or []:
                if not entry:
                    continue

                vid = get_id(entry)
                if not vid or vid in seen:
                    continue

                seen.add(vid)
                videos.append((vid, entry))

        except Exception as error:
            print("KAYNAK HATASI:", error)
            errors.append(str(error))

    print("\nVideo sayısı:", len(videos))
    if not videos:
        print("Video bulunamadı.")
        return None

    results = []
    detail_errors = []

    with YoutubeDL(DETAIL) as ydl:
        for index, (vid, entry) in enumerate(videos, 1):
            print(f"\n[{index}/{len(videos)}] Video kontrol: {vid}")
            url = "https://www.youtube.com/watch?v=" + vid

            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise RuntimeError("Video bilgisi yok")
            except Exception as error:
                print("VIDEO HATASI:", error)
                detail_errors.append(str(error))
                time.sleep(1)
                continue

            if is_upcoming(info):
                print("Henüz başlamadı.")
                time.sleep(1)
                continue

            group = classify(info)
            if not group:
                print("Voleybol videosu değil.")
                time.sleep(1)
                continue

            hls = get_hls(info)
            if not hls:
                print("HLS bağlantısı bulunamadı.")
                time.sleep(1)
                continue

            title = str(info.get("title") or entry.get("title") or vid)
            title = re.sub(r'[\r\n"]+', " ", title).strip()

            results.append({
                "id": vid,
                "name": title,
                "stream_url": hls,
                "group": group,
                "is_live": is_live(info),
                "live_status": info.get("live_status"),
            })

            print("YAYIN:", title)
            print("GRUP:", group)
            time.sleep(1)

    # Eksik tarama ile eski grupları silme.
    if errors or detail_errors:
        print("\nTARAMA TAMAMLANAMADI.")
        print("Hata sayısı:", len(errors) + len(detail_errors))
        print("Eski M3U korunacak.")
        return None

    print("\nGeçerli HLS:", len(results))
    return results


def read_blocks(lines):
    """M3U dosyasını başlık ve EXTINF bloklarına ayır."""
    preamble = []
    blocks = []
    current = None

    for line in lines:
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

    return preamble, blocks


def get_group(block):
    if not block:
        return ""

    match = re.search(r'group-title="([^"]*)"', block[0])
    return match.group(1) if match else ""


def save_json(data):
    temp = RESULT_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(temp, RESULT_FILE)


def save(items):
    if items is None:
        print("Tarama başarısız. M3U değişmedi.")
        return

    if not items:
        print("Yeni HLS bulunamadı. Eski kayıtlar korundu.")
        return

    groups = {group: [] for group in GROUPS}
    for item in items:
        group = item.get("group")
        if group in groups and item.get("stream_url"):
            groups[group].append(item)

    # Yalnızca yeni HLS bulunan gruplar yenilenir.
    replace_groups = {
        group for group, records in groups.items() if records
    }

    if not replace_groups:
        print("Güncellenecek grup yok. Eski kayıtlar korundu.")
        return

    if os.path.isfile(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8-sig") as file:
            old_lines = file.read().splitlines()
    else:
        old_lines = ["#EXTM3U"]

    preamble, blocks = read_blocks(old_lines)
    final_lines = list(preamble)

    if not any(line.strip() == "#EXTM3U" for line in final_lines):
        final_lines.insert(0, "#EXTM3U")

    # Güncellenmeyen tüm IPTV gruplarını olduğu gibi koru.
    for block in blocks:
        group = get_group(block)
        if group in replace_groups:
            print("Eski grup yenileniyor:", group)
            continue
        final_lines.extend(block)

    # Yeni voleybol kayıtlarını ekle.
    for group, records in groups.items():
        if group not in replace_groups:
            continue

        added = set()
        for item in records[:LIMITS[group]]:
            vid = item["id"]
            if vid in added:
                continue
            added.add(vid)

            title = re.sub(r'[\r\n"]+', " ", item["name"]).strip()
            final_lines.append(
                f'#EXTINF:-1 group-title="{group}",{title}'
            )
            final_lines.append(item["stream_url"])
            print("M3U EKLENDİ:", title)

    # M3U önce geçici dosyaya yazılır, sonra atomik olarak değiştirilir.
    temp = MASTER_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as file:
        file.write("\n".join(final_lines) + "\n")
    os.replace(temp, MASTER_FILE)
    save_json(items)

    print("\n" + "=" * 45)
    print("MIRTI68 VOLEYBOL GÜNCELLENDİ")
    print("=" * 45)

    for group, records in groups.items():
        if group in replace_groups:
            print(group + ":", min(len(records), LIMITS[group]))
        else:
            print(group + ": Eski kayıtlar korundu")

    print("Ana liste:", MASTER_FILE)
    print("JSON:", RESULT_FILE)
    print("Diğer IPTV grupları: KORUNDU")
    print("=" * 45)


def main():
    items = scan()
    save(items)


if __name__ == "__main__":
    main()
ON:", RESULT_FILE)
    print("Diğer IPTV grupları: KORUNDU")
    print("=" * 45)


def main():
    items = scan()
    save(items)


if __name__ == "__main__":
    main()
.splitlines()

    else:

        old_lines = ["#EXTM3U"]

    preamble, blocks = read_blocks(old_lines)

    final_lines = list(preamble)

    if not any(
        line.strip() == "#EXTM3U"
        for line in final_lines
    ):

        final_lines.insert(0, "#EXTM3U")

    # DİĞER BÜTÜN KANALLARI KORU

    for block in blocks:

        group = get_group(block)

        if group in replace_groups:

            print("Eski grup yenileniyor:", group)
            continue

        final_lines.extend(block)

    # YENİ HLS YAYINLARINI EKLE

    for group, records in groups.items():

        if group not in replace_groups:
            continue

        added = set()

        for item in records[:LIMITS[group]]:

            vid = item["id"]

            if vid in added:
                continue

            added.add(vid)

            title = re.sub(
                r'[\r\n"]+',
                " ",
                item["name"]
            ).strip()

            final_lines.append(
                f'#EXTINF:-1 group-title="{group}",{title}'
            )

            final_lines.append(
                item["stream_url"]
            )

            print("M3U EKLENDİ:", title)

    # ======================================
    # ATOMİK M3U KAYDI
    # ======================================

    temp = MASTER_FILE + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(final_lines) + "\n"
        )

    os.replace(temp, MASTER_FILE)

    # JSON KAYDI

    save_json(items)

    # ======================================
    # SONUÇ
    # ======================================

    print("\n" + "=" * 45)
    print("MIRTI68 VOLEYBOL GÜNCELLENDİ")
    print("=" * 45)

    for group, records in groups.items():

        if group in replace_groups:

            count = min(
                len(records),
                LIMITS[group]
            )

            print(group + ":", count)

        else:

            print(
                group + ": Eski kayıtlar korundu"
            )

    print("Ana liste:", MASTER_FILE)
    print("JSON:", RESULT_FILE)
    print("Diğer IPTV grupları: KORUNDU")
    print("=" * 45)


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    items = scan()

    save(items)


# ==========================================
# PROGRAMI BAŞLAT
# ==========================================

if __name__ == "__main__":

    main()
 for item in records[:LIMITS[group]]:
            vid = item["id"]

            if vid in added:
                continue

            added.add(vid)

            title = re.sub(
                r'[\r\n"]+',
                " ",
                item["name"]
            ).strip()

            final_lines.append(
                f'#EXTINF:-1 group-title="{group}",{title}'
            )

            final_lines.append(item["stream_url"])

            print("M3U EKLENDİ:", title)

    # Önce geçici dosyaya yaz, sonra ana dosyaya geçir.
    temp = MASTER_FILE + ".tmp"

    with open(temp, "w", encoding="utf-8") as file:
        file.write("\n".join(final_lines) + "\n")

    os.replace(temp, MASTER_FILE)

    save_json(items)

    print("\n" + "=" * 45)
    print("MIRTI68 VOLEYBOL GÜNCELLENDİ")
    print("=" * 45)

    for group, records in groups.items():
        if group in replace_groups:
            print(
                group + ":",
                min(len(records), LIMITS[group])
            )
        else:
            print(group + ": Eski kayıtlar korundu")

    print("Ana liste:", MASTER_FILE)
    print("JSON:", RESULT_FILE)
    print("Diğer kanallar: KORUNDU")
    print("=" * 45)


# ==========================================
# ANA PROGRAM
# ==========================================

def main():
    items = scan()
    save(items)


if __name__ == "__main__":
    main()
#Sadece yeni HLS bulunan grupları değiştir.
    replace_groups = {
        group
        for group, records in groups.items()
        if records
    }

    if not replace_groups:

        print("Güncellenecek grup yok.")
        print("Eski kayıtlar korundu.")
        return

    # Eski ana M3U dosyasını oku.
    if os.path.isfile(MASTER_FILE):

        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as file:

            old_lines = file.read().splitlines()

    else:

        old_lines = ["#EXTM3U"]

    preamble, blocks = read_blocks(old_lines)

    final_lines = list(preamble)

    if not any(
        line.strip() == "#EXTM3U"
        for line in final_lines
    ):

        final_lines.insert(0, "#EXTM3U")

    # Diğer kanalları ve güncellenmeyen
    # voleybol gruplarını koru.
    for block in blocks:

        group = get_group(block)

        if group in replace_groups:

            print("Grup yenileniyor:", group)
            continue

        final_lines.extend(block)

    # Yeni yayınları ekle.
    for group, records in groups.items():

        if group not in replace_groups:
            continue

        added = set()

        for item in records[:limits[group]]:

            vid = item["id"]

            if vid in added:
                continue

            added.add(vid)

            title = re.sub(
                r'[\r\n"]+',
                " ",
                item["name"]
            ).strip()

            final_lines.append(
                f'#EXTINF:-1 group-title="{group}",'
                f'{title}'
            )

            final_lines.append(
                item["stream_url"]
            )

            print("M3U EKLENDİ:", title)

    # Atomik M3U kaydı.
    temp = MASTER_FILE + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(final_lines) + "\n"
        )

    os.replace(temp, MASTER_FILE)

    # JSON kaydı.
    save_json(RESULT_FILE, items)

    print("\n" + "=" * 45)
    print("MIRTI68 VOLEYBOL GÜNCELLENDİ")
    print("=" * 45)

    for group, records in groups.items():

        if group in replace_groups:

            count = min(
                len(records),
                limits[group]
            )

            print(group + ":", count)

        else:

            print(group + ": Eski kayıtlar korundu")

    print("Ana liste:", MASTER_FILE)
    print("JSON:", RESULT_FILE)
    print("Diğer IPTV grupları: KORUNDU")
    print("=" * 45)


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    items = scan()
    save(items)


if __name__ == "__main__":
    main()
  ) as file:

            old_lines = file.read().splitlines()

    else:

        old_lines = ["#EXTM3U"]

    preamble, blocks = read_blocks(old_lines)

    final_lines = list(preamble)

    if not any(
        line.strip() == "#EXTM3U"
        for line in final_lines
    ):

        final_lines.insert(0, "#EXTM3U")

    # Diğer kanalları ve güncellenmeyen
    # voleybol gruplarını koru.
    for block in blocks:

        group = get_group(block)

        if group in replace_groups:
            print("Grup yenileniyor:", group)
            continue

        final_lines.extend(block)

    # Yeni yayınları ekle
    for group, records in groups.items():

        if group not in replace_groups:
            continue

        added = set()

        for item in records[:limits[group]]:

            vid = item["id"]

            if vid in added:
                continue

            added.add(vid)

            title = re.sub(
                r'["\r\n]+',
                " ",
                item["name"]
            ).strip()

            final_lines.append(
                f'#EXTINF:-1 group-title="{group}",'
                f'{title}'
            )

            final_lines.append(
                item["stream_url"]
            )

            print("M3U EKLENDİ:", title)

    # Atomik M3U kaydı
    temp = MASTER_FILE + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(final_lines) + "\n"
        )

    os.replace(temp, MASTER_FILE)

    save_json(RESULT_FILE, items)

    print("\n" + "=" * 45)
    print("MIRTI68 VOLEYBOL GÜNCELLENDİ")
    print("=" * 45)

    for group, records in groups.items():

        print(
            group + ":",
            min(len(records), limits[group])
            if group in replace_groups else
            "Eski kayıtlar korundu"
        )

    print("Ana liste:", MASTER_FILE)
    print("JSON:", RESULT_FILE)
    print("Diğer IPTV grupları: KORUNDU")
    print("=" * 45)


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    items = scan()
    save(items)


if __name__ == "__main__":
    main()
seen.add(vid)

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
