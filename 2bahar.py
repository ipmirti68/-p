
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
import subprocess
from urllib.parse import urlparse
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - IKINCI BAHAR HLS KONTROL
# Yalnizca dogrudan ve dogrulanmis M3U8
# ==========================================

M3U_FILE = "ikinci_bahar.m3u"
JSON_FILE = "ikinci_bahar_kontrol.json"
LOGO = "https://cdn.neoldu.com.tr/other/14-250.jpg"

VIDEO_IDS = [
    "LfbW6DO7Zgs",
    "Hw3dsq2vQ4g",
    "lNcOqYLowb8",
    "vwP-w63klHE",
    "NxrDuIWSBzM",
    "n9TL3sx1-p4",
    "6XMFs_6eQgI",
    "Z-E_yJOAPTQ",
    "sLJCtfZz4xg",
    "5iK7smTuUXI",
    "bJ7VH99YqXo",
    "rG_kYsgFw2M",
    "KswYPc4PNxo",
    "qebJp8JQ7TE",
    "sGujswnthwg",
    "izdZC-nFgnE",
    "WIlLyFRwSkA",
    "I9Katr8kVac",
    "s5gqzOmyBG4",
    "kTYyr9nhBcs",
    "CavumG3Remg",
    "WDBA05Hlamo",
    "m3JhYNa2hzc",
    "D6JOH1XxfcY",
    "bWLUlX7sv2o",
    "7Yp3iU_xF6Y",
    "OzUw40lfsrw",
    "aUsiTeAFTnI",
    "NHvjVdH66s0",
    "FlUSzeQZ4QI",
    "jmZsUdUw3TI",
    "wgivjyDfK7c",
    "uMY775MnqDI",
    "6ERQHjDpMUY",
    "6ERQHjDpMUY",
]

def tekil_idler():
    sonuc = []
    gorulen = set()

    for video_id in VIDEO_IDS:
        if video_id not in gorulen:
            gorulen.add(video_id)
            sonuc.append(video_id)

    return sonuc


def hls_dogrula(url, headers=None):
    if not url:
        return False

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.path.lower().endswith(".m3u8"):
            return False

        yanit = requests.get(
            url,
            headers=headers or {},
            timeout=20,
            stream=True,
            allow_redirects=True
        )

        try:
            if yanit.status_code != 200:
                return False

            icerik = yanit.raw.read(4096)
            metin = icerik.decode(
                "utf-8",
                errors="ignore"
            ).lstrip("\ufeff \r\n\t")

            return metin.startswith("#EXTM3U")

        finally:
            yanit.close()

    except Exception as hata:
        print("[HLS KONTROL HATASI]", hata)
        return False


def youtube_hls_bul(video_id):
    adres = f"https://www.youtube.com/watch?v={video_id}"

    ayarlar = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extractor_retries": 2,
        "socket_timeout": 20,
    }

    try:
        with YoutubeDL(ayarlar) as ydl:
            bilgi = ydl.extract_info(
                adres,
                download=False
            )

        if not bilgi:
            return None

        genel_headers = bilgi.get("http_headers", {})
        formatlar = bilgi.get("formats", [])

        adaylar = []

        for fmt in formatlar:
            url = fmt.get("url", "")
            protokol = fmt.get("protocol", "")

            if (
                protokol in ("m3u8", "m3u8_native")
                or urlparse(url).path.lower().endswith(".m3u8")
            ):
                adaylar.append(fmt)

        for fmt in adaylar:
            url = fmt.get("url")

            headers = dict(genel_headers)
            headers.update(fmt.get("http_headers", {}))

            if hls_dogrula(url, headers):
                return {
                    "url": url,
                    "format_id": fmt.get("format_id"),
                    "height": fmt.get("height"),
                }

        return None

    except Exception as hata:
        print("[VIDEO HATASI]", video_id, str(hata)[:250])
        return None


def m3u_yaz(kayitlar):
    if not kayitlar:
        print("CALISAN HLS YOK. ESKI M3U KORUNDU.")
        return False

    gecici = M3U_FILE + ".tmp"

    with open(gecici, "w", encoding="utf-8") as dosya:
        dosya.write("#EXTM3U\n")

        for kayit in kayitlar:
            dosya.write(
                f'#EXTINF:-1 tvg-logo="{LOGO}" '
                f'group-title="İKİNCİ BAHAR",'
                f'İKİNCİ BAHAR {kayit["bolum"]}. BÖLÜM\n'
            )
            dosya.write(kayit["url"] + "\n")

    os.replace(gecici, M3U_FILE)
    return True


def main():
    print("=" * 45)
    print("MIRTI68 - IKINCI BAHAR HLS GUNCELLEYICI")
    print("TELEVIZO - DOĞRUDAN M3U8")
    print("=" * 45)

    kayitlar = []
    rapor = []

    idler = tekil_idler()

    print("Tekil video ID:", len(idler))
    print("Kontrol basliyor...")

    for bolum, video_id in enumerate(idler, 1):
        print(f"[{bolum}] Bolum kontrol ediliyor: {video_id}")

        sonuc = youtube_hls_bul(video_id)

        if sonuc:
            kayit = {
                "bolum": bolum,
                "video_id": video_id,
                "url": sonuc["url"],
                "durum": "HLS_CALISIYOR",
            }

            kayitlar.append(kayit)
            rapor.append(kayit)

            print("[BULUNDU] Dogrudan HLS")
        else:
            rapor.append({
                "bolum": bolum,
                "video_id": video_id,
                "durum": "HLS_BULUNAMADI",
            })

            print("[YOK] Dogrudan HLS bulunamadi")

    with open(JSON_FILE, "w", encoding="utf-8") as dosya:
        json.dump(
            rapor,
            dosya,
            ensure_ascii=False,
            indent=2
        )

    if m3u_yaz(kayitlar):
        print("M3U GUNCELLENDI:", M3U_FILE)

    print("Toplam video:", len(idler))
    print("Calisan HLS:", len(kayitlar))
    print("HLS bulunamayan:", len(idler) - len(kayitlar))
    print("Kontrol raporu:", JSON_FILE)


if __name__ == "__main__":
    main()
    
