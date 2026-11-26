
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import html
import json
import requests
import urllib3

from html.parser import HTMLParser
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# =========================================================
# MIRTI68 - ATV CANLI YAYIN
# Televizo uyumlu HLS M3U8
# =========================================================

SITE_ID_FALLBACK = "0fe2a405-8afa-4238-b429-e5f96aec3a5c"
LIVE_ID = "00000000-0000-0000-0000-000000000000"

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"

VIDEO_API = (
    "https://videojs.tmgrup.com.tr/getvideo/"
    "{site_id}/{video_id}"
)

TOKEN_API = (
    "https://securevideotoken.tmgrup.com.tr/webtv/secure"
)

M3U_DOSYA = "mirti68.m3u"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
KANAL_ADI = "ATVᴴᴰ ⭕"
TVG_ID = "atv.tr"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

TIMEOUT = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": SAYFA_URL,
    "Origin": "https://www.atv.com.tr",
    "Accept": "*/*",
}


# =========================================================
# HTML İÇİNDEN AYNI ÖĞEDEKİ VIDEO ID VE SITE ID
# =========================================================

class VideoHTMLParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.video_id = None
        self.site_id = None

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        video_id = attrs.get("data-videoid")
        site_id = attrs.get("data-websiteid")

        if video_id and site_id:
            self.video_id = video_id.strip()
            self.site_id = site_id.strip()


def kimlikleri_al(session):

    print("[1] ATV sayfası açılıyor...")

    try:
        response = session.get(
            SAYFA_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        kaynak = response.text

        parser = VideoHTMLParser()
        parser.feed(kaynak)

        video_id = parser.video_id
        site_id = parser.site_id

        # HTML içine kaçışlı gömülmüş içerik ihtimali
        if not video_id or not site_id:

            temiz = html.unescape(kaynak)
            temiz = temiz.replace("\\/", "/")
            temiz = temiz.replace('\\"', '"')

            parser2 = VideoHTMLParser()
            parser2.feed(temiz)

            video_id = video_id or parser2.video_id
            site_id = site_id or parser2.site_id

        # Sayfada video ID bulunamazsa canlı yayın ID'sini kullan
        if not video_id:
            video_id = LIVE_ID

        # Kullanıcının verdiği SITE ID yedek olarak kullanılır
        if not site_id:
            site_id = SITE_ID_FALLBACK

        if not video_id or not site_id:
            print("[HATA] Video veya site kimliği bulunamadı.")
            return None, None

        print("[OK] VIDEO ID:", video_id)
        print("[OK] WEBSITE ID:", site_id)

        return video_id, site_id

    except Exception as e:

        print("[HATA] ATV sayfası okunamadı:", str(e))
        return None, None


# =========================================================
# VIDEO API
# =========================================================

def video_api_al(session, site_id, video_id):

    print("[2] ATV video API sorgulanıyor...")

    api_url = VIDEO_API.format(
        site_id=site_id,
        video_id=video_id
    )

    try:

        response = session.get(
            api_url,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        print("[API] HTTP:", response.status_code)

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            print("[HATA] Video API JSON döndürmedi.")
            return None

        if data.get("success") is not True:
            print("[HATA] API success değeri True değil.")
            print("[API] Dönen alanlar:", list(data.keys()))
            return None

        video = data.get("video")

        if not isinstance(video, dict):
            print("[HATA] API içinde video bilgisi bulunamadı.")
            return None

        smil_url = video.get("VideoSmilUrl")

        if not smil_url:
            print("[HATA] VideoSmilUrl bulunamadı.")
            print("[API] Video alanları:", list(video.keys()))
            return None

        print("[OK] Video adresi alındı.")

        return smil_url

    except Exception as e:

        print("[HATA] Video API:", str(e))
        return None


# =========================================================
# GÜVENLİ YAYIN TOKEN ADRESİ
# =========================================================

def token_al(session, smil_url):

    print("[3] Güvenli yayın adresi alınıyor...")

    try:

        response = session.get(
            TOKEN_API,
            params={"url": smil_url},
            headers=HEADERS,
            timeout=TIMEOUT
        )

        print("[TOKEN] HTTP:", response.status_code)

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            print("[HATA] Token servisi JSON döndürmedi.")
            return None

        if data.get("Success") is not True:
            print("[HATA] Token servisi Success=True döndürmedi.")
            print("[TOKEN] Dönen alanlar:", list(data.keys()))
            return None

        yayin_url = data.get("Url")

        if not yayin_url:
            print("[HATA] Token yanıtında Url bulunamadı.")
            return None

        if not yayin_url.startswith(("http://", "https://")):
            print("[HATA] Yayın adresi geçerli HTTP adresi değil.")
            return None

        print("[OK] Güvenli yayın adresi alındı.")
        print("[OK] Yayın sunucusu:", urlparse(yayin_url).netloc)

        return yayin_url

    except Exception as e:

        print("[HATA] Token servisi:", str(e))
        return None


# =========================================================
# HLS YAYININI KONTROL ET
# =========================================================

def hls_kontrol(session, yayin_url):

    print("[4] HLS yayın kontrolü yapılıyor...")

    try:

        response = session.get(
            yayin_url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True
        )

        print("[HLS] HTTP:", response.status_code)

        response.raise_for_status()

        ilk_parca = next(
            response.iter_content(chunk_size=4096),
            b""
        )

        response.close()

        icerik = ilk_parca.decode(
            "utf-8",
            errors="ignore"
        ).lstrip("\ufeff \r\n\t")

        if not icerik.startswith("#EXTM3U"):

            print("[HATA] Gelen yanıt HLS M3U8 değil.")
            print("[HATA] İlk yanıt:", repr(icerik[:150]))
            return False

        print("[OK] HLS M3U8 başlığı doğrulandı.")

        return True

    except Exception as e:

        print("[HATA] HLS kontrolü başarısız:", str(e))
        return False


# =========================================================
# M3U KANAL BLOĞU
# =========================================================

def kanal_blok(yayin_url):

    return [
        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL_ADI}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL_ADI}'
        ),
        yayin_url
    ]


