
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
LIST_URL = BASE + "/yilan-hikayesi/bolumler"

OUTPUT = "yilan_hikayesi.m3u"
GROUP = "🟪◆ YILAN HİKAYESİ"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

# ==========================================
# BÖLÜM NUMARASI BUL
# ==========================================

def bolum_numarasi(text, href=""):
    text = text.lower()
    href = href.lower()

    if "ilk bölüm" in text or "ilk-bolum" in href:
        return 1

    m = re.search(r"yilan-hikayesi-(\d+)-bolum", href)
    if m:
        return int(m.group(1))

    m = re.search(r"(\d+)\s*\.?\s*bölüm", text)
    if m:
        return int(m.group(1))

    return None


# ==========================================
# SEZON VE BÖLÜM ADI
# ==========================================

def bolum_adi(no):
    if 1 <= no <= 34:
        sezon = 1
        bolum = no
    elif 35 <= no <= 64:
        sezon = 2
        bolum = no - 34
    elif 65 <= no <= 90:
        sezon = 3
        bolum = no - 64
    else:
        sezon = 1
        bolum = no

    return f"YILAN HİKAYESİ S{sezon:02d} E{bolum:02d}"


# ==========================================
# BÖLÜMLERİ TOPLA
# ==========================================

def bolumleri_bul():
    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    for sayfa in range(1, 11):
        url = (
            f"{LIST_URL}"
            f"?orderby=EpisodeNumber+asc&page={sayfa}"
        )

        print(f"\nListe taranıyor: {url}")

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.select("a[href]"):
                href = a.get("href", "")
                baslik = " ".join(
                    a.get_text(" ", strip=True).split()
                )

                if "/yilan-hikayesi/bolumler/" not in href:
                    continue

                no = bolum_numarasi(baslik, href)

                if no is None or not 1 <= no <= 90:
                    continue

                tam_url = urljoin(BASE, href)
                bulunan[no] = tam_url

                print(f"Bulundu: {bolum_adi(no)}")

        except Exception as e:
            print("Liste hatası:", e)

    # İlk bölüm bağlantısı
    if 1 not in bulunan:
        bulunan[1] = (
            BASE +
            "/yilan-hikayesi/bolumler/"
            "yilan-hikayesi-ilk-bolum"
        )

    return dict(sorted(bulunan.items()))


# ==========================================
# M3U8 ADRESİ YAKALA
# ==========================================

async def m3u8_yakala(page_url, browser):
    context = await browser.new_context(
        user_agent=HEADERS["User-Agent"]
    )

    page = await context.new_page()
    yakalanan = []

    def istek_yakala(request):
        adres = request.url.lower()

        if ".m3u8" in adres:
            if request.url not in yakalanan:
                yakalanan.append(request.url)
                print("M3U8 bulundu:", request.url)

    page.on("request", istek_yakala)

    try:
        await page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(12000)

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
        print("Sayfa hatası:", e)

    finally:
        await context.close()

    return yakalanan


# ==========================================
# M3U DOSYASI OLUŞTUR
# ==========================================

def m3u_olustur(sonuc):
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for no, adres in sorted(sonuc.items()):
            baslik = bolum_adi(no)

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
    print("YILAN HİKAYESİ TARAMASI BAŞLADI")
    print("--------------------------------")

    bolumler = bolumleri_bul()

    if not bolumler:
        print("Bölüm bulunamadı.")
        return

    print("\nBulunan bölüm sayısı:", len(bolumler))

    sonuc = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        for no, url in bolumler.items():
            print("\nTaranıyor:", bolum_adi(no))

            adresler = await m3u8_yakala(
                url,
                browser
            )

            if adresler:
                sonuc[no] = adresler[0]
                print("Yayın adresi bulundu.")
            else:
                print("Açık M3U8 bulunamadı.")

        await browser.close()

    if not sonuc:
        print("Hiçbir açık M3U8 adresi yakalanamadı.")
        return

    m3u_olustur(sonuc)


if __name__ == "__main__":
    asyncio.run(main())
