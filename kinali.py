
import asyncio
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==========================================
# AYARLAR
# ==========================================

BASE = "https://www.kanald.com.tr"
LIST_URL = BASE + "/kinali-kar"
OUTPUT = "kinali_kar.m3u"

GROUP = "🟪◆ KINALI KAR ⭕"

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

    m = re.search(r"(\d+)\s*\.?\s*bölüm", text)
    if m:
        return int(m.group(1))

    m = re.search(r"kinali-kar-(\d+)-bolum", href)
    if m:
        return int(m.group(1))

    m = re.search(r"/(\d+)-bolum", href)
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

    try:
        r = session.get(LIST_URL, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            baslik = " ".join(a.get_text(" ", strip=True).split())

            if "/kinali-kar/bolumler/" not in href:
                continue

            no = bolum_numarasi(baslik, href)

            if no is None:
                continue

            tam_url = urljoin(BASE, href)
            bulunan[no] = tam_url

            print(f"{no}. bölüm bulundu: {tam_url}")

        # İlk bölüm bağlantısını ayrıca garanti et
        ilk_bolum = BASE + "/kinali-kar/bolumler/ilk-bolum"

        if 1 not in bulunan:
            bulunan[1] = ilk_bolum
            print("İlk bölüm bağlantısı eklendi.")

    except Exception as e:
        print("Bölüm listesi alınamadı:", e)

    return dict(sorted(bulunan.items()))


# ==========================================
# M3U8 YAKALA
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
                print("M3U8 isteği:", adres)

    page.on("request", istek_yakala)

    try:
        await page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(12000)

        # Normal oynatma düğmesini dene
        for selector in [
            "button[aria-label*='Oynat']",
            "button[aria-label*='Play']",
            ".vjs-big-play-button",
            ".jw-icon-play"
        ]:
            try:
                button = page.locator(selector).first

                if await button.is_visible(timeout=1500):
                    await button.click(timeout=3000)
                    await page.wait_for_timeout(8000)
                    break

            except Exception:
                pass

    except Exception as e:
        print("Oynatıcı sayfası hatası:", e)

    finally:
        await context.close()

    return yakalanan


# ==========================================
# M3U OLUŞTUR
# ==========================================

def m3u_olustur(sonuc):
    with open(OUTPUT, "w", encoding="utf-8") as f:
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

    print("\n================================")
    print("M3U DOSYASI OLUŞTURULDU")
    print("Dosya:", OUTPUT)
    print("Bulunan yayın:", len(sonuc))
    print("================================")


# ==========================================
# ANA PROGRAM
# ==========================================

async def main():
    bolumler = bolumleri_bul()

    if not bolumler:
        print("Bölüm bulunamadı.")
        return

    print("\nToplam bölüm:", len(bolumler))

    sonuc = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for no, url in bolumler.items():

            print(f"\n{no}. BÖLÜM AÇILIYOR")

            adresler = await m3u8_yakala(url, browser)

            if adresler:
                sonuc[no] = adresler[0]
                print("Yayın adresi bulundu.")
            else:
                print("Açık M3U8 isteği bulunamadı.")

        await browser.close()

    if not sonuc:
        print("\nM3U8 adresi bulunamadı.")
        return

    m3u_olustur(sonuc)


if __name__ == "__main__":
    asyncio.run(main())
