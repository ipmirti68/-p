
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import re
import requests

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - IHLAMURLAR ALTINDA KANAL D BOT
# RESMI KANAL D BOLUM TARAMA
# ==================================================

BASE = "https://www.kanald.com.tr"

DIZI_URL = BASE + "/ihlamurlaraltinda"
BOLUM_URL = DIZI_URL + "/bolumler"

OUTPUT = "ihlamurlar_altinda.m3u"

GROUP = "🟪◆ IHLAMURLAR ALTINDA ⭕"

TOPLAM_BOLUM = 80
ES_ZAMANLI = 3

SAYFA_TIMEOUT = 35000
BEKLEME = 5000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
}


# ==================================================
# BOLUM ADRESLERI
# ==================================================

def bolum_adresi(no):
    return BOLUM_URL + f"/{no}-bolum"


# ==================================================
# ESKI M3U DOSYASINI OKU
# ==================================================

def eski_m3u_oku():

    eski = {}

    if not os.path.exists(OUTPUT):
        return eski

    try:
        with open(OUTPUT, "r", encoding="utf-8") as f:
            satirlar = f.read().splitlines()

        son_no = None

        for satir in satirlar:

            satir = satir.strip()

            if satir.startswith("#EXTINF"):

                m = re.search(
                    r"IHLAMURLAR ALTINDA\s+(?:İLK|(\d+))",
                    satir,
                    re.IGNORECASE
                )

                if m:
                    son_no = int(m.group(1)) if m.group(1) else 1

            elif satir and not satir.startswith("#"):

                if son_no is not None:
                    eski[son_no] = satir

                son_no = None

        print("ESKI KAYIT:", len(eski))

    except Exception as e:
        print("Eski M3U okuma hatasi:", e)

    return eski


# ==================================================
# BOLUM SAYFALARINI BUL
# ==================================================

