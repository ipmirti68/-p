
import os
import re
import asyncio
import tempfile
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# ==================================================
# AYARLAR
# ==================================================

BASE = "https://www.kanald.com.tr"
M3U_FILE = "mirti68.m3u"
GROUP = "🟪◆  KANAL D DİZİ 📺⭕"

DIZILER = [
    {
        "name": "Susuz Yaz - Fragman",
        "url": BASE + "/susuz-yaz/fragmanlar",
        "kind": "fragman",
        "slug": "susuz-yaz"
    },
    {
        "name": "Karakuyu - Fragman",
        "url": BASE + "/karakuyu/fragmanlar",
        "kind": "fragman",
        "slug": "karakuyu"
    },
    {
        "name": "Uzak Şehir - Son Bölüm",
        "url": BASE + "/uzak-sehir",
        "kind": "bolum",
        "slug": "uzak-sehir"
    },
    {
        "name": "Haysiyet - Son Bölüm",
        "url": BASE + "/haysiyet",
        "kind": "bolum",
        "slug": "haysiyet"
    },
    {
        "name": "Güller ve Günahlar - Son Bölüm",
        "url": BASE + "/guller-ve-gunahlar",
        "kind": "bolum",
        "slug": "guller-ve-gunahlar"
    },
    {
        "name": "Daha 17 - Son Bölüm",
        "url": BASE + "/daha-17",
        "kind": "bolum",
        "slug": "daha-17"
    }
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
    )
}


# ==================================================
# VİDEO ADRESİ BULMA
# ==================================================

async def video_adresi_bul(browser, dizi):

    page = await browser.new_page(
        user_agent=HEADERS["User-Agent"]
    )

    bulunanlar = set()

    def adres_yakala(url):
        url = url.replace("&amp;", "&")

        if (
            "kanaldvod.duhnet.tv" in url
            and (
                ".m3u8" in url.lower()
                or ".smil/playlist.m3u8" in url.lower()
            )
        ):
            bulunanlar.add(url)

    page.on(
        "request",
        lambda request: adres_yakala(request.url)
    )

    page.on(
        "response",
        lambda response: adres_yakala(response.url)
    )

    try:
        print(f"\n[AÇILIYOR] {dizi['name']}")

        await page.goto(
            dizi["url"],
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        # Son fragman veya bölüm sayfasına geç
        if dizi["kind"] == "fragman":
            selector = "a[href*='/fragmanlar/']"
        else:
            selector = "a[href*='/bolumler/']"

        links = await page.locator(selector).evaluate_all(
            """els => els.map(a => a.href).filter(Boolean)"""
        )

        hedef = None

        for link in links:
            if (
                dizi["slug"] in link
                and link.rstrip("/") != dizi["url"].rstrip("/")
            ):
                hedef = link
                break

        if hedef:
            print("[VİDEO SAYFASI]", hedef)

            await page.goto(
                hedef,
                wait_until="domcontentloaded",
                timeout=60000
            )

            await page.wait_for_timeout(5000)

        # Sayfadaki olası doğrudan adresleri tara
        html = await page.content()

        for match in re.findall(
            r'https?://[^"\'\s<>]+',
            html
        ):
            adres_yakala(match)

        # Video oynatmayı tetikle
        for selector in [
            ".jw-icon-play",
            ".vjs-big-play-button",
            ".plyr__control--overlaid",
            "button[aria-label*='Oynat']",
            "video"
        ]:
            try:
                element = page.locator(selector).first

                if await element.count():
                    await element.click(
                        timeout=2000,
                        force=True
                    )
                    await page.wait_for_timeout(7000)
                    break

            except Exception:
                pass

        html = await page.content()

        for match in re.findall(
            r'https?://[^"\'\s<>]+',
            html
        ):
            adres_yakala(match)

        if not bulunanlar:
            print("[BULUNAMADI]", dizi["name"])
            return None

        # Öncelik doğrudan HLS playlist adresinde
        sirali = sorted(
            bulunanlar,
            key=lambda x: (
                "playlist.m3u8" not in x.lower(),
                len(x)
            )
        )

        sonuc = sirali[0]

        print("[BULUNDU]", sonuc)

        return sonuc

    except Exception as e:
        print("[HATA]", dizi["name"], str(e))
        return None

    finally:
        await page.close()


# ==================================================
# M3U DOSYASINI KORUYARAK GÜNCELLE
# ==================================================

def listeyi_guncelle(yeni_kayitlar):

    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
        return False

    with open(
        M3U_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:
        satirlar = f.read().splitlines()

    # EPG ve üst başlık satırlarını koru
    ilk_extinf = next(
        (
            i for i, line in enumerate(satirlar)
            if line.startswith("#EXTINF:")
        ),
        len(satirlar)
    )

    baslik = satirlar[:ilk_extinf]
    govde = satirlar[ilk_extinf:]

    # Her EXTINF kaydını kendi URL ve metadata satırlarıyla tut
    kayitlar = []
    mevcut = []

    for line in govde:

        if line.startswith("#EXTINF:") and mevcut:
            kayitlar.append(mevcut)
            mevcut = []

        mevcut.append(line)

    if mevcut:
        kayitlar.append(mevcut)

    # Yalnızca bizim grubumuzu kaldır.
    # Diğer grupların tüm satırları aynen kalır.
    grup_regex = re.compile(
        r'group-title="([^"]*)"'
    )

    korunan = []

    for kayit in kayitlar:

        extinf = next(
            (
                x for x in kayit
                if x.startswith("#EXTINF:")
            ),
            ""
        )

        match = grup_regex.search(extinf)

        if match and match.group(1) == GROUP:
            continue

        korunan.extend(kayit)

    # Yeni kayıtlar
    yeni_satirlar = []

    for dizi in yeni_kayitlar:

        yeni_satirlar.append(
            f'#EXTINF:-1 tvg-id="" tvg-name="{dizi["name"]}" '
            f'tvg-logo="" group-title="{GROUP}",{dizi["name"]}'
        )

        yeni_satirlar.append(dizi["url"])

    # Yeni grubu en üstte tut
    sonuc = (
        baslik
        + yeni_satirlar
        + korunan
    )

    # Önce geçici dosyaya yaz, sonra atomik değiştir
    fd, temp_path = tempfile.mkstemp(
        suffix=".m3u",
        dir=os.path.dirname(os.path.abspath(M3U_FILE))
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f:
            f.write("\n".join(sonuc) + "\n")

        os.replace(temp_path, M3U_FILE)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print("\n================================")
    print("KANAL D GRUBU GÜNCELLENDİ")
    print("Diğer gruplar korundu.")
    print("EPG başlığı korundu.")
    print("Toplam kayıt:", len(yeni_kayitlar))
    print("================================")

    return True


# ==================================================
# ANA İŞLEM
# ==================================================

async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        yeni_kayitlar = []

        try:
            for dizi in DIZILER:

                adres = await video_adresi_bul(
                    browser,
                    dizi
                )

                if not adres:
                    print(
                        "\n[GÜNCELLEME İPTAL] "
                        "Eksik adres var. Mevcut liste korunuyor."
                    )
                    return

                yeni_kayitlar.append({
                    "name": dizi["name"],
                    "url": adres
                })

        finally:
            await browser.close()

        if len(yeni_kayitlar) == len(DIZILER):
            listeyi_guncelle(yeni_kayitlar)


if __name__ == "__main__":
    asyncio.run(main())
