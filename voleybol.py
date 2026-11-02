
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF VOLEYBOL MAC TAKIP SISTEMI
Eski program yeni program gelene kadar korunur.
Yalnizca kendi kayitlarini yonetir.
"""

import os
import re
import json
import hashlib
import requests

from pathlib import Path
from bs4 import BeautifulSoup

# =====================================
# AYARLAR
# =====================================

MASTER_FILE = "mirti68.m3u"
STATE_FILE = "voleybol_eski.json"
PROGRAM_FILE = "voleybol_program.json"

TVF_URL = "https://fikstur.tvf.org.tr/tvftvyayin"

YOUTUBE_CHANNEL = (
    "https://www.youtube.com/channel/"
    "UCTgQ8Bfq3AUuo1vWULdvRKw"
)

GROUP = "🏐 VOLEYBOL CANLI"
MARKER = "# MIRTI68_VOLEYBOL_AUTO"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Mobile Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


# =====================================
# TVF PROGRAMINI AL
# =====================================

def get_program():

    print("🏐 TVF programi indiriliyor...")

    response = session.get(TVF_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    lines = [
        re.sub(r"\s+", " ", x).strip()
        for x in soup.get_text("\n").splitlines()
    ]

    matches = []
    current_date = None
    current_channel = None

    date_pattern = re.compile(
        r"(\d{2}\.\d{2}\.\d{4})"
    )

    for line in lines:

        if not line:
            continue

        date_match = date_pattern.search(line)

        if date_match and "|" in line:
            current_date = date_match.group(1)

            if "TVF Voleybol TV" in line:
                current_channel = "TVF Voleybol TV"

            elif "TRT Spor Yıldız" in line:
                current_channel = "TRT Spor Yıldız"

            else:
                current_channel = None

            continue

        if current_channel != "TVF Voleybol TV":
            continue

        match = re.match(
            r"(.+?)\s+(\d{1,2}:\d{2})$",
            line
        )

        if not match or not current_date:
            continue

        team_names = match.group(1).strip()
        match_time = match.group(2)

        matches.append({
            "date": current_date,
            "time": match_time,
            "name": team_names,
            "channel": current_channel,
            "youtube": YOUTUBE_CHANNEL
        })

    print(f"✅ Bulunan TVF maci: {len(matches)}")

    return matches


# =====================================
# PROGRAM KIMLIGI
# =====================================

def program_hash(matches):

    content = json.dumps(
        matches,
        ensure_ascii=False,
        sort_keys=True
    )

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# =====================================
# ESKI PROGRAMI KORU
# =====================================

def load_state():

    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}


def save_json(path, data):

    temp = str(path) + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp, path)


# =====================================
# SADECE KENDI M3U KAYITLARINI SIL
# =====================================

def remove_own_records(lines):

    result = []
    i = 0

    while i < len(lines):

        if lines[i].strip() == MARKER:

            i += 1

            if i < len(lines) and lines[i].strip().startswith("#EXTINF:"):
                i += 1

                while i < len(lines):
                    current = lines[i].strip()

                    if current and not current.startswith("#"):
                        i += 1
                        break

                    if current.startswith("#EXTINF:"):
                        break

                    i += 1

            continue

        result.append(lines[i])
        i += 1

    return result


# =====================================
# PROGRAMI GUNCELLE
# =====================================

def main():

    print("=" * 45)
    print(" MIRTI68 - VOLEYBOL GUNCELLEYICI")
    print("=" * 45)

    try:
        matches = get_program()

    except Exception as e:
        print("❌ TVF programi alinamadi:", e)
        print("Eski program korunuyor.")
        return

    if not matches:
        print("⚠ Program bos geldi.")
        print("Eski program korunuyor.")
        return

    old_state = load_state()

    new_hash = program_hash(matches)
    old_hash = old_state.get("hash")

    if old_hash == new_hash:
        print("ℹ Program degismemis.")
        print("Eski program korunuyor.")

    else:
        print("🆕 Yeni TVF programi bulundu.")

        save_json(STATE_FILE, {
            "hash": new_hash,
            "matches": matches
        })

        print("✅ Yeni program kaydedildi.")

    # Program dosyasini kaydet
    save_json(PROGRAM_FILE, matches)

    # Ana M3U dosyasini oku
    if not os.path.exists(MASTER_FILE):
        print("❌ mirti68.m3u bulunamadi!")
        return

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:
        lines = f.readlines()

    # Yalnizca kendi eski kayitlarini kaldir
    output = remove_own_records(lines)

    if not any(x.strip() == "#EXTM3U" for x in output):
        output.insert(0, "#EXTM3U\n")

    # Bu ilk aşamada maçları program JSON dosyasında tutuyoruz.
    # Henüz doğrulanmış oynatılabilir YouTube URL'si bulunmadığı
    # için sahte M3U8 bağlantısı eklemiyoruz.

    temp = MASTER_FILE + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        f.writelines(output)

    os.replace(temp, MASTER_FILE)

    print("=" * 45)
    print("TVF mac sayisi:", len(matches))
    print("Program:", PROGRAM_FILE)
    print("Hafiza:", STATE_FILE)
    print("Ana liste:", MASTER_FILE)
    print("Diger gruplar: KORUNDU")
    print("=" * 45)


if __name__ == "__main__":
    main()
