import json
import os
from m3u_manager import update_group

# =========================================
# AYARLAR
# =========================================

OUTPUT_FILENAME = "mirti68.m3u"
GROUP = "🖥beINSPORTS"
LOGO = "https://i.imgur.com/OqdfQmw.png"
SOURCE_FILE = "mahsun_streams.json"


# =========================================
# YETKİLİ YAYINLARI OKU
# =========================================

def get_channels():

    if not os.path.exists(SOURCE_FILE):
        print("Yayın dosyası bulunamadı:", SOURCE_FILE)
        return []

    try:
        with open(SOURCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (OSError, json.JSONDecodeError) as e:
        print("Dosya okuma hatası:", e)
        return []


# =========================================
# M3U KAYITLARINI HAZIRLA
# =========================================

def create_entries(channels):

    entries = []
    seen = set()

    for channel in channels:

        name = str(channel.get("name", "")).strip()
        url = str(channel.get("url", "")).strip()
        referrer = str(channel.get("referrer", "")).strip()

        if not name or not url:
            continue

        if not url.startswith(("https://", "http://")):
            continue

        key = name.casefold()

        if key in seen:
            print("[TEKRAR ATLANDI]", name)
            continue

        seen.add(key)

        entry = (
            f'#EXTINF:-1 tvg-name="{name}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GROUP}",{name}\n'
        )

        if referrer:
            entry += f"#EXTVLCOPT:http-referrer={referrer}\n"

        entry += url

        entries.append(entry)

        print("[EKLENDİ]", name)

    return entries


# =========================================
# ANA İŞLEM
# =========================================

def main():

    print("====================================")
    print("     MIRTI68 beINSPORTS GÜNCELLEME")
    print("====================================")

    channels = get_channels()

    if not channels:
        print("Yeni yayın bulunamadı.")
        print("Mevcut liste korunuyor.")
        return

    entries = create_entries(channels)

    if not entries:
        print("Geçerli yayın bulunamadı.")
        print("Mevcut liste korunuyor.")
        return

    update_group(
        GROUP,
        entries,
        OUTPUT_FILENAME
    )

    print("------------------------------------")
    print("GÜNCELLEME TAMAMLANDI")
    print("Kanal sayısı:", len(entries))
    print("Kategori:", GROUP)
    print("Logo:", LOGO)
    print("Dosya:", OUTPUT_FILENAME)
    print("====================================")


if __name__ == "__main__":
    main()
