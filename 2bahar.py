
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
from yt_dlp import YoutubeDL

# ==================================================
# MIRTI68 - İKİNCİ BAHAR
# TELEVIZO UYUMLU HLS M3U8
# ==================================================

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
    "6ERQHjDpMUY"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}


# ==================================================
# HLS ADRESİ DOĞRULAMA
# ==================================================

def hls_dogrula(url, headers=None):

    if not url:
        return False

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.path.lower().endswith(".m3u8"):
            return False

        request_headers = HEADERS.copy()

        if headers:
            request_headers.update(headers)

        response = requests.get(
            url,
            headers=request_headers,
            timeout=20,
            stream=True,
            allow_redirects=True
        )

        if response.status_code != 200:
            response.close()
            return False

        ilk_veri = next(
            response.iter_content(2048),
            b""
        )

        response.close()

        return b"#EXTM3U" in ilk_veri

    except Exception:
        return False


# ==================================================
# YOUTUBE HLS BULUCU
# ==================================================

def youtube_hls_bul(video_id):

    video_url = (
        "https://www.youtube.com/watch?v=" + video_id
    )

    ayarlar = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 25,
        "retries": 2,
        "extractor_retries": 2,
        "ignoreerrors": False,
        "format": "best",
    }

    try:

        with YoutubeDL(ayarlar) as ydl:

            bilgi = ydl.extract_info(
                video_url,
                download=False
            )

        if not bilgi:

            return {
                "error": "YouTube video bilgisi döndürmedi."
            }

        formats = bilgi.get("formats", [])
        adaylar = []

        for fmt in formats:

            adres = fmt.get("url", "")
            protocol = fmt.get("protocol", "")

            if not adres:
                continue

            if (
                protocol in ("m3u8", "m3u8_native")
                or urlparse(adres).path.lower().endswith(".m3u8")
            ):

                adaylar.append({
                    "url": adres,
                    "height": fmt.get("height") or 0,
                    "format_id": fmt.get("format_id"),
                    "headers": fmt.get("http_headers") or {}
                })

        adaylar.sort(
            key=lambda x: x["height"],
            reverse=True
        )

        for aday in adaylar:

            if hls_dogrula(
                aday["url"],
                aday["headers"]
            ):

                return {
                    "url": aday["url"],
                    "height": aday["height"],
                    "format_id": aday["format_id"],
                    "title": bilgi.get("title", "")
                }

        return {
            "error": "Doğrulanmış HLS M3U8 bulunamadı"
        }

        except Exception as hata:

        print(
            "GERÇEK YOUTUBE HATASI:",
            repr(hata)
        )

        return {
            "error": str(hata)[:1000]
        }

# ==================================================
# M3U OLUŞTUR
# ==================================================

def m3u_yaz(kayitlar):

    if not kayitlar:
        print("HLS bulunamadı. Eski M3U korunuyor.")
        return False

    gecici = M3U_FILE + ".tmp"

    try:

        with open(
            gecici,
            "w",
            encoding="utf-8"
        ) as dosya:

            dosya.write("#EXTM3U\n")

            for kayit in kayitlar:

                bolum = kayit["bolum"]
                adres = kayit["url"]

                dosya.write(
                    '#EXTINF:-1 '
                    'tvg-logo="' + LOGO + '" '
                    'group-title="🎬 İKİNCİ BAHAR",'
                    'İkinci Bahar - Bölüm '
                    + str(bolum) + '\n'
                )

                dosya.write(adres + "\n")

        os.replace(gecici, M3U_FILE)

        print(
            str(len(kayitlar))
            + " bölüm M3U dosyasına yazıldı."
        )

        return True

    except Exception as hata:

        print("M3U yazma hatası:", hata)

        if os.path.exists(gecici):
            os.remove(gecici)

        return False


# ==================================================
# JSON RAPORU
# ==================================================

def rapor_yaz(sonuclar):

    rapor = {
        "proje": "MIRTI68 - İkinci Bahar",
        "tarih": datetime.now(
            timezone.utc
        ).isoformat(),
        "toplam_kayit": len(VIDEO_IDS),
        "sonuclar": sonuclar
    }

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as dosya:

        json.dump(
            rapor,
            dosya,
            ensure_ascii=False,
            indent=4
        )


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 50)
    print("MIRTI68 - İKİNCİ BAHAR HLS TARAMASI")
    print("=" * 50)

    kayitlar = []
    rapor = []

    gorulen_idler = {}

    for bolum, video_id in enumerate(
        VIDEO_IDS,
        start=1
    ):

        print(
            "\nBölüm "
            + str(bolum)
            + " kontrol ediliyor..."
        )

        if video_id in gorulen_idler:

            ilk_bolum = gorulen_idler[video_id]

            print(
                "Tekrarlanan video ID. İlk bölüm: "
                + str(ilk_bolum)
            )

            rapor.append({
                "bolum": bolum,
                "video_id": video_id,
                "durum": "TEKRAR",
                "ilk_bolum": ilk_bolum
            })

            continue

        gorulen_idler[video_id] = bolum

        sonuc = youtube_hls_bul(video_id)

        if sonuc and sonuc.get("url"):

            kayitlar.append({
                "bolum": bolum,
                "video_id": video_id,
                "url": sonuc["url"]
            })

            rapor.append({
                "bolum": bolum,
                "video_id": video_id,
                "durum": "HLS_BULUNDU",
                "format": sonuc.get("format_id"),
                "height": sonuc.get("height")
            })

            print(
                "HLS bulundu - Bölüm "
                + str(bolum)
            )

        else:

            hata = (
                sonuc.get("error", "Bilinmeyen hata")
                if sonuc else "Video alınamadı"
            )

            rapor.append({
                "bolum": bolum,
                "video_id": video_id,
                "durum": "BULUNAMADI",
                "hata": hata
            })

            print("Bulunamadı:", hata)

    kayitlar.sort(
        key=lambda x: x["bolum"]
    )

    m3u_yaz(kayitlar)
    rapor_yaz(rapor)

    print("\n" + "=" * 50)
    print("TARAMA TAMAMLANDI")
    print("Bulunan HLS:", len(kayitlar))
    print("Toplam bölüm kaydı:", len(VIDEO_IDS))
    print("M3U:", M3U_FILE)
    print("Rapor:", JSON_FILE)
    print("=" * 50)


if __name__ == "__main__":
    main()
    