def bolumleri_bul():

    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    print("\nIHLAMURLAR ALTINDA ARSIVI KONTROL EDILIYOR")

    # Ana dizi ve arşiv sayfaları
    sayfalar = [
        DIZI_URL,
        BOLUM_URL,
    ]

    # Arşiv sayfalarının sayfalama bağlantıları
    for page in range(1, 6):

        sayfalar.append(
            BOLUM_URL +
            f"?orderby=EpisodeNumber+asc&page={page}"
        )

    for sayfa_url in sayfalar:

        try:

            response = session.get(
                sayfa_url,
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for a in soup.select("a[href]"):

                href = a.get("href", "").strip()

                match = re.search(
                    r"/ihlamurlaraltinda/bolumler/(\d+)-bolum",
                    href,
                    re.IGNORECASE
                )

                if match:

                    no = int(match.group(1))

                    if 1 <= no <= TOPLAM_BOLUM:

                        bulunan[no] = urljoin(
                            BASE,
                            href
                        )

            print(
                "[ARSIV]",
                sayfa_url.split("?")[0],
                "BULUNAN:",
                len(bulunan)
            )

        except Exception as e:

            print(
                "[ARSIV HATASI]",
                str(e)[:120]
            )

    # Eksik numaralar için resmî adres biçimini ekle.
    # Gerçek sayfa ve yayın kontrolü Playwright tarafından yapılır.

    for no in range(1, TOPLAM_BOLUM + 1):

        if no not in bulunan:

            bulunan[no] = bolum_adresi(no)

    bulunan = dict(sorted(bulunan.items()))

    print("----------------------------------")
    print("TARAMA LISTESI:", len(bulunan))
    print("ILK BOLUM:", bolum_adresi(1))
    print("SON BOLUM:", bolum_adresi(TOPLAM_BOLUM))
    print("----------------------------------")

    return bulunan


# ==================================================
# M3U8 ADRESI YAKALA
# ==================================================

async def m3u8_yakala(
    no,
    page_url,
    browser,
    semaphore
):

    async with semaphore:

        page = await browser.new_page()

        yakalanan = []

        def response_yakala(response):

            adres = response.url

            if ".m3u8" not in adres.lower():
                return

            try:

                if response.status >= 400:
                    return

            except Exception:
                return

            if adres not in yakalanan:
                yakalanan.append(adres)

        page.on("response", response_yakala)

        try:

            print(
                f"\n[{no}/{TOPLAM_BOLUM}] BOLUM ACILIYOR"
            )

            await page.goto(
                page_url,
                wait_until="domcontentloaded",
                timeout=SAYFA_TIMEOUT
            )

            await page.wait_for_timeout(BEKLEME)

            # Oynatıcı başlatma düğmeleri

            seciciler = [
                "button[aria-label*='Oynat']",
                "button[aria-label*='Play']",
                ".vjs-big-play-button",
                ".jw-icon-play",
                ".plyr__control--overlaid",
                "[data-testid='play-button']"
            ]

            for secici in seciciler:

                try:

                    dugme = page.locator(secici).first

                    if await dugme.is_visible(timeout=1000):

                        await dugme.click(
                            timeout=2500,
                            force=True
                        )

                        await page.wait_for_timeout(4000)

                        if yakalanan:
                            break

                except Exception:
                    continue

            # Oynatıcıya ek süre ver

            if not yakalanan:
                await page.wait_for_timeout(3000)

            if yakalanan:

                yakalanan.sort(
                    key=lambda x: (
                        "manifest" not in x.lower(),
                        "master" not in x.lower(),
                        -len(x)
                    )
                )

                adres = yakalanan[0]

                print(
                    f"[BULUNDU] {no}. BOLUM "
                    f"({len(yakalanan)} adres)"
                )

                return no, adres

            print(
                f"[BULUNAMADI] {no}. BOLUM"
            )

            return no, None

        except Exception as e:

            print(
                f"[HATA] {no}. BOLUM: "
                f"{str(e)[:150]}"
            )

            return no, None

        finally:

            page.remove_listener(
                "response",
                response_yakala
            )

            await page.close()


# ==================================================
# M3U OLUSTUR
# ==================================================

def m3u_olustur(sonuc):

    gecici = OUTPUT + ".tmp"

    with open(
        gecici,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for no, adres in sorted(sonuc.items()):

            if no == 1:

                baslik = (
                    "IHLAMURLAR ALTINDA ILK BOLUM"
                )

            elif no == TOPLAM_BOLUM:

                baslik = (
                    f"IHLAMURLAR ALTINDA "
                    f"{no}. BOLUM - FINAL"
                )

            else:

                baslik = (
                    f"IHLAMURLAR ALTINDA "
                    f"{no}. BOLUM"
                )

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",{baslik}\n'
            )

            f.write(adres + "\n")

    os.replace(gecici, OUTPUT)

    print("\n================================")
    print("M3U DOSYASI GUNCELLENDI")
    print("DOSYA:", OUTPUT)
    print("TOPLAM KAYIT:", len(sonuc))
    print("================================")


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    print("================================")
    print("MIRTI68 IHLAMURLAR ALTINDA BOT")
    print("KANAL D RESMI BOLUM TARAMA")
    print("================================")

    eski = eski_m3u_oku()

    bolumler = bolumleri_bul()

    if not bolumler:

        print("Bolum bulunamadi.")
        return

    yeni = {}

    basarisiz = []

    semaphore = asyncio.Semaphore(ES_ZAMANLI)

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

            tamamlanan = await asyncio.gather(
                *gorevler,
                return_exceptions=True
            )

            for sonuc in tamamlanan:

                if isinstance(sonuc, Exception):

                    print(
                        "GOREV HATASI:",
                        sonuc
                    )

                    continue

                no, adres = sonuc

                if adres:

                    yeni[no] = adres

                else:

                    basarisiz.append(no)

        finally:

            await browser.close()

    # ==============================================
    # ESKI VE YENI KAYITLARI BIRLESTIR
    # ==============================================

    birlesik = dict(eski)

    for no, adres in yeni.items():

        birlesik[no] = adres

    # Hiç yeni adres yoksa eski dosyayı koru.

    if not yeni:

        print("\nHIC YENI YAYIN BULUNAMADI.")

        if eski:

            print("ESKI M3U DOSYASI KORUNDU.")

        else:

            print("M3U DOSYASI OLUSTURULMADI.")

    else:

        m3u_olustur(birlesik)

    # ==============================================
    # RAPOR
    # ==============================================

    print("\n================================")
    print("IHLAMURLAR ALTINDA TARAMA RAPORU")
    print("================================")

    print("Arsiv bolumu:", len(bolumler))
    print("Yeni bulunan:", len(yeni))
    print("Eski kayit:", len(eski))
    print("Birlesik toplam:", len(birlesik))
    print("Basarisiz:", len(basarisiz))

    if basarisiz:

        print(
            "Bulunamayan bolumler:",
            sorted(basarisiz)
        )

    print("TARAMA TAMAMLANDI.")
    print("================================")


# ==================================================
# CALISTIR
# ==================================================

if __name__ == "__main__":

    asyncio.run(main())
