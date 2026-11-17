
import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# KANAL D DİZİ OTOMATİK GÜNCELLEYİCİ
# ==================================================

BASE = "https://www.kanald.com.tr"
M3U_FILE = "mirti68.m3u"

SHOW_GROUP = "🟪◆ SHOWTV DİZİLERİ ⭕"
KANAL_GROUP = "🟪◆  KANAL D DİZİ 📺⭕"

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)

DIZILER = [
    {
        "slug": "susuz-yaz",
        "name": "SUSUZ YAZ",
        "type": "fragman",
        "description": "Susuz Yaz dizisinin en yeni fragmanı."
    },
    {
        "slug": "karakuyu",
        "name": "KARAKUYU",
        "type": "fragman",
        "description": "Karakuyu dizisinin en yeni fragmanı."
    },
    {
        "slug": "uzak-sehir",
        "name": "UZAK ŞEHİR",
        "type": "bolum",
        "description": "Uzak Şehir dizisinin en son yayınlanan bölümü."
    },
    {
        "slug": "haysiyet",
        "name": "HAYSİYET",
        "type": "bolum",
        "description": "Haysiyet dizisinin en son yayınlanan bölümü."
    },
    {
        "slug": "guller-ve-gunahlar",
        "name": "GÜLLER VE GÜNAHLAR",
        "type": "bolum",
        "description": "Güller ve Günahlar dizisinin en son yayınlanan bölümü."
    },
    {
        "slug": "daha-17",
        "name": "DAHA 17",
        "type": "bolum",
        "description": "Daha 17 dizisinin en son yayınlanan bölümü."
    }
]


# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def attr(value):
    return str(value or "").replace('"', "%22").replace("\n", " ").strip()


