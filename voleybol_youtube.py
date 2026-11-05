# voleybol_youtube.py - TEST MODU

GROUP_LIVE = "🏐 VOLEYBOL HLS"
GROUP_REPLAY = "🏐 SULTANLAR LİGİ TEKRAR"
OLD_GROUPS = ("🏐 VOLEYBOL CANLI", "🏐 KUZEYBORU", "🏐 VOLEYBOL HLS", "🏐 SULTANLAR LİGİ TEKRAR")

# TEST İÇİN: Son hafta maçlarını da al
INCLUDE_PAST = True 
PAST_LIMIT = 15 # Son 15 bitmiş maçı tara

def scan_video(ydl, video_id, entry=None):
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        info = ydl.extract_info(youtube_url, download=False) or {}
    except Exception as e:
        print(f"Hata: {video_id} - {e}")
        return None

    title = clean_title(info.get("title") or (entry or {}).get("title") or video_id)
    
    # Sultanlar Ligi filtresi
    if "sultanlar" not in normalize_text(title) and "kuzeyboru" not in normalize_text(title):
        # İstersen bu filtreyi kaldır, tüm ligler gelsin
        pass

    state = get_state(info, entry)
    hls_url = get_hls_url(info)

    # ÖNEMLİ: Artık TAMAMLANDI'yı silmiyoruz
    if not hls_url:
        print(f"⏳ HLS yok: {state} - {title}")
        # YAKLAŞAN'da zaten HLS olmaz, normal
        if state == "YAKLAŞAN":
            return {
                "video_id": video_id, "name": title, "title": title,
                "youtube_url": youtube_url, "stream_url": "",
                "thumbnail": get_thumbnail(info, entry, video_id),
                "match_time": takvimden_tarih_bul(title, TAKVIM) or get_match_time(info, entry),
                "state": state, "hls_status": "YAKLAŞAN",
                "priority": team_priority(title), "is_replay": False
            }
        return None

    print(f"✅ HLS bulundu: {state} - {title}")

    return {
        "video_id": video_id,
        "name": title,
        "title": title,
        "youtube_url": youtube_url,
        "stream_url": hls_url, # Bu artık VOD HLS de olabilir
        "thumbnail": get_thumbnail(info, entry, video_id),
        "match_time": takvimden_tarih_bul(title, TAKVIM) or get_match_time(info, entry),
        "state": state,
        "hls_status": "HLS_BULUNDU",
        "priority": team_priority(title),
        "is_replay": state == "TAMAMLANDI",
        "channel_id": CHANNEL_ID,
    }

def save_files(items):
    # ... JSON aynı ...
    
    live_items = [i for i in items if i.get("stream_url") and not i.get("is_replay")]
    replay_items = [i for i in items if i.get("stream_url") and i.get("is_replay")][:PAST_LIMIT]

    # Eski grupları temizle
    base_lines = remove_old_groups(old_lines)

    # 1. CANLI'ları ekle
    for item in live_items:
        new_lines.append(f'#EXTINF:-1 tvg-logo="{item["thumbnail"]}" group-title="{GROUP_LIVE}",🏐 {item["name"]} | {item["match_time"]} | CANLI\n')
        new_lines.append(item["stream_url"] + "\n")

    # 2. SON HAFTA TEKRAR'ları ekle - TEST İÇİN
    for item in replay_items:
        # Kuzeyboru ve Sultanlar Ligi öncelikli
        if "kuzeyboru" in normalize_text(item["name"]) or "sultanlar" in normalize_text(item["name"]):
            new_lines.append(f'#EXTINF:-1 tvg-logo="{item["thumbnail"]}" group-title="{GROUP_REPLAY}",{item["name"]} | {item["match_time"]} | TEKRAR\n')
            new_lines.append(item["stream_url"] + "\n")

    atomic_write(MASTER_FILE, "".join(new_lines))
    print(f"✅ M3U: {len(live_items)} canlı + {len(replay_items)} tekrar eklendi")
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
