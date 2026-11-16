
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import re
import time
import requests

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from yt_dlp import YoutubeDL

# ==========================================
# MIRTI68 - EŞREF RÜYA BOT
# ==========================================

BASE = "https://www.kanald.com.tr"
LIST_URL = BASE + "/esref-ruya/bolumler"

OUTPUT = "esref_ruya.m3u"
GROUP = "🟪◆ EŞREF RÜYA ⭕"

MAX_SAYFA = 20
BEKLEME = 1000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    ),
    "Referer": BASE + "/"
}

# ==========================================
# BÖLÜM NUMARASI
# ==========================================

def bolum_numarasi(text, href=""):

    text = text.lower()
    href = href.lower()

    if "ilk bölüm" in text or "ilk-bolum" in href:
        return 1

    patterns = [
        r"esref-ruya-(\d+)-bolum",
        r"(\d+)\s*\.?\s*bölüm",
        r"(\d+)-bolum"
    ]

    for pattern in patterns:

        kaynak = href if "esref-ruya" in pattern else text

        m = re.search(pattern, kaynak)

        if m:
            return int(m.group(1))

    return None


# ==========================================
# BÖLÜM ADI
# ==========================================

def bolum_adi(no):

    if no == 1:
        return "EŞREF RÜYA İLK BÖLÜM"

    return f"EŞREF RÜYA {no}. BÖLÜM"


# ==========================================
# BÖLÜMLERİ BUL
# ==========================================

def bolumleri_bul():

    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    for sayfa in range(1, MAX_SAYFA + 1):

        url = f"{LIST_URL}?page={sayfa}"

        print("\nListe taranıyor:", url)

        try:

            r = session.get(
                url,
                timeout=30
            )

            r.raise_for_status()

            soup = BeautifulSoup(
                r.text,
                "html.parser"
            )

            for a in soup.select("a[href]"):

                href = a.get("href", "")

                if "/esref-ruya/bolumler/" not in href:
                    continue

                baslik = " ".join(
                    a.get_text(" ", strip=True).split()
                )

                no = bolum_numarasi(
                    baslik,
                    href
                )

                if no is None or no < 1:
                    continue

                tam_url = urljoin(BASE, href)

                if no not in bulunan:

                    bulunan[no] = tam_url

                    print(
                        "Bulundu:",
                        bolum_adi(no)
                    )

        except Exception as e:

            print("Liste hatası:", e)

    return dict(sorted(bulunan.items()))


# ==========================================
# DAILYMOTION VIDEO KİMLİĞİ BUL
# ==========================================

def video_id_bul(adres):

    patterns = [
        r"dailymotion\.com/(?:embed/)?video/([A-Za-z0-9]+)",
        r"/manifest/video/([A-Za-z0-9]+)\.m3u8",
        r"/video/([A-Za-z0-9]+)\.m3u8"
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            adres,
            re.IGNORECASE
        )

        if m:
            return m.group(1)

    return None


# ==========================================
# KANAL D SAYFASINDAN VİDEO KİMLİĞİ YAKALA
# ==========================================

async def video_kimligi_yakala(page_url, browser):

    context = await browser.new_context(
        user_agent=HEADERS["User-Agent"]
    )

    page = await context.new_page()

    kimlikler = []

    def ekle(adres):

        vid = video_id_bul(adres)

        if vid and vid not in kimlikler:

            kimlikler.append(vid)

            print(
                "Video kimliği bulundu:",
                vid
            )

    def istek_yakala(request):

        ekle(request.url)

    page.on(
        "request",
        istek_yakala
    )

    try:

        await page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(10000)

        # Sayfadaki video iframe adresleri

        iframe_adresleri = await page.locator(
            "iframe"
        ).evaluate_all(
            "(items) => items.map(x => x.src).filter(Boolean)"
        )

        for adres in iframe_adresleri:
            ekle(adres)

        # Açık sayfa çerçevelerini tara

        for frame in page.frames:

            try:
                ekle(frame.url)
            except Exception:
                pass

        # Oynatmayı dene

        for selector in [
            "button[aria-label*='Oynat']",
            "button[aria-label*='Play']",
            ".vjs-big-play-button",
            ".jw-icon-play"
        ]:

            try:

                button = page.locator(
                    selector
                ).first

                if await button.is_visible(
                    timeout=1500
                ):

                    await button.click(
                        timeout=3000
                    )

                    await page.wait_for_timeout(
                        10000
                    )

                    break

            except Exception:
                pass

        # Son kez iframe kontrolü

        iframe_adresleri = await page.locator(
            "iframe"
        ).evaluate_all(
            "(items) => items.map(x => x.src).filter(Boolean)"
        )

        for adres in iframe_adresleri:
            ekle(adres)

    except Exception as e:

        print("Sayfa tarama hatası:", e)

    finally:

        await context.close()

    return kimlikler


