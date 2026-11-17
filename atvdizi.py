
import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# ATV DİZİ OTOMATİK GÜNCELLEYİCİ
# ==================================================

M3U_FILE = "atvdizi.m3u"

BASE = "https://www.atv.com.tr"

SHOW_GROUP = "🟪◆ SHOW DİZİ 📺⭕"
TARGET_GROUP = "🟪◆  ATV DİZİ 📺⭕"

INFO_URL = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/-p/main/bilgi.mp4"
)

INFO_LOGO = (
    "https://www.freepnglogos.com/uploads/"
    "turk-bayragi-png/turk-bayragi-hareketli-"
    "bayrak-gif-turkey-wavy-flag-png-27.png"
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)

DIZILER = [
    {
        "slug": "alti-ustu-istanbul",
        "name": "ALTI ÜSTÜ İSTANBUL",
        "url": BASE + "/alti-ustu-istanbul"
    },
    {
        "slug": "gunesin-dogdugu-yer",
        "name": "GÜNEŞİN DOĞDUĞU YER",
        "url": BASE + "/gunesin-dogdugu-yer"
    }
]


# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def temizle(value):
    return unescape(str(value or "")).strip()


def guvenli(value):
    return (
        temizle(value)
        .replace('"', "'")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def grup_bul(record):

    for line in record:

        if line.startswith("#EXTINF:"):

            m = re.search(
                r'group-title="([^"]*)"',
                line
            )

            return m.group(1) if m else ""

    return ""


def kanal_adi(record):

    for line in record:

        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip()

    return ""


def info_kaydi():

    return [
        f'#EXTINF:-1 tvg-name="***** ATV DİZİ *****" '
        f'tvg-logo="{INFO_LOGO}" '
        f'group-title="{TARGET_GROUP}",BİLGİLENDİRME',
        INFO_URL
    ]


def dizi_kaydi(d):

    ad = d["name"]

    if d.get("episode"):
        ad += " - " + d["episode"]

    if d.get("date"):
        ad += " - " + d["date"]

    extinf = (
        f'#EXTINF:-1 '
        f'tvg-id="" '
        f'tvg-name="{guvenli(ad)}" '
        f'tvg-logo="{guvenli(d["logo"])}" '
        f'tvg-description="{guvenli(d["description"])}" '
        f'group-title="{TARGET_GROUP}",'
        f'{guvenli(ad)}'
    )

    return [
        extinf,
        d["url"]
    ]


# ==================================================
# EN GÜNCEL BÖLÜMÜ BUL
# ==================================================

async def dizi_bul(browser, dizi):

    page = await browser.new_page(
        user_agent=UA
    )

    hls_adresleri = set()

    def yakala(url):

        url = (
            temizle(url)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        if (
            url.startswith("http")
            and ".m3u8" in url.lower()
        ):
            hls_adresleri.add(url)

    page.on(
        "request",
        lambda r: yakala(r.url)
    )

    page.on(
        "response",
        lambda r: yakala(r.url)
    )

    try:

        print("\n================================")
        print("[DİZİ]", dizi["name"])
        print("================================")

        # Bölümler sayfası
        liste_url = (
            dizi["url"] + "/bolumler"
        )

        await page.goto(
            liste_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        # Bölüm bağlantılarını topla
        links = await page.locator(
            "a[href]"
        ).evaluate_all(
            """els => els.map(a => ({
                url: a.href,
                text: (a.innerText || a.textContent || '').trim()
            }))"""
        )

        adaylar = {}

        for item in links:

            link = item["url"]
            text = item["text"]

            path = urlparse(link).path.lower()

            if dizi["slug"] not in path:
                continue

            match = re.search(
                r'/(\d+)-bolum(?:/izle)?/?$',
                path
            )

            if not match:
                continue

            bolum_no = int(match.group(1))

            if bolum_no not in adaylar:
                adaylar[bolum_no] = link

        if not adaylar:

            print(
                "[HATA] Bölüm bağlantısı bulunamadı:",
                dizi["name"]
            )

            return None

        # En yüksek bölüm numarasını seç
        son_bolum = max(adaylar)

        hedef = adaylar[son_bolum]

        print("[SON BÖLÜM]", son_bolum)
        print("[SAYFA]", hedef)

        # Son bölüm sayfası
        await page.goto(
            hedef,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(6000)

        # Logo
        logo = ""

        for selector in [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]'
        ]:

            try:

                logo = await page.locator(
                    selector
                ).first.get_attribute("content")

                if logo:
                    break

            except Exception:
                pass

        if not logo:
            logo = BASE + "/favicon.ico"

        # Açıklama
        description = ""

        try:

            description = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content") or ""

        except Exception:
            pass

        # Yayın tarihi
        tarih = ""

        for selector in [
            'meta[property="article:published_time"]',
            'meta[property="og:updated_time"]'
        ]:

            try:

                tarih = await page.locator(
                    selector
                ).first.get_attribute("content") or ""

                if tarih:
                    break

            except Exception:
                pass

        if tarih:
            tarih = tarih[:10]

        # Sayfadaki HLS adreslerini tara
        html = await page.content()

        html = (
            temizle(html)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        for adres in re.findall(
            r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
            html,
            re.I
        ):
            yakala(adres)

        # Oynatmayı dene
        for selector in [
            ".jw-icon-play",
            ".vjs-big-play-button",
            ".plyr__control--overlaid",
            "button[aria-label*='Oynat']"
        ]:

            try:

                button = page.locator(
                    selector
                ).first

                if await button.count():

                    await button.click(
                        timeout=2500,
                        force=True
                    )

                    await page.wait_for_timeout(7000)
                    break

            except Exception:
                pass

        try:

            await page.locator(
                "video"
            ).first.evaluate(
                "(v) => v.play()"
            )

            await page.wait_for_timeout(7000)

        except Exception:
            pass

        # Son istekleri tekrar kontrol et
        html = await page.content()

        html = (
            temizle(html)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        for adres in re.findall(
            r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
            html,
            re.I
        ):
            yakala(adres)

        if not hls_adresleri:

            print(
                "[HLS BULUNAMADI]",
                dizi["name"]
            )

            return None

        # Master playlist öncelikli
        sirali = sorted(
            hls_adresleri,
            key=lambda x: (
                "master.m3u8" not in x.lower(),
                len(x)
            )
        )

        sonuc = sirali[0]

        print("[HLS BULUNDU]", sonuc)
        print("[LOGO]", logo)
        print("[TARİH]", tarih)

        return {
            "name": dizi["name"],
            "episode": f"{son_bolum}. BÖLÜM",
            "date": tarih,
            "logo": logo,
            "description": description,
            "url": sonuc
        }

    except Exception as e:

        print(
            "[HATA]",
            dizi["name"],
            str(e)
        )

        return None

    finally:
        await page.close()


# ==================================================
# M3U DOSYASINI KORUYARAK GÜNCELLE
# ==================================================

def listeyi_guncelle(yeni_diziler):

    if not os.path.exists(M3U_FILE):

        print("[HATA] mirti68.m3u bulunamadı!")
        return False

    raw = open(M3U_FILE, "rb").read()

    bom = raw.startswith(codecs.BOM_UTF8)

    metin = raw.decode("utf-8-sig")

    newline = (
        "\r\n" if "\r\n" in metin else "\n"
    )

    satirlar = metin.splitlines()

    # EPG başlığı korunur
    ilk_extinf = next(
        (
            i for i, s in enumerate(satirlar)
            if s.startswith("#EXTINF:")
        ),
        len(satirlar)
    )

    baslik = satirlar[:ilk_extinf]
    govde = satirlar[ilk_extinf:]

    # M3U kayıtlarını ayır
    records = []
    current = []

    for line in govde:

        if line.startswith("#EXTINF:") and current:

            records.append(current)
            current = []

        current.append(line)

    if current:
        records.append(current)

    # SHOW DİZİ grubunun son kaydını bul
    anchor = None

    for i, record in enumerate(records):

        if grup_bul(record) == SHOW_GROUP:
            anchor = i

    if anchor is None:

        print(
            "[HATA] SHOW DİZİ grubu bulunamadı!"
        )

        print("Dosya değiştirilmedi.")
        return False

    # Önceki ATV bilgilendirme kaydını koru
    info = None

    for record in records:

        if (
            grup_bul(record) == TARGET_GROUP
            and "BİLGİLENDİRME" in kanal_adi(record).upper()
        ):

            info = record
            break

    if info is None:
        info = info_kaydi()

    # Sadece eski ATV grubunu kaldır
    digerleri = [
        r for r in records
        if grup_bul(r) != TARGET_GROUP
    ]

    # SHOW DİZİ grubunun son konumunu tekrar bul
    anchor = None

    for i, record in enumerate(digerleri):

        if grup_bul(record) == SHOW_GROUP:
            anchor = i

    if anchor is None:
        return False

    # Yeni ATV kayıtları
    yeni_kayitlar = [info]

    for dizi in yeni_diziler:

        yeni_kayitlar.append(
            dizi_kaydi(dizi)
        )

    # SHOW DİZİ grubunun hemen arkasına ekle
    son_records = (
        digerleri[:anchor + 1]
        + yeni_kayitlar
        + digerleri[anchor + 1:]
    )

    # Yedek al
    shutil.copy2(
        M3U_FILE,
        M3U_FILE + ".bak"
    )

    sonuc = list(baslik)

    for record in son_records:
        sonuc.extend(record)

    yeni_metin = (
        newline.join(sonuc) + newline
    )

    temp = M3U_FILE + ".tmp"

    encoding = (
        "utf-8-sig" if bom else "utf-8"
    )

    with open(temp, "wb") as f:
        f.write(yeni_metin.encode(encoding))

    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("ATV DİZİ GÜNCELLEME TAMAMLANDI")
    print("===================================")
    print("Grup:", TARGET_GROUP)
    print("Konum: SHOW DİZİ grubunun hemen sonrası")
    print("Dizi sayısı:", len(yeni_diziler))
    print("Logo: EKLENDİ")
    print("Açıklama: EKLENDİ")
    print("Tarih: BULUNDUĞUNDA EKLENDİ")
    print("EPG başlığı: KORUNDU")
    print("Diğer gruplar: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("===================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    if not os.path.exists(M3U_FILE):

        print("[HATA] M3U dosyası bulunamadı!")
        return

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        yeni_diziler = []

        try:

            for dizi in DIZILER:

                sonuc = await dizi_bul(
                    browser,
                    dizi
                )

                if sonuc is None:

                    print("\nGÜNCELLEME İPTAL EDİLDİ!")
                    print("Mevcut liste korunuyor.")
                    return

                yeni_diziler.append(sonuc)

        finally:
            await browser.close()

        if len(yeni_diziler) == len(DIZILER):

            listeyi_guncelle(
                yeni_diziler
            )


if __name__ == "__main__":
    asyncio.run(main())
