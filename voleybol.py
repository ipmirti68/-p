
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIRTI68 - TVF VOLEYBOL MAC TAKIP SISTEMI

- TVF fiksturunu otomatik alir.
- Eski program, yeni program gelene kadar korunur.
- Program degisikligini SHA256 ile kontrol eder.
- JSON dosyalarini guvenli sekilde kaydeder.
- mirti68.m3u dosyasina dokunmaz.
"""

import os
import re
import json
import hashlib
import requests

from bs4 import BeautifulSoup

# =====================================
# AYARLAR
# =====================================

STATE_FILE = "voleybol_eski.json"
PROGRAM_FILE = "voleybol_program.json"

TVF_URL = "https://fikstur.tvf.org.tr/tvftvyayin"

YOUTUBE_CHANNEL = (
    "https://www.youtube.com/channel/"
    "UCTgQ8Bfq3AUuo1vWULdvRKw"
)

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
# PROGRAM HASH KONTROLU
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
# ESKI PROGRAM HAFIZASI
# =====================================

def load_state():

    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        print("Eski program hafizasi okunamadi:", e)
        return {}


# =====================================
# GUVENLI JSON KAYDI
# =====================================

def save_json(path, data):

    temp = str(path) + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp, path)


# =====================================
# TVF PROGRAMINI AL
# =====================================

def get_program():

    print("🏐 TVF programi indiriliyor...")

    response = session.get(
        TVF_URL,
        timeout=30
    )

    response.raise_for_status()

    response.encoding = "iso-8859-9"

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in soup.get_text("\n").splitlines()
        if line.strip()
    ]

    print("Okunan satir:", len(lines))

    matches = []

    current_date = None
    current_channel = None

    team_parts = []
    separator_found = False

    date_pattern = re.compile(
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b"
    )

    time_pattern = re.compile(
        r"^([01]?\d|2[0-3]):([0-5]\d)$"
    )

    for line in lines:

        lower = line.casefold()

        # Tarih kontrolu
        date_match = date_pattern.search(line)

        if date_match:

            current_date = (
                date_match.group(1)
                .replace("/", ".")
                .replace("-", ".")
            )

            current_channel = None
            team_parts = []
            separator_found = False

            continue

        # Yayin kanali kontrolu
        if "tvf voleybol tv" in lower:

            current_channel = "TVF Voleybol TV"

            team_parts = []
            separator_found = False

            continue

        if "trt spor yıldız" in lower:

            current_channel = "TRT Spor Yıldız"

            team_parts = []
            separator_found = False

            continue

        # Simdilik yalnizca TVF Voleybol TV
        if current_channel != "TVF Voleybol TV":
            continue

        if not current_date:
            continue

        # Takimlar arasindaki ayirac
        if line.strip() in ("-", "–", "—"):

            separator_found = True
            continue

        # Mac saati kontrolu
        time_match = time_pattern.fullmatch(line)

        if time_match:

            if separator_found and "|" in team_parts:

                separator_index = team_parts.index("|")

                home_team = " ".join(
                    team_parts[:separator_index]
                ).strip()

                away_team = " ".join(
                    team_parts[separator_index + 1:]
                ).strip()

                if home_team and away_team:

                    item = {
                        "date": current_date,
                        "time": line,
                        "name": home_team + " - " + away_team,
                        "home": home_team,
                        "away": away_team,
                        "channel": current_channel,
                        "youtube": YOUTUBE_CHANNEL
                    }

                    if item not in matches:
                        matches.append(item)

            team_parts = []
            separator_found = False

            continue

        # Takim isimlerini biriktir
        if len(line) < 2:
            continue

        if not separator_found:

            team_parts.append(line)

        else:

            if "|" not in team_parts:
                team_parts.append("|")

            team_parts.append(line)

    print("Bulunan TVF maci:", len(matches))

    for item in matches:

        print(
            "🏐",
            item["date"],
            item["time"],
            item["name"]
        )

    return matches


# =====================================
# ANA GUNCELLEME
# =====================================

def main():

    print("=" * 45)
    print(" MIRTI68 - VOLEYBOL GUNCELLEYICI")
    print("=" * 45)

    # TVF programini indir
    try:

        matches = get_program()

    except Exception as e:

        print("TVF programi alinamadi:", e)
        print("Eski program korunuyor.")
        return

    # Bos programi kaydetme
    if not matches:

        print("Program bos geldi.")
        print("Eski program korunuyor.")
        return

    # Eski hafizayi oku
    old_state = load_state()

    old_hash = old_state.get("hash")

    # Yeni program hash
    new_hash = program_hash(matches)

    # Program degisikligi
    if old_hash == new_hash:

        print("Program degismemis.")

    else:

        print("Yeni TVF programi bulundu!")

        new_state = {
            "hash": new_hash,
            "matches": matches
        }

        save_json(
            STATE_FILE,
            new_state
        )

        print("Yeni program hafizaya kaydedildi.")

    # Guncel program JSON dosyasi
    save_json(
        PROGRAM_FILE,
        matches
    )

    print("=" * 45)
    print("TVF mac sayisi:", len(matches))
    print("Program dosyasi:", PROGRAM_FILE)
    print("Hafiza dosyasi:", STATE_FILE)
    print("Ana M3U: DEGISTIRILMEDI")
    print("Diger IPTV gruplari: KORUNDU")
    print("=" * 45)


# =====================================
# BASLAT
# =====================================

if __name__ == "__main__":
    main()
