
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
LIST_URL = BASE + "/esref-ruya/bolumler"

OUTPUT = "esref_ruya.m3u"
GROUP = "🟪◆ EŞREF RÜYA ⭕"

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

    if "ilk bölüm" in text or "ilk-bolum" in text:
        return 1

    m = re.search(r"(\d+)\s*\.?\s*bölüm", text)
    if m:
        return int(m.group(1))

    m = re.search(r"esref-ruya-(\d+)-bolum", href)
    if m:
        return int(m.group(1))

    return None


# ==========================================
# BÖLÜM LİSTESİNİ TOPLA
# ==========================================

def bolumleri_bul():
    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    for sayfa in range(1, 21):
        url = f"{LIST_URL}?page={sayfa}"

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

                if "/esref-ruya/bolumler/" not in href:
                    continue

                no = bolum_numarasi(baslik, href)

                if no is None:
                    continue

                tam_url = urljoin(BASE, href)

                bulunan[no] = tam_url

                if no == 1:
                    print("İlk bölüm bulundu:", tam_url)
                else:
                    print(f"{no}. bölüm bulundu")

        except Exception as e:
            print("Liste hatası:", e)

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

        # Oynatıcıdaki normal oynatma düğmesini dene
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

            if no == 1:
                baslik = "EŞREF RÜYA İLK BÖLÜM"
            else:
                baslik = f"EŞREF RÜYA {no}. BÖLÜM"

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",'
                f'{baslik}\n'
            )

            f.write(adres + "\n")

    print("\n================================")
    print("M3U DOSYASI OLUŞTURULDU")
    print("Dosya:", OUTPUT)
    print("Toplam yayın:", len(sonuc))
    print("================================")


# ==========================================
# ANA PROGRAM
# ==========================================

async def main():

    print("EŞREF RÜYA BÖLÜMLERİ TARANIYOR")
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

            if no == 1:
                print("\nİLK BÖLÜM TARANIYOR")
            else:
                print(f"\n{no}. BÖLÜM TARANIYOR")

            adresler = await m3u8_yakala(
                url,
                browser
            )

            if adresler:
                # İlk bulunan açık HLS adresi
                sonuc[no] = adresler[0]
                print("Yayın adresi bulundu.")
            else:
                print("Açık M3U8 adresi bulunamadı.")

        await browser.close()

    if not sonuc:
        print("\nHiçbir açık M3U8 adresi bulunamadı.")
        return

    m3u_olustur(sonuc)


if __name__ == "__main__":
    asyncio.run(main())
