
import asyncio
import re
import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==========================================
# AYARLAR
# ==========================================

BASE = "https://www.kanald.com.tr"
LIST_URL = BASE + "/kinali-kar/bolumler"
OUTPUT = "kinali_kar.m3u"

GROUP = "🟪◆ KINALI KAR ⭕"

ES_ZAMANLI = 4
SAYFA_TIMEOUT = 45000
BEKLEME = 4000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

# ==========================================
# BÖLÜM NUMARASI
# ==========================================

def bolum_numarasi(text, href=""):
    text = text.lower()
    href = href.lower()

    if "ilk bölüm" in text or "ilk-bolum" in href:
        return 1

    kaliplar = [
        r"(\d+)\s*\.?\s*bölüm",
        r"kinali-kar-(\d+)-bolum",
        r"/(\d+)-bolum"
    ]

    for kalip in kaliplar:
        m = re.search(kalip, text + " " + href)

        if m:
            return int(m.group(1))

    return None


# ==========================================
# BÖLÜMLERİ BUL
# ==========================================

def bolumleri_bul():
    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    print("KINALI KAR BÖLÜMLERİ TARANIYOR")

    sayfalar = [
        LIST_URL,
        LIST_URL + "?page=2",
        LIST_URL + "?page=3"
    ]

    for sayfa in sayfalar:
        print("\nArşiv:", sayfa)

        try:
            r = session.get(sayfa, timeout=40)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.select("a[href]"):
                href = a.get("href", "").strip()

                if "/kinali-kar/bolumler/" not in href:
                    continue

                baslik = " ".join(
                    a.get_text(" ", strip=True).split()
                )

                no = bolum_numarasi(baslik, href)

                if no is None:
                    continue

                tam_url = urljoin(BASE, href)
                bulunan[no] = tam_url

        except Exception as e:
            print("Arşiv sayfası hatası:", e)

    if 1 not in bulunan:
        bulunan[1] = BASE + "/kinali-kar/bolumler/ilk-bolum"

    bulunan = dict(sorted(bulunan.items()))

    print("\n================================")
    print("TOPLAM BULUNAN BÖLÜM:", len(bulunan))
    print("BÖLÜM NUMARALARI:", list(bulunan.keys()))
    print("================================")

    return bulunan


# ==========================================
# YAYIN ADRESİ TARAMA
# ==========================================

async def m3u8_yakala(page_url, context, semaphore, no):

    async with semaphore:

        page = await context.new_page()
        yakalanan = []

        def istek_yakala(request):
            adres = request.url.lower()

            if ".m3u8" in adres:
                if request.url not in yakalanan:
                    yakalanan.append(request.url)

        page.on("request", istek_yakala)

        try:
            print(f"{no}. BÖLÜM AÇILIYOR: {page_url}")

            await page.goto(
                page_url,
                wait_until="domcontentloaded",
                timeout=SAYFA_TIMEOUT
            )

            await page.wait_for_timeout(BEKLEME)

            # Oynatıcı düğmelerini kontrol et
            selectors = [
                "button[aria-label*='Oynat']",
                "button[aria-label*='Play']",
                ".vjs-big-play-button",
                ".jw-icon-play"
            ]

            for selector in selectors:
                try:
                    button = page.locator(selector).first

                    if await button.is_visible(timeout=1000):
                        await button.click(timeout=2500)
                        await page.wait_for_timeout(3000)
                        break

                except Exception:
                    continue

            if yakalanan:
                print(f"{no}. BÖLÜM: Yayın isteği tespit edildi.")
                return no, yakalanan[0]

            print(f"{no}. BÖLÜM: Yayın isteği tespit edilemedi.")
            return no, None

        except Exception as e:
            print(f"{no}. BÖLÜM HATASI: {str(e)[:180]}")
            return no, None

        finally:
            await page.close()


# ==========================================
# M3U OLUŞTUR
# ==========================================

def m3u_olustur(sonuc):

    gecici_dosya = OUTPUT + ".tmp"

    with open(gecici_dosya, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for no, adres in sorted(sonuc.items()):

            if no == 1:
                baslik = "KINALI KAR İLK BÖLÜM"
            else:
                baslik = f"KINALI KAR {no}. BÖLÜM"

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",{baslik}\n'
            )

            f.write(adres + "\n")

    os.replace(gecici_dosya, OUTPUT)

    print("\n================================")
    print("M3U DOSYASI OLUŞTURULDU")
    print("DOSYA:", OUTPUT)
    print("YAYIN SAYISI:", len(sonuc))
    print("================================")


# ==========================================
# ANA PROGRAM
# ==========================================

async def main():

    bolumler = bolumleri_bul()

    if not bolumler:
        print("Bölüm bulunamadı.")
        return

    sonuc = {}
    basarisiz = []

    semaphore = asyncio.Semaphore(ES_ZAMANLI)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"]
        )

        try:

            gorevler = [
                m3u8_yakala(
                    url,
                    context,
                    semaphore,
                    no
                )
                for no, url in bolumler.items()
            ]

            tamamlanan = await asyncio.gather(
                *gorevler,
                return_exceptions=True
            )

            for no, sonuc_adresi in tamamlanan:

                if isinstance(sonuc_adresi, Exception):
                    basarisiz.append(no)
                    continue

                if sonuc_adresi:
                    sonuc[no] = sonuc_adresi
                else:
                    basarisiz.append(no)

        finally:
            await context.close()
            await browser.close()

    # ======================================
    # SONUÇ
    # ======================================

    if sonuc:
        m3u_olustur(sonuc)
    else:
        print("Hiçbir yayın adresi bulunamadı.")
        print("Eski M3U dosyası korunuyor.")

    print("\n================================")
    print("TARAMA SONUCU")
    print("Bulunan:", len(sonuc))
    print("Bulunamayan:", len(basarisiz))
    print("Bulunamayan bölümler:", sorted(basarisiz))
    print("TARAMA TAMAMLANDI.")
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())
