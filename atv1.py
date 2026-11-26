
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import subprocess
import requests
import urllib3

from pathlib import Path
from urllib.parse import urljoin

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

# ==================================================
# MIRTI68 - ATV HLS GELİŞMİŞ TEST SİSTEMİ
# TELEVIZO UYUMLU M3U
# ==================================================

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"

M3U_DOSYA = "mirti68.m3u"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
KANAL = "ATVᴴᴰ⭕"
TVG_ID = "atv.tr"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

REFERER = "https://www.atv.com.tr/canli-yayin"
ORIGIN = "https://www.atv.com.tr"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TIMEOUT = 30

# ==================================================
# HTTP OTURUMU
# ==================================================

session = requests.Session()

session.headers.update({
    "User-Agent": USER_AGENT,
    "Referer": REFERER,
    "Origin": ORIGIN,
    "Accept": "*/*",
    "Connection": "keep-alive"
})


# ==================================================
# GÜVENLİ URL GÖSTERİMİ
# TOKEN VE GİZLİ PARAMETRELERİ YAZDIRMAZ
# ==================================================

def guvenli_adres(adres):

    from urllib.parse import urlsplit

    try:

        parca = urlsplit(adres)

        return (
            parca.scheme + "://" +
            parca.netloc +
            parca.path
        )

    except Exception:

        return "Adres gizlendi"


# ==================================================
# STREAMLINK
# ==================================================

def streamlink_bul():

    yol = shutil.which("streamlink")

    if yol:
        print("[OK] Streamlink bulundu:", yol)
        return yol

    print("[HATA] Streamlink kurulu değil.")

    return None


# ==================================================
# ATV YAYIN ADRESİNİ AL
# ==================================================

def atv_yayinini_al():

    print("")
    print("[1] ATV canlı yayın sayfası taranıyor...")

    streamlink = streamlink_bul()

    if not streamlink:
        return None

    komut = [
        streamlink,
        "--loglevel", "error",
        "--http-header", f"Referer={REFERER}",
        "--http-header", f"Origin={ORIGIN}",
        "--http-header", f"User-Agent={USER_AGENT}",
        "--stream-url",
        SAYFA_URL,
        "best"
    ]

    try:

        sonuc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            timeout=60
        )

        print(
            "[STREAMLINK] Çıkış kodu:",
            sonuc.returncode
        )

        if sonuc.returncode != 0:

            print("[HATA] Streamlink başarısız.")

            if sonuc.stderr:
                print(sonuc.stderr[-1500:])

            return None

        adresler = []

        for satir in sonuc.stdout.splitlines():

            satir = satir.strip()

            if re.match(r"^https?://", satir):
                adresler.append(satir)

        if not adresler:

            print("[HATA] Yayın adresi bulunamadı.")

            return None

        adres = adresler[-1]

        print("[OK] ATV yayın adresi alındı.")
        print("[URL]", guvenli_adres(adres))

        return adres

    except subprocess.TimeoutExpired:

        print("[HATA] Streamlink zaman aşımı.")

        return None

    except Exception as hata:

        print("[HATA] Streamlink:", hata)

        return None


# ==================================================
# HLS DOSYASINI İNDİR
# ==================================================

def hls_oku(adres, baslik):

    try:

        cevap = session.get(
            adres,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )

        print(
            f"[{baslik}] HTTP:",
            cevap.status_code
        )

        if cevap.status_code != 200:
            return None, None

        icerik = cevap.text.lstrip("\ufeff \r\n\t")

        if not icerik.startswith("#EXTM3U"):

            print(
                f"[HATA] {baslik}: HLS formatı değil."
            )

            return None, None

        return icerik, cevap.url

    except requests.RequestException as hata:

        print(f"[HATA] {baslik}:", hata)

        return None, None


# ==================================================
# HLS SATIRLARINDAN URI BUL
# ==================================================

def hls_uri_bul(satir):

    eslesme = re.search(
        r'URI="([^"]+)"',
        satir
    )

    if eslesme:
        return eslesme.group(1)

    return None


# ==================================================
# YAYIN PARÇASI TESTİ
# ==================================================

def parca_test(adres, aciklama):

    print("")
    print("[TEST]", aciklama)

    print("[URL]", guvenli_adres(adres))

    try:

        cevap = session.get(
            adres,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True,
            stream=True
        )

        print("[PARÇA HTTP]", cevap.status_code)

        if cevap.status_code not in (200, 206):

            print("[HATA] Yayın parçası indirilemedi.")

            cevap.close()

            return False

        veri = cevap.raw.read(65536)

        cevap.close()

        print("[İNDİRİLEN BYTE]", len(veri))

        if len(veri) < 100:

            print("[HATA] Video parçası çok küçük.")

            return False

        # HTML hata sayfasını tespit et.
        ilk = veri[:500].lstrip().lower()

        if (
            ilk.startswith(b"<!doctype html")
            or ilk.startswith(b"<html")
            or b"access denied" in ilk
            or b"forbidden" in ilk
        ):

            print("[HATA] Sunucu video yerine HTML döndürdü.")

            return False

        print("[OK] Yayın parçası indirilebildi.")

        return True

    except requests.RequestException as hata:

        print("[HATA] Video parçası:", hata)

        return False