def get_group(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', line)
            return m.group(1) if m else ""
    return ""


def get_channel_name(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip()
    return ""


def make_info_record():
    return [
        f'#EXTINF:-1 tvg-name="***** TURKIYE 4K *****" '
        f'tvg-logo="{INFO_LOGO}" '
        f'group-title="{KANAL_GROUP}",BİLGİLENDİRME',
        INFO_URL
    ]


def make_dizi_record(dizi):
    return [
        f'#EXTINF:-1 tvg-id="" '
        f'tvg-name="{attr(dizi["name"])}" '
        f'tvg-logo="{attr(dizi["logo"])}" '
        f'tvg-description="{attr(dizi["description"])}" '
        f'group-title="{KANAL_GROUP}",'
        f'{attr(dizi["name"])} - '
        f'{"FRAGMAN" if dizi["type"] == "fragman" else "SON BÖLÜM"}',
        dizi["url"]
    ]


# ==================================================
# VİDEO VE LOGO ADRESLERİNİ BUL
# ==================================================

async def video_bul(browser, dizi):

    context = await browser.new_context(
        user_agent=UA,
        ignore_https_errors=True
    )

    page = await context.new_page()
    bulunan = set()

    def yakala(url):
        url = unescape(url).replace("\\/", "/")
        url = url.replace("\\u0026", "&")

        if (
            "kanaldvod.duhnet.tv" in url
            and ".m3u8" in url.lower()
        ):
            bulunan.add(url)

    page.on("request", lambda r: yakala(r.url))
    page.on("response", lambda r: yakala(r.url))

    slug = dizi["slug"]
    tip = dizi["type"]

    sayfalar = [
        f"{BASE}/{slug}/{ 'fragmanlar' if tip == 'fragman' else 'bolumler'}",
        f"{BASE}/{slug}"
    ]

    hedef = None
    logo = ""
    aciklama = dizi["description"]

    try:
        for liste_url in sayfalar:

            print("\n[SAYFA]", liste_url)

            try:
                await page.goto(
                    liste_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await page.wait_for_timeout(3000)

            except Exception:
                continue

            links = await page.locator("a[href]").evaluate_all(
                """els => els.map(a => a.href).filter(Boolean)"""
            )

            adaylar = []

            for link in links:
                path = urlparse(link).path.lower()

                if slug not in path:
                    continue

                if tip == "fragman" and "fragman" not in path:
                    continue

                if tip == "bolum" and "bolum" not in path:
                    continue

                if link.rstrip("/") != liste_url.rstrip("/"):
                    if link not in adaylar:
                        adaylar.append(link)

            if adaylar:
                # Bölümlerde numarası en yüksek olanı önceliklendir.
                if tip == "bolum":
                    def bolum_no(url):
                        nums = re.findall(r'\d+', url)
                        return int(nums[-1]) if nums else 0

                    adaylar.sort(
                        key=bolum_no,
                        reverse=True
                    )

                hedef = adaylar[0]
                break

            # Sayfanın kendisinde video bulunabilir.
            hedef = liste_url

        if not hedef:
            print("[HATA] Video sayfası bulunamadı:", dizi["name"])
            return None

        print("[VİDEO SAYFASI]", hedef)

        await page.goto(
            hedef,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(6000)

        # Logo ve açıklama
        for selector in [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]'
        ]:
            try:
                value = await page.locator(selector).first.get_attribute("content")
                if value:
                    logo = value
                    break
            except Exception:
                pass

        try:
            value = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content")

            if value:
                aciklama = value.strip()
        except Exception:
            pass

        # Sayfadaki gömülü HLS adreslerini tara
        html = await page.content()

        html = (
            unescape(html)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        matches = re.findall(
            r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
            html,
            re.I
        )

        for url in matches:
            yakala(url)

        # Video oynatmayı tetikle
        for selector in [
            ".jw-icon-play",
            ".vjs-big-play-button",
            ".plyr__control--overlaid",
            "button[aria-label*='Oynat']"
        ]:
            try:
                button = page.locator(selector).first

                if await button.count():
                    await button.click(
                        timeout=2500,
                        force=True
                    )
                    await page.wait_for_timeout(7000)
                    break
            except Exception:
                pass

        # Video elementini de oynatmayı dene
        try:
            await page.locator("video").first.evaluate(
                "(v) => v.play()"
            )
            await page.wait_for_timeout(7000)
        except Exception:
            pass

        # Son ağ isteklerini tara
        html = await page.content()

        html = (
            unescape(html)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        for url in re.findall(
            r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
            html,
            re.I
        ):
            yakala(url)

        if not bulunan:
            print("[BULUNAMADI]", dizi["name"])
            return None

        adresler = sorted(
            bulunan,
            key=lambda x: (
                "playlist.m3u8" not in x.lower(),
                len(x)
            )
        )

        sonuc = adresler[0]

        if not logo:
            logo = BASE + "/favicon.ico"

        print("[HLS BULUNDU]", dizi["name"])
        print(sonuc)

        return {
            "name": dizi["name"],
            "type": dizi["type"],
            "description": aciklama,
            "logo": logo,
            "url": sonuc
        }

    except Exception as e:
        print("[HATA]", dizi["name"], str(e))
        return None

    finally:
        await context.close()


# ==================================================
# M3U DOSYASINI KORUYARAK DÜZENLE
# ==================================================

def listeyi_guncelle(yeni_diziler):

    if not os.path.exists(M3U_FILE):
        print("[HATA] M3U dosyası bulunamadı!")
        return False

    raw = open(M3U_FILE, "rb").read()
    bom = raw.startswith(codecs.BOM_UTF8)

    metin = raw.decode("utf-8-sig")

    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()

    # EPG ve ana başlık korunur
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

    # SHOWTV bilgilendirme kaydını bul
    show_index = None

    for i, record in enumerate(records):

        if (
            get_group(record) == SHOW_GROUP
            and "BİLGİLENDİRME" in get_channel_name(record).upper()
        ):
            show_index = i
            break

    if show_index is None:
        print("[HATA] SHOWTV bilgilendirme grubu bulunamadı.")
        print("Dosya değiştirilmedi.")
        return False

    # Mevcut Kanal D bilgilendirme kaydını koru
    info_record = None

    for record in records:

        if (
            get_group(record) == KANAL_GROUP
            and "BİLGİLENDİRME" in get_channel_name(record).upper()
        ):
            info_record = record
            break

    if info_record is None:
        info_record = make_info_record()

    # Yalnızca Kanal D grubunun eski kayıtlarını çıkar
    diger_gruplar = [
        record for record in records
        if get_group(record) != KANAL_GROUP
    ]

    # SHOWTV bilgilendirme kaydının yeni konumunu bul
    show_index = None

    for i, record in enumerate(diger_gruplar):

        if (
            get_group(record) == SHOW_GROUP
            and "BİLGİLENDİRME" in get_channel_name(record).upper()
        ):
            show_index = i
            break

    if show_index is None:
        print("[HATA] Yerleştirme noktası kayboldu.")
        return False

    # Yeni Kanal D grubu
    kanal_d_records = [info_record]

    for dizi in yeni_diziler:
        kanal_d_records.append(make_dizi_record(dizi))

    # SHOWTV bilgilendirmesinden hemen sonra yerleştir
    yeni_records = (
        diger_gruplar[:show_index + 1]
        + kanal_d_records
        + diger_gruplar[show_index + 1:]
    )

    # Dosya yedeği al
    shutil.copy2(
        M3U_FILE,
        M3U_FILE + ".bak"
    )

    sonuc = list(baslik)

    for record in yeni_records:
        sonuc.extend(record)

    yeni_metin = newline.join(sonuc) + newline

    temp_file = M3U_FILE + ".tmp"

    with open(temp_file, "wb") as f:
        encoding = "utf-8-sig" if bom else "utf-8"
        f.write(yeni_metin.encode(encoding))

    os.replace(temp_file, M3U_FILE)

    print("\n====================================")
    print("KANAL D DİZİ GÜNCELLEMESİ TAMAMLANDI")
    print("====================================")
    print("Konum: SHOWTV bilgilendirmesinin hemen sonrası")
    print("Bilgilendirme videosu: KORUNDU")
    print("EPG başlığı: KORUNDU")
    print("Diğer gruplar: KORUNDU")
    print("Dizi sayısı:", len(yeni_diziler))
    print("Yedek:", M3U_FILE + ".bak")
    print("====================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
        return

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        yeni_diziler = []

        try:
            for dizi in DIZILER:

                sonuc = await video_bul(
                    browser,
                    dizi
                )

                if sonuc is None:
                    print("\nGÜNCELLEME İPTAL EDİLDİ!")
                    print("Mevcut M3U dosyasına dokunulmadı.")
                    return

                yeni_diziler.append(sonuc)

        finally:
            await browser.close()

        if len(yeni_diziler) == len(DIZILER):
            listeyi_guncelle(yeni_diziler)


if __name__ == "__main__":
    asyncio.run(main())
