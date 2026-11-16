
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
LIST_URL = BASE + "/hayat-bilgisi/bolumler"

OUTPUT = "hayat_bilgisi.m3u"
GROUP = "🟪◆ HAYAT BİLGİSİ"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

# Sezonların bölüm başlangıç ve bitişleri
SEZONLAR = [
    (1, 19, 1),
    (20, 59, 2),
    (60, 98, 3),
    (99, 137, 4),
]


# ==========================================
# SEZON / BÖLÜM ADI
# ==========================================

def bolum_adi(no):
    for baslangic, bitis, sezon in SEZONLAR:
        if baslangic <= no <= bitis:
            bolum = no - baslangic + 1
            return f"HAYAT BİLGİSİ S{sezon:02d} E{bolum:02d}"

    return f"HAYAT BİLGİSİ BÖLÜM {no}"


# ==========================================
# BÖLÜM NUMARASI BUL
# ==========================================

def bolum_numarasi(text, href=""):
    text = text.lower()
    href = href.lower()

    if "ilk bölüm" in text or "ilk-bolum" in href:
        return 1

    desenler = [
        r"hayat-bilgisi-(\d+)-bolum",
        r"hayat-bilgisi-(\d+)\.bolum",
        r"(\d+)-bolum",
        r"(\d+)\s*\.?\s*bölüm",
    ]

    for desen in desenler:
        m = re.search(desen, href if "href" in desen else text)

        if m:
            return int(m.group(1))

    return None


# ==========================================
# BÖLÜMLERİ TOPLA
# ==========================================

def bolumleri_bul():
    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    for sayfa in range(1, 16):
        url = (
            f"{LIST_URL}"
            f"?orderby=EpisodeNumber+asc&page={sayfa}"
        )

        print(f"\nListe taranıyor: {url}")

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            yeni = 0

            for a in soup.select("a[href]"):
                href = a.get("href", "")
                baslik = " ".join(
                    a.get_text(" ", strip=True).split()
                )

                if "/hayat-bilgisi/bolumler/" not in href:
                    continue

                no = bolum_numarasi(baslik, href)

                if no is None or not 1 <= no <= 137:
                    continue

                tam_url = urljoin(BASE, href)

                if no not in bulunan:
                    bulunan[no] = tam_url
                    yeni += 1
                    print(f"Bulundu: {bolum_adi(no)}")

            print("Yeni bölüm:", yeni)

            # Yeni bölüm bulunmuyorsa sonraki sayfalarda
            # da sonuç çıkmayabilir; taramayı bitir.
            if yeni == 0 and sayfa > 1:
                break

        except Exception as e:
            print("Liste hatası:", e)

    # İlk bölümün bağlantısını garanti et
    if 1 not in bulunan:
        bulunan[1] = (
            BASE +
            "/hayat-bilgisi/bolumler/"
            "hayat-bilgisi-ilk-bolum"
        )

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
        print("Oynatıcı hatası:", e)

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
    print("HAYAT BİLGİSİ TARAMASI BAŞLADI")
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
        print("\nHiçbir açık M3U8 adresi yakalanamadı.")
        return

    m3u_olustur(sonuc)


if __name__ == "__main__":
    asyncio.run(main())