# ==================================================
# ŞİFRELEME ANAHTARI TESTİ
# ==================================================

def anahtar_test(anahtar_adresi):

    print("")
    print("[TEST] HLS şifreleme anahtarı")

    try:

        cevap = session.get(
            anahtar_adresi,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )

        print("[ANAHTAR HTTP]", cevap.status_code)

        if cevap.status_code != 200:

            print("[HATA] Anahtara erişilemedi.")

            return False

        if len(cevap.content) < 16:

            print("[HATA] Anahtar yanıtı eksik.")

            return False

        print("[OK] Anahtar indirilebildi.")

        return True

    except requests.RequestException as hata:

        print("[HATA] Anahtar testi:", hata)

        return False


# ==================================================
# HLS YAYIN ZİNCİRİ
# ==================================================

def hls_zincir_test(adres):

    print("")
    print("======================================")
    print("MIRTI68 ATV HLS ZİNCİR TESTİ")
    print("======================================")

    icerik, son_adres = hls_oku(
        adres,
        "ANA M3U8"
    )

    if not icerik:

        print("[BAŞARISIZ] Ana M3U8 okunamadı.")

        return False

    print("[OK] Ana M3U8 okundu.")

    # --------------------------------------------------
    # MASTER PLAYLIST KONTROLÜ
    # --------------------------------------------------

    satirlar = [
        x.strip()
        for x in icerik.splitlines()
        if x.strip()
    ]

    varyantlar = []

    for i, satir in enumerate(satirlar):

        if satir.startswith("#EXT-X-STREAM-INF:"):

            bant = re.search(
                r"BANDWIDTH=(\d+)",
                satir
            )

            hiz = int(bant.group(1)) if bant else 0

            if i + 1 < len(satirlar):

                alt = satirlar[i + 1]

                if not alt.startswith("#"):

                    varyantlar.append(
                        (hiz, urljoin(son_adres, alt))
                    )

    if varyantlar:

        varyantlar.sort(
            key=lambda x: x[0],
            reverse=True
        )

        alt_adres = varyantlar[0][1]

        print(
            "[OK] Master playlist bulundu.",
            "Varyant sayısı:",
            len(varyantlar)
        )

        print(
            "[SEÇİLEN BANDWIDTH]",
            varyantlar[0][0]
        )

        medya, medya_adresi = hls_oku(
            alt_adres,
            "ALT M3U8"
        )

        if not medya:

            print("[BAŞARISIZ] Alt M3U8 okunamadı.")

            return False

    else:

        print("[BİLGİ] Ana dosya doğrudan medya playlist'i.")

        medya = icerik
        medya_adresi = son_adres

    # --------------------------------------------------
    # ŞİFRELEME ANAHTARI
    # --------------------------------------------------

    for satir in medya.splitlines():

        if not satir.startswith("#EXT-X-KEY:"):
            continue

        if "METHOD=NONE" in satir:
            continue

        anahtar = hls_uri_bul(satir)

        if anahtar:

            anahtar_adresi = urljoin(
                medya_adresi,
                anahtar
            )

            if not anahtar_test(anahtar_adresi):
                return False

        else:

            print(
                "[UYARI] Şifreleme satırı var fakat "
                "URI bulunamadı."
            )

    # --------------------------------------------------
    # INIT SEGMENT / MAP
    # --------------------------------------------------

    map_adresi = None

    for satir in medya.splitlines():

        if satir.startswith("#EXT-X-MAP:"):

            uri = hls_uri_bul(satir)

            if uri:

                map_adresi = urljoin(
                    medya_adresi,
                    uri
                )

                break

    if map_adresi:

        if not parca_test(
            map_adresi,
            "INIT SEGMENT"
        ):

            return False

    # --------------------------------------------------
    # İLK VİDEO PARÇASI
    # --------------------------------------------------

    parca_adresi = None

    for satir in medya.splitlines():

        satir = satir.strip()

        if not satir or satir.startswith("#"):
            continue

        parca_adresi = urljoin(
            medya_adresi,
            satir
        )

        break

    if not parca_adresi:

        print("[HATA] Medya playlist içinde parça bulunamadı.")

        return False

    if not parca_test(
        parca_adresi,
        "İLK VİDEO PARÇASI"
    ):

        print("[BAŞARISIZ] Video parçası alınamadı.")

        return False

    print("")
    print("[BAŞARILI] HLS zinciri test edildi.")

    return True


# ==================================================
# ATV M3U KAYDI
# ==================================================

