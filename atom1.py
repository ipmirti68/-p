
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
from urllib.parse import urlparse

# ==================================================
# MIRTI68 - ATOM SPOR M3U GUNCELLEYICI
# SADECE BEIN SPORTS GRUBUNU YENILER
# DIGER M3U GRUPLARINI KORUR
# ==================================================

OUTPUT_FILENAME = "mirti68.m3u"

STATIC_LOGO = "https://i.imgur.com/71TSn0Q.jpeg"

GROUP = "🟩◆ beIN SPORTS 🖥"

# ==================================================
# YETKILI HLS YAYIN ADRESLERI
# KENDI ERISIM HAKKIN OLAN M3U8 ADRESLERINI GIR
# ==================================================

AUTHORIZED_CHANNELS = [
    {
        "id": "bein-sports-1",
        "name": "beIN SPORTS 1 - Atom ⭕",
        "url": ""
    },
    {
        "id": "bein-sports-2",
        "name": "beIN SPORTS 2 - Atom ⭕",
        "url": ""
    },
    {
        "id": "bein-sports-3",
        "name": "beIN SPORTS 3 - Atom ⭕",
        "url": ""
    },
    {
        "id": "bein-sports-4",
        "name": "beIN SPORTS 4 - Atom ⭕",
        "url": ""
    },
    {
        "id": "bein-sports-5",
        "name": "beIN SPORTS 5 - Atom ⭕",
        "url": ""
    },
    {
        "id": "bein-sports-max-1",
        "name": "beIN SPORTS Max 1 - Atom ⭕",
        "url": ""
    },
    {
        "id": "bein-sports-max-2",
        "name": "beIN SPORTS Max 2 - Atom ⭕",
        "url": ""
    }
]


# ==================================================
# M3U8 ADRES KONTROLU
# ==================================================

def hls_adresi_gecerli(url):

    if not url:
        return False

    url = url.strip()

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.netloc:
            return False

        if ".m3u8" not in parsed.path.lower():
            return False

        return True

    except Exception:
        return False


# ==================================================
# YENI KANAL LISTESI HAZIRLA
# ==================================================

def yeni_kanallari_hazirla():

    print("\nYAYINLAR KONTROL EDILIYOR")

    entries = []
    seen_links = set()

    for kanal in AUTHORIZED_CHANNELS:

        name = kanal.get("name", "").strip()
        link = kanal.get("url", "").strip()

        if not name:
            continue

        if not hls_adresi_gecerli(link):

            print("GECERSIZ VEYA BOS ADRES:", name)
            continue

        if link in seen_links:

            print("TEKRAR YAYIN ATLANDI:", name)
            continue

        seen_links.add(link)

        entry = (
            f'#EXTINF:-1 tvg-logo="{STATIC_LOGO}" '
            f'group-title="{GROUP}",{name}\n'
            f'{link}'
        )

        entries.append(entry)

        print("OK:", name)

    print("\nBULUNAN GECERLI KANAL:", len(entries))

    return entries


# ==================================================
# SADECE HEDEF GRUBU TEMIZLE
# ==================================================

def eski_grubu_temizle(eski_satirlar):

    yeni_satirlar = []

    i = 0

    while i < len(eski_satirlar):

        satir = eski_satirlar[i]
        temiz = satir.strip()

        if temiz == "#EXTM3U":
            i += 1
            continue

        if temiz.startswith("#EXTINF:"):

            grup_eslesmesi = re.search(
                r'group-title="([^"]*)"',
                temiz,
                re.IGNORECASE
            )

            hedef_grup = (
                grup_eslesmesi.group(1)
                if grup_eslesmesi
                else ""
            )

            if hedef_grup == GROUP:

                i += 1

                # Kanalin URL satirini da atla.
                while i < len(eski_satirlar):

                    sonraki = eski_satirlar[i].strip()

                    if sonraki and not sonraki.startswith("#"):
                        i += 1
                        break

                    i += 1

                continue

        yeni_satirlar.append(satir)
        i += 1

    return yeni_satirlar


# ==================================================
# M3U DOSYASINI GUVENLI GUNCELLE
# ==================================================

def m3u_guncelle(entries):

    if not entries:

        print("\nHIC GECERLI YAYIN BULUNAMADI.")
        print("ESKI M3U DOSYASI KORUNDU.")

        return False

    eski_satirlar = []

    if os.path.exists(OUTPUT_FILENAME):

        try:

            with open(
                OUTPUT_FILENAME,
                "r",
                encoding="utf-8-sig"
            ) as f:

                eski_satirlar = f.read().splitlines()

        except Exception as hata:

            print("ESKI DOSYA OKUNAMADI:", hata)
            return False

    yeni_satirlar = ["#EXTM3U"]

    if eski_satirlar:

        diger_gruplar = eski_grubu_temizle(
            eski_satirlar
        )

        yeni_satirlar.extend(diger_gruplar)

    # Yeni beIN SPORTS grubunu ekle.

    for entry in entries:

        yeni_satirlar.extend(
            entry.splitlines()
        )

    gecici = OUTPUT_FILENAME + ".tmp"

    try:

        with open(
            gecici,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n".join(yeni_satirlar)
                + "\n"
            )

        os.replace(
            gecici,
            OUTPUT_FILENAME
        )

    except Exception as hata:

        print("DOSYA KAYIT HATASI:", hata)

        if os.path.exists(gecici):
            os.remove(gecici)

        return False

    print("\n====================================")
    print("MIRTI68 ATOM GUNCELLEME TAMAMLANDI")
    print("====================================")
    print("GRUP:", GROUP)
    print("YENI KANAL:", len(entries))
    print("DIGER GRUPLAR: KORUNDU")
    print("TEKRAR KANAL: ENGELLENDI")
    print("DOSYA:", OUTPUT_FILENAME)
    print("KAYIT YERI:", os.path.abspath(OUTPUT_FILENAME))
    print("====================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("\n" + "=" * 50)
    print("MIRTI68 - ATOM SPOR")
    print("SADECE BEIN SPORTS GRUBU YENILENIR")
    print("=" * 50)

    entries = yeni_kanallari_hazirla()

    if not entries:

        print("\nGUNCELLEME YAPILMADI.")
        print("ESKI DOSYA KORUNDU.")
        sys.exit(1)

    if not m3u_guncelle(entries):

        sys.exit(1)


# ==================================================
# CALISTIR
# ==================================================

if __name__ == "__main__":
    main()
    
