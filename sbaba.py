
import asyncio
import re
import os
import requests

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==========================================
# AYARLAR
# ==========================================

BASE = "https://www.atv.com.tr"
LIST_URL = BASE + "/super-baba/bolumler"

OUTPUT = "super_baba.m3u"
GROUP = "🟪◆ SÜPER BABA"

TOPLAM_BOLUM = 137
ES_ZAMANLI = 6
SAYFA_TIMEOUT = 20000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}


# ==========================================
# BÖLÜM LİNKLERİNİ TOPLA
# ==========================================

def bolumleri_bul():

    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    print("SÜPER BABA BÖLÜMLERİ TARANIYOR")

    bos_sayfa = 0

    for sayfa in range(1, 21):

        url = (
            LIST_URL
            if sayfa == 1
            else f"{LIST_URL}?page={sayfa}"
        )

        print(f"\nListe sayfası: {sayfa}")

        try:
            cevap = session.get(url, timeout=25)
            cevap.raise_for_status()

            soup = BeautifulSoup(
                cevap.text,
                "html.parser"
            )

            yeni = 0

            for a in soup.select("a[href]"):

                href = a.get("href", "").strip()

                match = re.search(
                    r"/super-baba/(\d+)-bolum/izle(?:[/?#]|$)",
                    href,
                    re.I
                )

                if not match:
                    continue

                no = int(match.group(1))

                if not 1 <= no <= TOPLAM_BOLUM:
                    continue

                tam_url = urljoin(BASE, href)

                # Yalnızca ATV alan adındaki bağlantıları kabul et
                parsed = urlparse(tam_url)

                if parsed.netloc.lower() not in (
                    "www.atv.com.tr",
                    "atv.com.tr"
                ):
                    continue

                if no not in bulunan:
                    bulunan[no] = tam_url
                    yeni += 1

                    print(f"{no}. bölüm bulundu: {tam_url}")

            print("Yeni bulunan:", yeni)

            if yeni == 0:
                bos_sayfa += 1
            else:
                bos_sayfa = 0

            if bos_sayfa >= 3:
                print(
                    "Üç ardışık boş sayfa nedeniyle "
                    "liste taraması durduruldu."
                )
                break

        except Exception as e:
            print("Liste hatası:", str(e)[:180])

    bulunan = dict(sorted(bulunan.items()))

    print("\n================================")
    print("GERÇEK BULUNAN BÖLÜM:", len(bulunan))
    print("BÖLÜM NUMARALARI:", list(bulunan.keys()))
    print("================================")

    return bulunan


# ==========================================
# TEK BÖLÜMDE YAYIN ADRESİ KONTROLÜ
# ==========================================

async def m3u8_yakala(page_url, context, no):

    page = await context.new_page()
    yakalanan = []

    def istek_yakala(request):

        adres = request.url

        if ".m3u8" in adres.lower():

            if adres not in yakalanan:
                yakalanan.append(adres)
                print(f"{no}. bölüm: HLS isteği görüldü.")

    page.on("request", istek_yakala)

    try:

        response = await page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=SAYFA_TIMEOUT
        )

        if response and response.status >= 400:
            print(f"{no}. bölüm HTTP: {response.status}")
            return []

        await page.wait_for_timeout(3000)

        selectors = [
            "button[aria-label*='Oynat']",
            "button[aria-label*='Play']",
            ".vjs-big-play-button",
            ".jw-icon-play",
            ".plyr__control--overlaid"
        ]

        for selector in selectors:

            try:

                button = page.locator(selector).first

                if await button.is_visible(timeout=700):

                    await button.click(timeout=2000)
                    await page.wait_for_timeout(3000)

                    break

            except Exception:
                continue

        if yakalanan:
            return yakalanan

        await page.wait_for_timeout(2000)

        return yakalanan

    except Exception as e:

        print(
            f"{no}. bölüm açılamadı: "
            f"{str(e)[:120]}"
        )

        return []

    finally:

        await page.close()


# ==========================================
# M3U DOSYASINI OLUŞTUR
# ==========================================

def m3u_olustur(sonuc):

    if not sonuc:
        print("Yayın bulunamadı. Eski M3U korunuyor.")
        return

    gecici = OUTPUT + ".tmp"

    with open(gecici, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for no, adres in sorted(sonuc.items()):

            baslik = f"SÜPER BABA {no:03d}. BÖLÜM"

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",{baslik}\n'
            )

            f.write(adres.strip() + "\n")

    os.replace(gecici, OUTPUT)

    print("\n================================")
    print("M3U DOSYASI OLUŞTURULDU")
    print("Dosya:", OUTPUT)
    print("Bulunan yayın:", len(sonuc))
    print("Bölümler:", sorted(sonuc.keys()))
    print("================================")


# ==========================================
# ANA PROGRAM
# ==========================================

async def main():

    print("SÜPER BABA TARAMASI BAŞLADI")
    print("--------------------------------")

    bolumler = bolumleri_bul()

    if not bolumler:
        print("Arşivden gerçek bölüm bağlantısı alınamadı.")
        print("Eski M3U korunuyor.")
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

        async def bolum_gorevi(no, url):

            async with semaphore:

                print(f"\n{no}. bölüm kontrol ediliyor")

                try:
                    adresler = await m3u8_yakala(
                        url,
                        context,
                        no
                    )

                    if adresler:
                        sonuc[no] = adresler[0]
                        print(f"{no}. bölüm: Yayın bulundu.")
                    else:
                        basarisiz.append(no)
                        print(f"{no}. bölüm: Yayın bulunamadı.")

                except Exception as e:
                    basarisiz.append(no)
                    print(f"{no}. bölüm görev hatası: {e}")

        try:

            gorevler = [
                bolum_gorevi(no, url)
                for no, url in bolumler.items()
            ]

            await asyncio.gather(*gorevler)

        finally:

            await context.close()
            await browser.close()

    # ======================================
    # SONUÇ
    # ======================================

    m3u_olustur(sonuc)

    print("\n================================")
    print("TARAMA TAMAMLANDI")
    print("Arşivden bulunan:", len(bolumler))
    print("Başarılı:", len(sonuc))
    print("Başarısız:", len(basarisiz))
    print("Başarısız bölümler:", sorted(basarisiz))
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())
