
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - YILAN HIKAYESI
# KANAL D / DAILYMOTION HLS KONTROLLU TARAMA
# ==================================================

BASE = "https://www.kanald.com.tr"
LIST_URL = BASE + "/yilan-hikayesi/bolumler"

OUTPUT = "yilan_hikayesi.m3u"

GROUP = "🟪◆ YILAN HİKAYESİ"

MAX_BOLUM = 90
ES_ZAMANLI = 3

SAYFA_TIMEOUT = 40000
BEKLEME = 7000
MANIFEST_TIMEOUT = 15000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

# ==================================================
# BOLUM ADI
# ==================================================

def bolum_adi(no):

    if no <= 32:
        sezon = 1
        bolum = no

    elif no <= 64:
        sezon = 2
        bolum = no - 32

    else:
        sezon = 3
        bolum = no - 64

    return f"YILAN HİKAYESİ S{sezon:02d} E{bolum:02d}"


# ==================================================
# BOLUM NUMARASI
# ==================================================

def bolum_numarasi(text, href=""):

    metin = (text + " " + href).lower()

    if "ilk-bolum" in metin or "ilk bölüm" in metin:
        return 1

    kaliplar = [
        r"yilan-hikayesi-(\d+)-bolum",
        r"/(\d+)-bolum(?:/|$|\?)",
        r"(\d+)\s*\.?\s*bölüm"
    ]

    for kalip in kaliplar:

        m = re.search(kalip, metin)

        if m:
            return int(m.group(1))

    return None


# ==================================================
# ESKI M3U OKU
# ==================================================

def eski_m3u_oku():

    eski = {}

    if not os.path.exists(OUTPUT):
        return eski

    try:

        with open(
            OUTPUT,
            "r",
            encoding="utf-8"
        ) as f:

            satirlar = f.read().splitlines()

        aktif_no = None
        secenekler = []

        for satir in satirlar:

            satir = satir.strip()

            if satir.startswith("#EXTINF"):

                aktif_no = None
                secenekler = []

                m = re.search(
                    r"S(\d{2})\s+E(\d{2})",
                    satir,
                    re.IGNORECASE
                )

                if m:

                    sezon = int(m.group(1))
                    bolum = int(m.group(2))

                    if sezon == 1:
                        aktif_no = bolum
                    elif sezon == 2:
                        aktif_no = 32 + bolum
                    elif sezon == 3:
                        aktif_no = 64 + bolum

            elif satir.startswith("#EXTVLCOPT"):

                secenekler.append(satir)

            elif satir and not satir.startswith("#"):

                if aktif_no is not None:
                    eski[aktif_no] = {
                        "url": satir,
                        "options": list(secenekler)
                    }

                aktif_no = None
                secenekler = []

        print("ESKI KAYIT:", len(eski))

    except Exception as e:

        print("Eski M3U okuma hatasi:", e)

    return eski


# ==================================================
# BOLUM LISTESI
# ==================================================

def bolumleri_bul():

    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    print("\nKANAL D ARSIVI TARANIYOR")

    for sayfa in range(1, 11):

        url = (
            LIST_URL
            + f"?orderby=EpisodeNumber+asc&page={sayfa}"
        )

        try:

            response = session.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for a in soup.select("a[href]"):

                href = a.get("href", "").strip()

                if "/yilan-hikayesi/bolumler/" not in href:
                    continue

                baslik = " ".join(
                    a.get_text(" ", strip=True).split()
                )

                no = bolum_numarasi(
                    baslik,
                    href
                )

                if no is None:
                    continue

                if not 1 <= no <= MAX_BOLUM:
                    continue

                bulunan[no] = urljoin(
                    BASE,
                    href
                )

            print(
                f"Arsiv sayfasi {sayfa}: "
                f"{len(bulunan)} bolum"
            )

        except Exception as e:

            print(
                f"Arsiv sayfasi {sayfa} hatasi:",
                str(e)[:150]
            )

    # Bilinen sayfa adreslerini eksikler için dene.
    for no in range(1, MAX_BOLUM + 1):

        if no in bulunan:
            continue

        if no == 1:
            bulunan[no] = (
                LIST_URL + "/yilan-hikayesi-ilk-bolum"
            )
        else:
            bulunan[no] = (
                LIST_URL + f"/yilan-hikayesi-{no}-bolum"
            )

    return dict(sorted(bulunan.items()))


# ==================================================
# HLS MANIFEST KONTROLU
# ==================================================

def manifest_gecerli(body):

    if not body:
        return False

    metin = body.lstrip("\ufeff \r\n\t")

    if not metin.startswith("#EXTM3U"):
        return False

    # HLS manifestinde beklenen etiketlerden biri olmalı.
    etiketler = [
        "#EXT-X-STREAM-INF",
        "#EXT-X-TARGETDURATION",
        "#EXT-X-MEDIA-SEQUENCE",
        "#EXTINF",
        "#EXT-X-PLAYLIST-TYPE",
        "#EXT-X-MAP"
    ]

    return any(
        etiket in metin
        for etiket in etiketler
    )


# ==================================================
# M3U8 YAKALA VE DOGRULA
# ==================================================

