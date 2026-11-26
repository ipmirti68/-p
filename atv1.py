
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================================================
# MIRTI68 - ATV OTOMATIK YAYIN CEKICI
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

TIMEOUT = 60

# ==================================================
# OTURUM
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
# STREAMLINK KONTROLÜ
# ==================================================

def streamlink_bul():

    yol = shutil.which("streamlink")

    if yol:
        return yol

    print("[HATA] Streamlink kurulu değil.")
    return None


# ==================================================
# ATV YAYIN ADRESİNİ AL
# ==================================================

def atv_yayinini_al():

    print("[1] ATV canlı yayın adresi alınıyor...")

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
            timeout=TIMEOUT
        )

        print("[STREAMLINK] Çıkış kodu:", sonuc.returncode)

        if sonuc.returncode != 0:

            print("[HATA] Streamlink yayın adresini alamadı.")

            if sonuc.stderr:
                print(sonuc.stderr[-2000:])

            return None

        satirlar = sonuc.stdout.splitlines()

        adresler = []

        for satir in satirlar:

            satir = satir.strip()

            if re.match(r"^https?://", satir):
                adresler.append(satir)

        if not adresler:

            print("[HATA] Yayın adresi bulunamadı.")
            print(sonuc.stdout[-2000:])
            return None

        adres = adresler[-1]

        print("[OK] ATV yayın adresi alındı.")

        return adres

    except subprocess.TimeoutExpired:

        print("[HATA] Streamlink zaman aşımına uğradı.")
        return None

    except Exception as hata:

        print("[HATA] Yayın alma hatası:", hata)
        return None


# ==================================================
# HLS M3U8 KONTROLÜ
# ==================================================

def yayin_kontrol(adres):

    print("[2] Yayın bağlantısı kontrol ediliyor...")

    try:

        cevap = session.get(
            adres,
            timeout=20,
            verify=False,
            allow_redirects=True
        )

        print("[HTTP]", cevap.status_code)

        if cevap.status_code != 200:

            print("[HATA] Yayın sunucusu HTTP 200 döndürmedi.")
            return False

        icerik = cevap.text.lstrip("\ufeff \r\n\t")

        if not icerik.startswith("#EXTM3U"):

            print("[HATA] Gelen içerik HLS M3U8 değil.")
            print(icerik[:300])
            return False

        print("[OK] HLS M3U8 doğrulandı.")

        return True

    except requests.RequestException as hata:

        print("[HATA] Yayın kontrol hatası:", hata)
        return False


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

    if f'tvg-id="{TVG_ID}"' in metin:
        return True

    if KANAL in metin:
        return True

    return False


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

        print("[UYARI] M3U dosyası bulunamadı. Yeni dosya oluşturulacak.")
        satirlar = ["#EXTM3U"]

    if not satirlar:
        satirlar = ["#EXTM3U"]

    if satirlar[0].strip() != "#EXTM3U":
        satirlar.insert(0, "#EXTM3U")

    # Kanalları bloklara ayır.
    # Her blok bir #EXTINF satırından başlar.

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

    # Eski ATV kaydını çıkar.
    yeni_bloklar = []

    silinen = 0

    for blok in bloklar:

        if atv_mi(blok):

            silinen += 1
            continue

        yeni_bloklar.append(blok)

    if silinen:
        print("[OK] Eski ATV kaydı yenilenecek.")

    # Yeni ATV kaydı
    yeni_atv = atv_m3u_kaydi(adres)

    # Hedef grubun son kanalını bul.
    grup_sonu = -1

    for indeks, blok in enumerate(yeni_bloklar):

        if hedef_grup_mu(blok):
            grup_sonu = indeks

    if grup_sonu >= 0:

        yeni_bloklar.insert(grup_sonu + 1, yeni_atv)

        print("[OK] ATV mevcut grubun içine eklendi.")

    else:

        yeni_bloklar.append(yeni_atv)

        print("[UYARI] Hedef grup bulunamadı.")
        print("[UYARI] ATV listenin sonuna eklendi.")

    # Dosyayı geçici dosyaya yaz.
    cikti = []

    for satir in baslik:
        cikti.append(satir)

    for blok in yeni_bloklar:

        cikti.extend(blok)

    gecici = Path(M3U_DOSYA + ".tmp")

    try:

        gecici.write_text(
            "\n".join(cikti) + "\n",
            encoding="utf-8"
        )

        # Yazılan dosyanın kontrolü
        kontrol = gecici.read_text(encoding="utf-8")

        if "#EXTM3U" not in kontrol:
            print("[HATA] Geçici M3U kontrolü başarısız.")
            gecici.unlink(missing_ok=True)
            return False

        if TVG_ID not in kontrol:
            print("[HATA] ATV kaydı dosyada bulunamadı.")
            gecici.unlink(missing_ok=True)
            return False

        # Eski dosyanın yerine güvenli şekilde geçir.
        os.replace(gecici, dosya)

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
    print("MIRTI68 - ATV OTOMATİK YAYIN ÇEKİCİ")
    print("TELEVIZO M3U GÜNCELLEYİCİ")
    print("======================================")

    adres = atv_yayinini_al()

    if not adres:

        print("[BAŞARISIZ] ATV yayın adresi alınamadı.")
        sys.exit(1)

    if not yayin_kontrol(adres):

        print("[BAŞARISIZ] HLS kontrolü geçilemedi.")
        sys.exit(1)

    if not m3u_guncelle(adres):

        print("[BAŞARISIZ] M3U güncellenemedi.")
        sys.exit(1)

    print("")
    print("======================================")
    print("ATV GÜNCELLEME TAMAMLANDI")
    print("======================================")


if __name__ == "__main__":
    main()
        
