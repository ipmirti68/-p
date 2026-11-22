
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import html
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from urllib.parse import urlparse

# ==================================================
# MIRTI68 - IKINCI BAHAR 37 BOLUM
# TELEVIZO UYUMLU HLS M3U8
# SADECE YETKILI YAYIN KAYNAKLARI
# ==================================================

CHANNEL_ID = "UC8Nnnhuc9V5YUiYBa4Qdr6A"

RSS_URL = (
    "https://www.youtube.com/feeds/videos.xml"
    f"?channel_id={CHANNEL_ID}"
)

JSON_FILE = "ikinci_bahar_kaynaklar.json"

HLS_FILE = "ikinci_bahar_hls.json"

M3U_FILE = "ikinci_bahar.m3u"

TOPLAM_BOLUM = 37

GROUP = "🎬 İKİNCİ BAHAR"

TIMEOUT = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Connection": "keep-alive",
}

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


# ==================================================
# ZAMAN
# ==================================================

def now_utc():

    return datetime.now(timezone.utc).isoformat()


# ==================================================
# JSON OKU
# ==================================================

def json_oku(dosya):

    if not os.path.exists(dosya):
        return {}

    try:

        with open(
            dosya,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print("JSON OKUMA HATASI:", e)

        return {}


# ==================================================
# JSON GUVENLI KAYDET
# ==================================================

def json_kaydet(dosya, veri):

    gecici = dosya + ".tmp"

    with open(
        gecici,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            veri,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(gecici, dosya)


# ==================================================
# 37 BOLUM HAZIRLA
# ==================================================

def bolumleri_hazirla(old_data):

    episodes = {}

    for number in range(1, TOPLAM_BOLUM + 1):

        episodes[number] = {
            "episode": number,
            "title": f"İkinci Bahar {number}. Bölüm",
            "youtube_url": None,
            "video_id": None,
            "embed_url": None,
            "hls_url": None,
            "hls_status": "BEKLENİYOR",
            "status": "BEKLENİYOR",
        }

    for item in old_data.get("episodes", []):

        try:

            number = int(item.get("episode"))

        except Exception:

            continue

        if 1 <= number <= TOPLAM_BOLUM:

            episodes[number].update(item)

    return episodes


# ==================================================
# YETKILI HLS KAYNAKLARINI OKU
# ==================================================

def hls_kaynaklarini_oku():

    data = json_oku(HLS_FILE)

    kaynaklar = data.get("episodes", {})

    if not isinstance(kaynaklar, dict):

        return {}

    return kaynaklar


# ==================================================
# YOUTUBE RSS BOLUM BILGILERI
# ==================================================

def youtube_rss_kontrol():

    print("\nYOUTUBE RESMI RSS KONTROL EDILIYOR")

    bulunan = []

    try:

        response = requests.get(
            RSS_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        for entry in root.findall("atom:entry", NS):

            title_node = entry.find(
                "atom:title",
                NS
            )

            id_node = entry.find(
                "yt:videoId",
                NS
            )

            if title_node is None or id_node is None:
                continue

            title = html.unescape(
                title_node.text or ""
            ).strip()

            video_id = (
                id_node.text or ""
            ).strip()

            if not video_id:
                continue

            match = re.search(
                r"(\d{1,2})\s*\.?\s*bölüm",
                title,
                re.IGNORECASE
            )

            if not match:
                continue

            number = int(match.group(1))

            if not 1 <= number <= TOPLAM_BOLUM:
                continue

            bulunan.append({

                "episode": number,

                "title": title,

                "video_id": video_id,

                "youtube_url": (
                    "https://www.youtube.com/watch?v="
                    + video_id
                ),

                "embed_url": (
                    "https://www.youtube.com/embed/"
                    + video_id
                ),

            })

        print("RSS BOLUM SAYISI:", len(bulunan))

    except Exception as e:

        print("RSS HATASI:", str(e))

    return bulunan


# ==================================================
# HLS ADRESI DOGRULA
# ==================================================

def hls_dogrula(adres):

    if not adres:
        return False

    adres = str(adres).strip()

    try:

        parsed = urlparse(adres)

        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.netloc:
            return False

        # YouTube normal video adreslerini kabul etme.

        host = parsed.netloc.lower()

        if (
            "youtube.com" in host
            or "youtu.be" in host
            or "googlevideo.com" in host
        ):

            return False

        headers = dict(HEADERS)

        headers["Range"] = "bytes=0-8191"

        response = requests.get(
            adres,
            headers=headers,
            timeout=TIMEOUT,
            stream=True,
            allow_redirects=True
        )

        try:

            if response.status_code not in (200, 206):

                print(
                    "[HLS HTTP HATASI]",
                    response.status_code,
                    adres[:100]
                )

                return False

            icerik = b""

            for parca in response.iter_content(
                chunk_size=2048
            ):

                if parca:

                    icerik += parca

                if len(icerik) >= 8192:
                    break

            metin = icerik.decode(
                "utf-8-sig",
                errors="ignore"
            ).lstrip()

            # HLS playlist imzası kontrolü.

            if not metin.startswith("#EXTM3U"):

                print(
                    "[HLS GECERSIZ]",
                    adres[:100]
                )

                return False

            print(
                "[HLS OK]",
                adres[:110]
            )

            return True

        finally:

            response.close()

    except Exception as e:

        print(
            "[HLS BAGLANTI HATASI]",
            str(e)[:120]
        )

        return False


# ==================================================
# HLS KAYNAKLARINI BOLUM LERLE BIRLESTIR
# ==================================================

def hls_bolumlerini_isle(episodes, kaynaklar):

    print("\nHLS KAYNAKLARI KONTROL EDILIYOR")

    for no in range(1, TOPLAM_BOLUM + 1):

        item = episodes[no]

        # Önce kaynak JSON dosyasına bak.

        kaynak = kaynaklar.get(str(no))

        if isinstance(kaynak, dict):

            adres = kaynak.get("hls_url")

        elif isinstance(kaynak, str):

            adres = kaynak

        else:

            adres = item.get("hls_url")

        if not adres:

            item["hls_url"] = None

            item["hls_status"] = "KAYNAK YOK"

            continue

        print(
            f"\n[{no}/{TOPLAM_BOLUM}] HLS KONTROL"
        )

        if hls_dogrula(adres):

            item["hls_url"] = adres

            item["hls_status"] = "CALISIYOR"

        else:

            item["hls_url"] = None

            item["hls_status"] = "GECERSIZ VEYA ERISILEMIYOR"

    return episodes


# ==================================================
# TELEVIZO UYUMLU M3U OLUSTUR
# ==================================================

def m3u_olustur(episodes):

    lines = [
        "#EXTM3U"
    ]

    toplam = 0

    for no in range(1, TOPLAM_BOLUM + 1):

        item = episodes[no]

        adres = item.get("hls_url")

        if not adres:
            continue

        if item.get("hls_status") != "CALISIYOR":
            continue

        baslik = (
            f"İkinci Bahar {no}. Bölüm"
        )

        lines.append(
            f'#EXTINF:-1 group-title="{GROUP}",{baslik}'
        )

        lines.append(adres)

        toplam += 1

    if toplam == 0:

        print(
            "\nCALISAN HLS YOK. ESKI M3U KORUNDU."
        )

        return False

    gecici = M3U_FILE + ".tmp"

    with open(
        gecici,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines) + "\n"
        )

    os.replace(
        gecici,
        M3U_FILE
    )

    print("\n================================")
    print("TELEVIZO M3U GUNCELLENDI")
    print("DOSYA:", M3U_FILE)
    print("CALISAN HLS:", toplam)
    print("================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 55)

    print("MIRTI68 - IKINCI BAHAR")

    print("37 BOLUM HLS M3U8 GUNCELLEYICI")

    print("TELEVIZO UYUMLU")

    print("=" * 55)

    # Eski JSON kayıtlarını al.

    old_data = json_oku(JSON_FILE)

    episodes = bolumleri_hazirla(
        old_data
    )

    # RSS ile bölüm bilgilerini güncelle.

    videos = youtube_rss_kontrol()

    for video in videos:

        no = video["episode"]

        episodes[no]["title"] = video["title"]

        episodes[no]["video_id"] = video["video_id"]

        episodes[no]["youtube_url"] = video["youtube_url"]

        episodes[no]["embed_url"] = video["embed_url"]

        episodes[no]["status"] = "RSS BULUNDU"

    # Yetkili HLS kaynaklarını al.

    kaynaklar = hls_kaynaklarini_oku()

    # HLS bağlantılarını doğrula.

    episodes = hls_bolumlerini_isle(
        episodes,
        kaynaklar
    )

    # JSON kayıtlarını hazırla.

    result = {

        "series": "İkinci Bahar",

        "channel": "İkinci Bahar (Dizi)",

        "channel_id": CHANNEL_ID,

        "expected_episodes": TOPLAM_BOLUM,

        "updated_at": now_utc(),

        "playlist": M3U_FILE,

        "format": "HLS M3U8",

        "episodes": [
            episodes[n]
            for n in range(1, TOPLAM_BOLUM + 1)
        ],

    }

    # JSON kaydet.

    json_kaydet(
        JSON_FILE,
        result
    )

    # M3U oluştur.

    m3u_olustur(episodes)

    # Rapor.

    youtube_count = sum(
        1
        for x in episodes.values()
        if x.get("youtube_url")
    )

    hls_count = sum(
        1
        for x in episodes.values()
        if x.get("hls_status") == "CALISIYOR"
    )

    print("\n" + "=" * 55)

    print("IKINCI BAHAR TARAMA RAPORU")

    print("=" * 55)

    print("Toplam bolum:", TOPLAM_BOLUM)

    print("RSS video kaydi:", youtube_count)

    print("Calisan HLS:", hls_count)

    print("HLS bulunamayan:", TOPLAM_BOLUM - hls_count)

    print("JSON:", JSON_FILE)

    print("HLS KAYNAK:", HLS_FILE)

    print("M3U:", M3U_FILE)

    print("=" * 55)


# ==================================================
# CALISTIR
# ==================================================

if __name__ == "__main__":

    main()
                    