async def m3u8_yakala(
    no,
    page_url,
    browser,
    semaphore
):

    async with semaphore:

        page = await browser.new_page(
            user_agent=HEADERS["User-Agent"]
        )

        adaylar = []

        def cevap_yakala(response):

            adres = response.url

            if ".m3u8" not in adres.lower():
                return

            if "adbreak" in adres.lower():
                return

            if "googleads" in adres.lower():
                return

            adaylar.append(response)

        page.on(
            "response",
            cevap_yakala
        )

        try:

            print(
                f"\n[{no}/90] "
                f"{bolum_adi(no)}"
            )

            await page.goto(
                page_url,
                wait_until="domcontentloaded",
                timeout=SAYFA_TIMEOUT
            )

            await page.wait_for_timeout(
                BEKLEME
            )

            # Oynatıcı düğmelerini dene.
            selectors = [
                "button[aria-label*='Oynat']",
                "button[aria-label*='Play']",
                ".vjs-big-play-button",
                ".jw-icon-play",
                ".plyr__control--overlaid"
            ]

            for selector in selectors:

                try:

                    button = page.locator(
                        selector
                    ).first

                    if await button.is_visible(
                        timeout=1000
                    ):

                        await button.click(
                            timeout=2500,
                            force=True
                        )

                        await page.wait_for_timeout(
                            5000
                        )

                        break

                except Exception:
                    continue

            if not adaylar:

                await page.wait_for_timeout(
                    5000
                )

            # En son gelen manifestleri de kontrol et.
            for response in reversed(adaylar):

                try:

                    if response.status != 200:
                        continue

                    body = await response.text()

                    if not manifest_gecerli(body):
                        continue

                    adres = response.url

                    print(
                        f"[MANIFEST OK] "
                        f"{bolum_adi(no)}"
                    )

                    return {
                        "url": adres,
                        "referer": page_url,
                        "options": [
                            "#EXTVLCOPT:http-user-agent="
                            + HEADERS["User-Agent"],
                            "#EXTVLCOPT:http-referrer="
                            + page_url
                        ]
                    }

                except Exception:
                    continue

            print(
                f"[MANIFEST GECERSIZ/YOK] "
                f"{bolum_adi(no)}"
            )

            return None

        except Exception as e:

            print(
                f"[SAYFA HATASI] "
                f"{no}: {str(e)[:150]}"
            )

            return None

        finally:

            page.remove_listener(
                "response",
                cevap_yakala
            )

            await page.close()


# ==================================================
# M3U OLUSTUR
# ==================================================

def m3u_olustur(kayitlar):

    gecici = OUTPUT + ".tmp"

    with open(
        gecici,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for no, kayit in sorted(kayitlar.items()):

            if no < 1 or no > MAX_BOLUM:
                continue

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",'
                f'{bolum_adi(no)}\n'
            )

            for option in kayit.get("options", []):
                f.write(option + "\n")

            f.write(kayit["url"] + "\n")

    os.replace(
        gecici,
        OUTPUT
    )

    print("\nM3U DOSYASI GUNCELLENDI")
    print("DOSYA:", OUTPUT)
    print("KAYIT:", len(kayitlar))


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    print("====================================")
    print("MIRTI68 - YILAN HIKAYESI")
    print("HLS MANIFEST KONTROLLU BOT")
    print("====================================")

    eski = eski_m3u_oku()

    bolumler = bolumleri_bul()

    if not bolumler:
        print("Bolum listesi bulunamadi.")
        return

    print(
        "\nTARAMA LISTESI:",
        len(bolumler)
    )

    yeni = {}
    basarisiz = []

    semaphore = asyncio.Semaphore(
        ES_ZAMANLI
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        try:

            gorevler = [
                m3u8_yakala(
                    no,
                    url,
                    browser,
                    semaphore
                )
                for no, url in bolumler.items()
            ]

            sonuclar = await asyncio.gather(
                *gorevler,
                return_exceptions=True
            )

            for no, sonuc in zip(
                bolumler.keys(),
                sonuclar
            ):

                if isinstance(sonuc, Exception):

                    print(
                        "GOREV HATASI:",
                        no,
                        str(sonuc)[:100]
                    )

                    basarisiz.append(no)
                    continue

                if sonuc:

                    yeni[no] = sonuc

                else:

                    basarisiz.append(no)

        finally:

            await browser.close()

    # ==========================================
    # ESKI + YENI KAYITLAR
    # ==========================================

    birlesik = dict(eski)

    for no, kayit in yeni.items():

        birlesik[no] = kayit

    # Yeni adres yoksa mevcut dosyaya dokunma.
    if not yeni:

        print("\nYENI GECERLI MANIFEST BULUNAMADI.")

        if eski:
            print("ESKI M3U KORUNDU.")

        return

    m3u_olustur(birlesik)

    # ==========================================
    # RAPOR
    # ==========================================

    print("\n====================================")
    print("YILAN HIKAYESI TARAMA RAPORU")
    print("====================================")

    print("Arsiv bolumu:", len(bolumler))
    print("Yeni dogrulanan:", len(yeni))
    print("Eski kayit:", len(eski))
    print("Toplam M3U kaydi:", len(birlesik))
    print("Dogrulanamayan:", len(basarisiz))

    if basarisiz:
        print(
            "Dogrulanamayan bolumler:",
            sorted(basarisiz)
        )

    print("ISLEM TAMAMLANDI.")
    print("====================================")


if __name__ == "__main__":
    asyncio.run(main())
            
