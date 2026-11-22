
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import sys
import urllib3
import warnings
import os
from urllib.parse import urlparse, urljoin

# ==================================================
# MIRTI68 - ATOM SPOR OTOMATIK GUNCELLEYICI
# SADECE BEIN SPORTS GRUBUNU YENILER
# DIGER M3U GRUPLARINI KORUR
# ==================================================

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

warnings.filterwarnings("ignore")

# ==================================================
# AYARLAR
# ==================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Connection": "keep-alive",
}

OUTPUT_FILENAME = "mirti68.m3u"

STATIC_LOGO = (
    "https://i.imgur.com/71TSn0Q.jpeg"
)

GROUP = "🟩◆  beIN SPORTS 🖥"

START_URL = "https://url24.link/AtomSpor"

FALLBACK_BASE = "https://www.atomsportv519.top"

FALLBACK_API = "https://teletv15.top/load/yayinlink.php"

TIMEOUT = 15


# ==================================================
# KANAL ISIMLERI
# ==================================================

PRETTY_NAMES = {

    "bein-sports-1": "beIN SPORTS 1 - Atom ⭕",

    "bein-sports-2": "beIN SPORTS 2 - Atom ⭕",

    "bein-sports-3": "beIN SPORTS 3 - Atom ⭕",

    "bein-sports-4": "beIN SPORTS 4 - Atom ⭕",

    "bein-sports-5": "beIN SPORTS 5 - Atom ⭕",

    "bein-sports-max-1": "beIN SPORTS Max 1 - Atom ⭕",

    "bein-sports-max-2": "beIN SPORTS Max 2 - Atom ⭕",

}

FALLBACK_IDS = list(PRETTY_NAMES.keys())


# ==================================================
# ANA MAKINEYI BUL
# ==================================================

def discover_base_domain():

    print("\nANA MAKINE ARANIYOR")

    headers = HEADERS.copy()
    headers["Referer"] = "https://url24.link/"

    url = START_URL

    try:

        for _ in range(5):

            response = requests.get(
                url,
                headers=headers,
                allow_redirects=False,
                timeout=TIMEOUT
            )

            location = response.headers.get("location")

            if not location:
                break

            url = urljoin(url, location)

        parsed = urlparse(url)

        if parsed.scheme and parsed.netloc:

            base = (
                parsed.scheme
                + "://"
                + parsed.netloc
            )

            print("ANA MAKINE:", base)

            return base

    except Exception as e:

        print("ANA MAKINE HATASI:", e)

    print("YEDEK ANA MAKINE:", FALLBACK_BASE)

    return FALLBACK_BASE


# ==================================================
# API ADRESINI BUL
# ==================================================