def atv_m3u_kaydi(adres):

    return [
        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL}'
        ),

        f"#EXTVLCOPT:http-referrer={REFERER}",

        f"#EXTVLCOPT:http-origin={ORIGIN}",

        f"#EXTVLCOPT:http-user-agent={USER_AGENT}",

        adres
    ]


# ==================================================
# ATV KAYDINI TANIMA
# ==================================================

def atv_mi(blok):

    metin = "\n".join(blok)

    return (
        f'tvg-id="{TVG_ID}"' in metin
        or KANAL in metin
    )


# ==================================================
# GRUP KONTROLÜ
# ==================================================

def hedef_grup_mu(blok):

    for satir in blok:

        if not satir.startswith("#EXTINF:"):
            continue

        eslesme = re.search(
            r'group-title="([^"]*)"',
            satir
        )

        if eslesme and eslesme.group(1) == GRUP:
            return True

    return False


# ==================================================
# M3U DOSYASINI GÜVENLİ GÜNCELLE
# ==================================================

def m3u_guncelle(adres):

    print("")
    print("[3] M3U dosyası hazırlanıyor...")

    dosya = Path(M3U_DOSYA)

    if dosya.exists():

        try:

            satirlar = dosya.read_text(
                encoding="utf-8-sig"
            ).splitlines()

        except Exception as hata:

            print("[HATA] M3U okunamadı:", hata)

            return False

    else:

        print("[HATA] mirti68.m3u bulunamadı.")

        return False

    if not satirlar:
        print("[HATA] M3U dosyası boş.")
        return False

    if satirlar[0].strip() != "#EXTM3U":

        print("[HATA] M3U başlığı geçersiz.")

        return False

    baslik = []
    bloklar = []
    mevcut_blok = None

    for satir in satirlar:

        if satir.startswith("#EXTINF:"):

            if mevcut_blok is not None:
                bloklar.append(mevcut_blok)

            mevcut_blok = [satir]

        elif mevcut_blok is None:

            baslik.append(satir)

        else:

            mevcut_blok.append(satir)

    if mevcut_blok is not None:
        bloklar.append(mevcut_blok)

    yeni_bloklar = []
    silinen = 0

    for blok in bloklar:

        if atv_mi(blok):

            silinen += 1

        else:

            yeni_bloklar.append(blok)

    print("[ESKİ ATV KAYDI]", silinen)

    grup_sonu = -1

    for indeks, blok in enumerate(yeni_bloklar):

        if hedef_grup_mu(blok):
            grup_sonu = indeks

    yeni_atv = atv_m3u_kaydi(adres)

    if grup_sonu >= 0:

        yeni_bloklar.insert(
            grup_sonu + 1,
            yeni_atv
        )

        print("[OK] ATV mevcut grubun içine eklendi.")

    else:

        print("[HATA] Hedef grup bulunamadı.")

        return False

    cikti = []

    cikti.extend(baslik)

    for blok in yeni_bloklar:
        cikti.extend(blok)

    gecici = Path(M3U_DOSYA + ".tmp")

    try:

        gecici.write_text(
            "\n".join(cikti) + "\n",
            encoding="utf-8"
        )

        kontrol = gecici.read_text(
            encoding="utf-8"
        )

        if kontrol.count(f'tvg-id="{TVG_ID}"') != 1:

            print("[HATA] ATV tekrar kontrolü başarısız.")

            gecici.unlink(missing_ok=True)

            return False

        if "#EXTM3U" not in kontrol:

            print("[HATA] M3U başlığı kayboldu.")

            gecici.unlink(missing_ok=True)

            return False

        os.replace(
            gecici,
            dosya
        )

        print("[BAŞARILI] ATV M3U dosyasına yazıldı.")

        return True

    except Exception as hata:

        print("[HATA] M3U yazma hatası:", hata)

        gecici.unlink(missing_ok=True)

        return False


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("")
    print("======================================")
    print("MIRTI68 ATV HLS TEŞHİS SİSTEMİ")
    print("======================================")

    adres = atv_yayinini_al()

    if not adres:

        print("[BAŞARISIZ] Yayın adresi alınamadı.")

        sys.exit(1)

    # HLS zincirini test et.
    # Başarısızsa mevcut M3U kaydına dokunma.

    if not hls_zincir_test(adres):

        print("")
        print("[BAŞARISIZ] HLS zincir testi geçilemedi.")
        print("[BİLGİ] Mevcut M3U kaydı korundu.")

        sys.exit(1)

    # Tüm testler başarılıysa M3U güncelle.

    if not m3u_guncelle(adres):

        print("[BAŞARISIZ] M3U güncellenemedi.")

        sys.exit(1)

    print("")
    print("======================================")
    print("ATV GÜNCELLEME TAMAMLANDI")
    print("HLS ZİNCİR TESTİ BAŞARILI")
    print("======================================")


if __name__ == "__main__":
    main()
    
