
import asyncio
import re
import requests

from urllib.parse import urljoin
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

# Aynı anda açılacak bölüm sayısı
ES_ZAMANLI = 6

# Sayfa açılma zaman aşımı
SAYFA_TIMEOUT = 15000

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

    bulunan = {
        1: BASE + "/super-baba/1-bolum/izle"
    }

    session = requests.Session()
    session.headers.update(HEADERS)

    print("SÜPER BABA BÖLÜMLERİ TARANIYOR")

    bos_sayfa = 0

    for sayfa in range(1, 21):

        url = f"{LIST_URL}?page={sayfa}"

        print(f"\nListe sayfası: {sayfa}")

        try:
            cevap = session.get(url, timeout=20)
            cevap.raise_for_status()

            soup = BeautifulSoup(
                cevap.text,
                "html.parser"
            )

            yeni = 0

            for a in soup.select("a[href]"):

                href = a.get("href", "")

                match = re.search(
                    r"/super-baba/(\d+)-bolum/izle",
                    href,
                    re.I
                )

                if not match:
                    continue

                no = int(match.group(1))

                if not 1 <= no <= TOPLAM_BOLUM:
                    continue

                tam_url = urljoin(BASE, href)

                if no not in bulunan:
                    bulunan[no] = tam_url
                    yeni += 1

                    print(f"{no}. bölüm bulundu")

            print("Yeni bulunan:", yeni)

            if yeni == 0:
                bos_sayfa += 1
            else:
                bos_sayfa = 0

            # Üç ardışık boş sayfada taramayı bitir
            if bos_sayfa >= 3:
                print("Ardışık boş sayfalar nedeniyle liste taraması durdu.")
                break

        except Exception as e:
            print("Liste hatası:", str(e)[:180])

    # Arşivde görünmeyen numaralar için standart adresler
    # oluşturulur; gerçekten var olup olmadıkları kontrol edilir.
    for no in range(1, TOPLAM_BOLUM + 1):

        if no not in bulunan:
            bulunan[no] = (
                f"{BASE}/super-baba/{no}-bolum/izle"
            )

    bulunan = dict(sorted(bulunan.items()))

    print("\nToplam kontrol edilecek bölüm:", len(bulunan))

    return bulunan


# ==========================================
# TEK BÖLÜMDE M3U8 YAKALA
# ==========================================

async def m3u8_yakala(page_url, context, no):

    page = await context.new_page()
    yakalanan = []

    def istek_yakala(request):

        adres = request.url

        if ".m3u8" in adres.lower():

            if adres not in yakalanan:
                yakalanan.append(adres)

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

        # Oynatıcıya kısa yüklenme süresi
        await page.wait_for_timeout(2500)

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

                    await button.click(timeout=1500)

                    await page.wait_for_timeout(3000)

                    break

            except Exception:
                pass

        if yakalanan:
            return yakalanan

        # Oynatıcıdan son istekleri bekle
        await page.wait_for_timeout(1500)

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

    import os
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

                print(
                    f"\n{no}. bölüm kontrol ediliyor"
                )

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

        try:

            gorevler = [
                bolum_gorevi(no, url)
                for no, url in bolumler.items()
            ]

            await asyncio.gather(*gorevler)

        finally:

            await context.close()
            await browser.close()

    # Sonuçları kaydet
    m3u_olustur(sonuc)

    print("\n================================")
    print("TARAMA TAMAMLANDI")
    print("Başarılı:", len(sonuc))
    print("Başarısız:", len(basarisiz))
    print("Başarısız bölüm numaraları:", sorted(basarisiz))
    print("================================")


if __name__ == "__main__":

    asyncio.run(main())
