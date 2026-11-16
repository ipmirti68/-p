
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

    # İlk bölüm özellikle ekleniyor
    bulunan[1] = BASE + "/super-baba/1-bolum/izle"

    for sayfa in range(1, 21):
        url = f"{LIST_URL}?page={sayfa}"

        print("\nListe sayfası:", sayfa)

        try:
            cevap = session.get(url, timeout=30)
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

        except Exception as e:
            print("Liste hatası:", e)

    # Arşiv bağlantılarından bulunamayan bölümleri
    # standart ATV bölüm adresiyle ekle.
    # Sayfanın gerçekten mevcut olup olmadığı aşağıda
    # tarayıcı tarafından kontrol edilecek.
    for no in range(1, TOPLAM_BOLUM + 1):
        if no not in bulunan:
            bulunan[no] = (
                f"{BASE}/super-baba/{no}-bolum/izle"
            )

    return dict(sorted(bulunan.items()))


# ==========================================
# M3U8 ADRESİNİ YAKALA
# ==========================================

async def m3u8_yakala(page_url, browser):
    context = await browser.new_context(
        user_agent=HEADERS["User-Agent"]
    )

    page = await context.new_page()
    yakalanan = []

    def istek_yakala(request):
        adres = request.url

        if ".m3u8" in adres.lower():
            if adres not in yakalanan:
                yakalanan.append(adres)
                print("M3U8 bulundu:", adres)

    page.on("request", istek_yakala)

    try:
        response = await page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=45000
        )

        if response and response.status >= 400:
            print("Sayfa HTTP hatası:", response.status)
            return []

        # Oynatıcının yüklenmesini bekle
        await page.wait_for_timeout(7000)

        # Normal oynatma düğmesini dene
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

                if await button.is_visible(timeout=1000):
                    await button.click(timeout=2500)
                    await page.wait_for_timeout(7000)
                    break

            except Exception:
                pass

        # Son isteklerin tamamlanması için bekle
        await page.wait_for_timeout(3000)

    except Exception as e:
        print("Sayfa açılamadı:", str(e)[:180])

    finally:
        await context.close()

    return yakalanan


# ==========================================
# M3U DOSYASI
# ==========================================

def m3u_olustur(sonuc):
    with open(OUTPUT, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for no, adres in sorted(sonuc.items()):

            baslik = f"SÜPER BABA {no:03d}. BÖLÜM"

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",'
                f'{baslik}\n'
            )

            f.write(adres + "\n")

    print("\n================================")
    print("M3U DOSYASI OLUŞTURULDU")
    print("Dosya:", OUTPUT)
    print("Bulunan yayın:", len(sonuc))
    print("================================")


# ==========================================
# ANA PROGRAM
# ==========================================

async def main():

    print("SÜPER BABA TARAMASI BAŞLADI")
    print("--------------------------------")

    bolumler = bolumleri_bul()

    print("\nTaranacak bölüm:", len(bolumler))

    sonuc = {}

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        for no, url in bolumler.items():

            print(
                f"\n{no}/{len(bolumler)} "
                f"- SÜPER BABA {no:03d}. BÖLÜM"
            )

            adresler = await m3u8_yakala(
                url,
                browser
            )

            if adresler:
                sonuc[no] = adresler[0]
                print("Yayın adresi kaydedildi.")
            else:
                print("Açık M3U8 bulunamadı.")

        await browser.close()

    if not sonuc:
        print("\nHiçbir M3U8 adresi yakalanamadı.")
        return

    m3u_olustur(sonuc)


if __name__ == "__main__":
    asyncio.run(main())