# ==========================================
# YT-DLP İLE VİDEO ÇÖZ
# ==========================================

def videoyu_coz(video_id):

    video_url = (
        "https://www.dailymotion.com/video/"
        + video_id
    )

    print("\nDailymotion çözülüyor:", video_id)

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "format": "best",
        "http_headers": {
            "User-Agent": HEADERS["User-Agent"],
            "Referer": "https://www.dailymotion.com/"
        }
    }

    try:

        with YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                video_url,
                download=False
            )

            if not info:
                return None

            formats = info.get(
                "formats",
                []
            )

            # Önce doğrudan HLS adreslerini seç

            hls_formats = [
                fmt for fmt in formats
                if (
                    fmt.get("protocol", "").startswith("m3u8")
                    or ".m3u8" in fmt.get("url", "").lower()
                )
                and fmt.get("url")
                and not fmt.get("has_drm")
                and fmt.get("vcodec") != "none"
            ]

            if hls_formats:

                hls_formats.sort(
                    key=lambda x: (
                        x.get("height") or 0,
                        x.get("tbr") or 0
                    ),
                    reverse=True
                )

                secilen = hls_formats[0]

            else:

                secilen = info

            adres = secilen.get("url")

            if not adres:
                print("Video adresi bulunamadı.")
                return None

            video_headers = (
                secilen.get("http_headers")
                or info.get("http_headers")
                or {}
            )

            print(
                "Çözüldü:",
                secilen.get("height", "Bilinmiyor"),
                "p"
            )

            return {
                "url": adres,
                "headers": video_headers
            }

    except Exception as e:

        print(
            "Video çözme hatası:",
            str(e)[:300]
        )

        return None


# ==========================================
# M3U OLUŞTUR
# ==========================================

def m3u_olustur(sonuc):

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for no, bilgi in sorted(sonuc.items()):

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",'
                f'{bolum_adi(no)}\n'
            )

            headers = bilgi.get(
                "headers",
                {}
            )

            ua = headers.get(
                "User-Agent",
                HEADERS["User-Agent"]
            )

            referer = headers.get(
                "Referer",
                headers.get(
                    "referer",
                    "https://www.dailymotion.com/"
                )
            )

            f.write(
                "#EXTVLCOPT:http-user-agent="
                + ua + "\n"
            )

            f.write(
                "#EXTVLCOPT:http-referrer="
                + referer + "\n"
            )

            f.write(
                bilgi["url"] + "\n"
            )

    print("\n================================")
    print("MIRTI68 - EŞREF RÜYA TAMAMLANDI")
    print("================================")
    print("Dosya:", OUTPUT)
    print("Oynatma adresi bulunan:", len(sonuc))
    print("================================")


# ==========================================
# ANA PROGRAM
# ==========================================

async def main():

    print("================================")
    print("MIRTI68 - EŞREF RÜYA BOT")
    print("================================")

    bolumler = bolumleri_bul()

    if not bolumler:

        print("Bölüm bulunamadı.")
        return

    print(
        "\nToplam bölüm:",
        len(bolumler)
    )

    sonuc = {}

    basarisiz = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        try:

            for no, url in bolumler.items():

                print("\n--------------------------------")
                print("Taranıyor:", bolum_adi(no))
                print("--------------------------------")

                kimlikler = await video_kimligi_yakala(
                    url,
                    browser
                )

                if not kimlikler:

                    print("Dailymotion kimliği bulunamadı.")
                    basarisiz.append(no)
                    continue

                cozuldu = None

                for video_id in kimlikler:

                    cozuldu = videoyu_coz(
                        video_id
                    )

                    if cozuldu:
                        break

                if cozuldu:

                    sonuc[no] = cozuldu

                    print("Bölüm kaydedilecek.")

                else:

                    print("Oynatma adresi çözülemedi.")
                    basarisiz.append(no)

                await asyncio.sleep(1)

        finally:

            await browser.close()

    if sonuc:

        m3u_olustur(sonuc)

    print("\n================================")
    print("TARAMA RAPORU")
    print("================================")
    print("Bulunan bölüm:", len(bolumler))
    print("Çözülen yayın:", len(sonuc))
    print("Başarısız bölüm:", len(basarisiz))

    if basarisiz:
        print(
            "Başarısız numaralar:",
            ", ".join(map(str, basarisiz))
        )

    print("================================")


# ==========================================
# BAŞLAT
# ==========================================

if __name__ == "__main__":

    asyncio.run(main())
    