def discover_api(base_domain):

    print("\nAPI ADRESI ARANIYOR")

    try:

        response = requests.get(
            base_domain + "/",
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        urls = re.findall(
            r'https?://[^"\'\s\\]+?/load/[a-z0-9_]+\.php',
            response.text,
            re.I
        )

        if urls:

            match = re.match(
                r'(https?://[^/]+)',
                urls[0]
            )

            if match:

                api = (
                    match.group(1)
                    + "/load/yayinlink.php"
                )

                print("API:", api)

                return api

    except Exception as e:

        print("API ARAMA HATASI:", e)

    print("YEDEK API:", FALLBACK_API)

    return FALLBACK_API


# ==================================================
# KANALLARI BUL
# ==================================================

def discover_channels(api_url):

    print("\nKANALLAR OKUNUYOR")

    match = re.match(
        r'(https?://[^/]+)',
        api_url
    )

    origin = (
        match.group(1)
        if match
        else "https://teletv15.top"
    )

    try:

        response = requests.get(
            origin + "/load/channels.php",
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        ids = re.findall(
            r'href=["\']matches\?id=([^"\']+)',
            response.text,
            re.I
        )

        names = re.findall(
            r'<div class="home">([^<]+)</div>',
            response.text,
            re.I
        )

        channels = []
        seen_ids = set()

        for i, cid in enumerate(ids):

            if cid in seen_ids:
                continue

            seen_ids.add(cid)

            site_name = (
                names[i].strip()
                if i < len(names)
                else cid
            )

            name = PRETTY_NAMES.get(
                cid,
                site_name
            )

            # SADECE beIN SPORTS KANALLARI
            if not re.search(
                r'bein[\s_-]*sports',
                cid + " " + name,
                re.IGNORECASE
            ):
                continue

            channels.append(
                (cid, name)
            )

        if channels:

            print(
                "BULUNAN KANAL:",
                len(channels)
            )

            return channels

    except Exception as e:

        print("KANAL OKUMA HATASI:", e)

    print(
        "YEDEK KANAL LISTESI:",
        len(FALLBACK_IDS)
    )

    return [
        (
            cid,
            PRETTY_NAMES.get(cid, cid)
        )
        for cid in FALLBACK_IDS
    ]


# ==================================================
# YAYIN ADRESINI AL
# ==================================================

def get_stream(api_url, cid):

    try:

        response = requests.get(
            api_url,
            params={"id": cid},
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        link = ""

        try:

            data = response.json()

            if isinstance(data, dict):

                link = str(
                    data.get("deismackanal") or ""
                ).strip()

        except ValueError:

            match = re.search(
                r'"deismackanal"\s*:\s*"(.*?)"',
                response.text,
                re.I
            )

            if match:

                link = (
                    match.group(1)
                    .replace("\\/", "/")
                    .strip()
                )

        link = link.replace("\\/", "/").strip()

        parsed = urlparse(link)

        if (
            parsed.scheme in ("https", "http")
            and parsed.netloc
            and ".m3u8" in parsed.path.lower()
        ):

            return link

        print(
            "GECERSIZ YAYIN ADRESI:",
            cid
        )

    except Exception as e:

        print(
            "YAYIN OKUMA HATASI:",
            cid,
            str(e)[:150]
        )

    return ""


# ==================================================
# YENI KANAL LISTESI HAZIRLA
# ==================================================

def yeni_kanallari_hazirla(channels, api_url):

    print("\nYAYINLAR ALINIYOR")

    entries = []
    seen_links = set()

    for cid, name in channels:

        link = get_stream(
            api_url,
            cid
        )

        if not link:

            print(
                "YAYIN YOK:",
                name
            )

            continue

        if link in seen_links:

            print(
                "TEKRAR YAYIN ATLANDI:",
                name
            )

            continue

        seen_links.add(link)

        entry = (
            f'#EXTINF:-1 tvg-logo="{STATIC_LOGO}" '
            f'group-title="{GROUP}",{name}\n'
            f'{link}'
        )

        entries.append(entry)

        print(
            "OK:",
            name
        )

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

            if f'group-title="{GROUP}"' in temiz:

                i += 1

                # Hedef kanalın URL satırını da sil.

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

        print("\nHIC YAYIN BULUNAMADI.")
        print("ESKI DOSYA KORUNDU.")

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

        except Exception as e:

            print("ESKI DOSYA OKUNAMADI:", e)

            return False

    yeni_satirlar = ["#EXTM3U"]

    if eski_satirlar:

        diger_gruplar = eski_grubu_temizle(
            eski_satirlar
        )

        yeni_satirlar.extend(
            diger_gruplar
        )

    # Yeni Atom grubunu ekle.

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

    except Exception as e:

        print("DOSYA KAYIT HATASI:", e)

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

    print(
        "KAYIT YERI:",
        os.path.abspath(OUTPUT_FILENAME)
    )

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

    # Ana makineyi bul.

    base_domain = discover_base_domain()

    # API adresini bul.

    api_url = discover_api(
        base_domain
    )

    # Kanalları bul.

    channels = discover_channels(
        api_url
    )

    if not channels:

        print("KANAL LISTESI BOS.")
        sys.exit(1)

    # Yayın adreslerini al.

    entries = yeni_kanallari_hazirla(
        channels,
        api_url
    )

    # M3U dosyasını güncelle.

    if not m3u_guncelle(entries):

        sys.exit(1)


# ==================================================
# CALISTIR
# ==================================================

if __name__ == "__main__":

    main()
                    

        return False

    print("\n====================================")

    print("MIRTI68 ATOM GUNCELLEME TAMAMLANDI")

    print("====================================")

    print("GRUP:", GROUP)

    print("YENI KANAL:", len(entries))

    print("DIGER GRUPLAR: KORUNDU")

    print("TEKRAR KANAL: ENGELLENDI")

    print("DOSYA:", OUTPUT_FILENAME)

    print(
        "KAYIT YERI:",
        os.path.abspath(OUTPUT_FILENAME)
    )

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

    base_domain = discover_base_domain()

    api_url = discover_api(base_domain)

    channels = discover_channels(api_url)

    if not channels:
        print("KANAL LISTESI BOS.")
        sys.exit(1)

    entries = yeni_kanallari_hazirla(
        channels,
        api_url
    )

    if not m3u_guncelle(entries):
        sys.exit(1)


# ==================================================
# CALISTIR
# ==================================================

if __name__ == "__main__":
    main()
