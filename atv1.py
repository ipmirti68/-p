
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import subprocess
import requests

# ==========================================
# MIRTI68 - ATV OTOMATİK YAYIN ÇEKİCİ
# ==========================================

SAYFA = "https://www.atv.com.tr/canli-yayin"

M3U_DOSYA = "mirti68.m3u"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
KANAL = "ATVᴴᴰ.  ⭕"
TVG_ID = "atv.tr"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": SAYFA,
    "Origin": "https://www.atv.com.tr"
}


# ==========================================
# 1 - STREAMLINK KONTROLÜ
# ==========================================

def streamlink_kontrol():

    komut = shutil.which("streamlink")

    if not komut:
        print("[HATA] Streamlink kurulu değil.")
        return None

    print("[OK] Streamlink bulundu:", komut)

    return komut


# ==========================================
# 2 - ATV YAYININI OTOMATİK ÇEK
# ==========================================

def yayin_cek():

    print("\n[1] ATV canlı yayın sayfası taranıyor...")

    streamlink = streamlink_kontrol()

    if not streamlink:
        return None

    komut = [
        streamlink,
        "--loglevel", "info",
        "--stream-url",
        SAYFA,
        "best"
    ]

    try:

        sonuc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            timeout=120
        )

        print("[STREAMLINK] Çıkış kodu:", sonuc.returncode)

        if sonuc.stderr:
            print("[STREAMLINK LOG]")
            print(sonuc.stderr[-5000:])

        if sonuc.returncode != 0:
            print("[HATA] ATV yayın adresi çekilemedi.")
            return None

        adresler = re.findall(
            r'https?://[^\s\'"]+',
            sonuc.stdout
        )

        if not adresler:
            print("[HATA] Çıktıda yayın URL'si bulunamadı.")
            print(sonuc.stdout[-2000:])
            return None

        yayin = adresler[-1].strip()

        print("[OK] ATV yayın adresi çekildi.")

        return yayin

    except subprocess.TimeoutExpired:
        print("[HATA] Yayın çekme işlemi zaman aşımına uğradı.")
        return None

    except Exception as e:
        print("[HATA] Yayın çekme:", str(e))
        return None


# ==========================================
# 3 - YAYIN ADRESİNİ TEST ET
# ==========================================

def yayin_test(adres):

    print("\n[2] Yayın adresi kontrol ediliyor...")

    try:

        r = requests.get(
            adres,
            headers=HEADERS,
            timeout=25,
            stream=True,
            allow_redirects=True
        )

        print("[HTTP]", r.status_code)

        r.raise_for_status()

        veri = next(
            r.iter_content(chunk_size=4096),
            b""
        )

        r.close()

        metin = veri.decode(
            "utf-8",
            errors="ignore"
        ).lstrip("\ufeff \r\n\t")

        if not metin.startswith("#EXTM3U"):

            print("[HATA] Gelen veri HLS M3U8 değil.")
            print("[YANIT]", repr(metin[:200]))

            return False

        print("[OK] HLS M3U8 doğrulandı.")

        return True

    except Exception as e:

        print("[HATA] Yayın kontrolü:", str(e))

        return False


# ==========================================
# 4 - M3U DOSYASINI OKU
# ==========================================

def m3u_oku():

    if not os.path.exists(M3U_DOSYA):
        return ["#EXTM3U"]

    with open(
        M3U_DOSYA,
        "r",
        encoding="utf-8-sig"
    ) as f:

        satirlar = f.read().splitlines()

    if not satirlar:
        return ["#EXTM3U"]

    return satirlar


# ==========================================
# 5 - BLOKLARA AYIR
# ==========================================

def bloklara_ayir(satirlar):

    baslik = []
    bloklar = []
    blok = []

    for satir in satirlar:

        if satir.startswith("#EXTINF:"):

            if blok:
                bloklar.append(blok)

            blok = [satir]

        elif blok:
            blok.append(satir)

        else:
            baslik.append(satir)

    if blok:
        bloklar.append(blok)

    return baslik, bloklar


# ==========================================
# 6 - ATV KAYDINI TANIMA
# ==========================================

def atv_mi(blok):

    if not blok:
        return False

    satir = blok[0].lower()

    return (
        'tvg-id="atv.tr"' in satir
        or "atvᴴᴰ. ⭕".lower() in satir
    )


# ==========================================
# 7 - GRUP KONTROLÜ
# ==========================================

def grup_mu(blok):

    if not blok:
        return False

    return f'group-title="{GRUP}"' in blok[0]


# ==========================================
# 8 - ATV KANALINI OLUŞTUR
# ==========================================

def atv_kanal(adres):

    return [
        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL}'
        ),
        adres
    ]


# ==========================================
# 9 - M3U GÜNCELLE
# ==========================================

def m3u_guncelle(adres):

    print("\n[3] M3U dosyası hazırlanıyor...")

    satirlar = m3u_oku()

    baslik, bloklar = bloklara_ayir(satirlar)

    # Eski ATV kayıtlarını kaldır.
    diger_kanallar = [
        blok for blok in bloklar
        if not atv_mi(blok)
    ]

    yeni_atv = atv_kanal(adres)

    # Hedef grubun son kanalını bul.
    hedef = -1

    for i, blok in enumerate(diger_kanallar):

        if grup_mu(blok):
            hedef = i

    if hedef >= 0:

        diger_kanallar.insert(
            hedef + 1,
            yeni_atv
        )

        print("[OK] ATV mevcut grubun içine eklendi.")

    else:

        diger_kanallar.append(yeni_atv)

        print("[UYARI] Hedef grup bulunamadı.")
        print("[BİLGİ] ATV dosyanın sonuna eklendi.")

    cikti = list(baslik)

    if not any(
        x.strip() == "#EXTM3U"
        for x in cikti
    ):
        cikti.insert(0, "#EXTM3U")

    for blok in diger_kanallar:
        cikti.extend(blok)

    gecici = M3U_DOSYA + ".tmp"

    try:

        with open(
            gecici,
            "w",
            encoding="utf-8"
        ) as f:

            f.write("\n".join(cikti) + "\n")

        os.replace(
            gecici,
            M3U_DOSYA
        )

        print("[BAŞARILI] ATV M3U dosyasına yazıldı.")

        return True

    except Exception as e:

        print("[HATA] M3U kaydedilemedi:", str(e))

        if os.path.exists(gecici):
            os.remove(gecici)

        return False


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    print("=" * 50)
    print("MIRTI68 - ATV OTOMATİK YAYIN ÇEKİCİ")
    print("=" * 50)

    adres = yayin_cek()

    if not adres:
        print("[SONUÇ] Yeni yayın adresi alınamadı.")
        sys.exit(1)

    if not yayin_test(adres):
        print("[SONUÇ] Yayın doğrulanamadı; eski M3U korunuyor.")
        sys.exit(1)

    if not m3u_guncelle(adres):
        sys.exit(1)

    print("=" * 50)
    print("ATV GÜNCELLEME TAMAMLANDI")
    print("=" * 50)


if __name__ == "__main__":
    main()
    