# =========================================================
# M3U BLOKLARINI OKU
# =========================================================

def m3u_bloklara_ayir(satirlar):

    baslik = []
    bloklar = []
    mevcut = []

    for satir in satirlar:

        if satir.startswith("#EXTINF:"):

            if mevcut:
                bloklar.append(mevcut)

            mevcut = [satir]

        elif mevcut:
            mevcut.append(satir)

        else:
            baslik.append(satir)

    if mevcut:
        bloklar.append(mevcut)

    return baslik, bloklar


def blok_grubu(blok):

    if not blok:
        return ""

    extinf = blok[0]

    eslesme = re.search(
        r'group-title="([^"]*)"',
        extinf,
        re.IGNORECASE
    )

    if eslesme:
        return eslesme.group(1)

    return ""


def atv_blok_mu(blok):

    if not blok:
        return False

    satir = blok[0].lower()

    return (
        'tvg-id="atv.tr"' in satir
        or "atvᴴᴰ⭕".lower() in satir
    )


# =========================================================
# M3U İÇİNE ATV EKLE / GÜNCELLE
# =========================================================

def m3u_guncelle(yayin_url):

    print("[5] M3U dosyası güncelleniyor...")

    if os.path.exists(M3U_DOSYA):

        try:

            with open(
                M3U_DOSYA,
                "r",
                encoding="utf-8-sig"
            ) as f:

                satirlar = f.read().splitlines()

        except Exception as e:

            print("[HATA] M3U okunamadı:", str(e))
            return False

    else:

        satirlar = ["#EXTM3U"]

    if not satirlar:
        satirlar = ["#EXTM3U"]

    baslik, bloklar = m3u_bloklara_ayir(satirlar)

    # ATV'nin eski kayıtlarını kaldır.
    # Diğer kanallara dokunulmaz.
    yeni_bloklar = [
        blok for blok in bloklar
        if not atv_blok_mu(blok)
    ]

    # Hedef grubun son kanalını bul.
    grup_indeksi = -1

    for i, blok in enumerate(yeni_bloklar):

        if blok_grubu(blok) == GRUP:
            grup_indeksi = i

    yeni_atv = kanal_blok(yayin_url)

    if grup_indeksi >= 0:

        yeni_bloklar.insert(
            grup_indeksi + 1,
            yeni_atv
        )

        print("[OK] ATV mevcut grubun içine eklendi.")

    else:

        yeni_bloklar.append(yeni_atv)

        print("[BİLGİ] Hedef grup bulunamadı.")
        print("[BİLGİ] ATV kanal kaydı dosyanın sonuna eklendi.")

    # Dosya içeriğini yeniden oluştur.
    cikti = []

    cikti.extend(baslik)

    if not any(
        satir.strip() == "#EXTM3U"
        for satir in cikti
    ):
        cikti.insert(0, "#EXTM3U")

    for blok in yeni_bloklar:
        cikti.extend(blok)

    gecici_dosya = M3U_DOSYA + ".tmp"

    try:

        with open(
            gecici_dosya,
            "w",
            encoding="utf-8"
        ) as f:

            f.write("\n".join(cikti))
            f.write("\n")

        os.replace(
            gecici_dosya,
            M3U_DOSYA
        )

        print("[OK] M3U dosyası kaydedildi.")
        print("[OK] Kanal:", KANAL_ADI)
        print("[OK] Grup:", GRUP)

        return True

    except Exception as e:

        print("[HATA] M3U kaydedilemedi:", str(e))

        if os.path.exists(gecici_dosya):
            os.remove(gecici_dosya)

        return False


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    print("=" * 55)
    print("       MIRTI68 - ATV CANLI YAYIN")
    print("       TELEVIZO HLS M3U8 SİSTEMİ")
    print("=" * 55)

    session = requests.Session()

    session.headers.update(HEADERS)

    # 1 - Video ve site kimlikleri
    video_id, site_id = kimlikleri_al(session)

    if not video_id or not site_id:
        print("[DURDU] Kimlikler alınamadı.")
        sys.exit(1)

    # 2 - Video API
    smil_url = video_api_al(
        session,
        site_id,
        video_id
    )

    if not smil_url:
        print("[DURDU] Video API adresi alınamadı.")
        sys.exit(1)

    # 3 - Token
    yayin_url = token_al(
        session,
        smil_url
    )

    if not yayin_url:
        print("[DURDU] Güvenli yayın adresi alınamadı.")
        sys.exit(1)

    # 4 - HLS kontrolü
    if not hls_kontrol(
        session,
        yayin_url
    ):
        print("[DURDU] Yayın M3U8 olarak doğrulanamadı.")
        sys.exit(1)

    # 5 - M3U kaydı
    if not m3u_guncelle(yayin_url):
        print("[DURDU] M3U güncellenemedi.")
        sys.exit(1)

    print("=" * 55)
    print("[BAŞARILI] ATV M3U kaydı güncellendi.")
    print("=" * 55)


if __name__ == "__main__":
    main()
