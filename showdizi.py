
import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# SHOW TV DİZİ OTOMATİK GÜNCELLEYİCİ
# ==================================================

M3U_FILE = "mirti68.m3u"

BASE = "https://www.showtv.com.tr"

SHOW_GROUP = "🟪◆ SHOWTV DİZİLERİ ⭕"
TARGET_GROUP = "🟪◆ SHOW DİZİ 📺⭕"

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
        "slug": "sevdan-bir-ates",
        "name": "SEVDAN BİR ATEŞ"
    },
    {
        "slug": "kizilcik-serbeti",
        "name": "KIZILCIK ŞERBETİ"
    },
    {
        "slug": "muhtemel-ask",
        "name": "MUHTEMEL AŞK"
    },
    {
        "slug": "menekse",
        "name": "MENEKŞE"
    },
    {
        "slug": "cevher",
        "name": "CEVHER"
    }
]


# ==================================================
# YARDIMCILAR
# ==================================================

def temizle(text):
    return unescape(str(text or "")).strip()


def grup_bul(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', line)
            return m.group(1) if m else ""
    return ""


def kanal_adi(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip()
    return ""


def info_kaydi():
    return [
        f'#EXTINF:-1 tvg-name="***** SHOW TV DİZİ *****" '
        f'tvg-logo="{INFO_LOGO}" '
        f'group-title="{TARGET_GROUP}",BİLGİLENDİRME',
        INFO_URL
    ]


def dizi_kaydi(d):
    tarih = d.get("date", "")
    bolum = d.get("episode", "")
    aciklama = d.get("description", "")

    gorunen_ad = d["name"]

    if bolum:
        gorunen_ad += " - " + bolum

    if tarih:
        gorunen_ad += " - " + tarih

    extinf = (
        f'#EXTINF:-1 '
        f'tvg-id="" '
        f'tvg-name="{gorunen_ad}" '
        f'tvg-logo="{d["logo"]}" '
        f'tvg-description="{aciklama}" '
        f'group-title="{TARGET_GROUP}",'
        f'{gorunen_ad}'
    )

    return [extinf, d["url"]]


# ==================================================
# DİZİ SAYFASINDAN SON BÖLÜMÜ BUL
# ==================================================

async def dizi_bul(browser, dizi):

    url = (
        f"{BASE}/dizi/tanitim/"
        f"{dizi['slug']}"
    )

    page = await browser.new_page(
        user_agent=UA
    )

    hls_adresleri = set()

    def adres_yakala(adres):

        adres = (
            temizle(adres)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        if (
            ".m3u8" in adres.lower()
            and adres.startswith("http")
        ):
            hls_adresleri.add(adres)

    page.on(
        "request",
        lambda r: adres_yakala(r.url)
    )

    page.on(
        "response",
        lambda r: adres_yakala(r.url)
    )

    try:

        print("\n[DİZİ]", dizi["name"])

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        # Dizi afişini al
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
        aciklama = ""

        try:
            aciklama = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content") or ""
        except Exception:
            pass

        # Sayfadaki son bölüm bağlantılarını bul
        links = await page.locator(
            "a[href]"
        ).evaluate_all(
            """els => els.map(a => ({
                url: a.href,
                text: (a.innerText || a.textContent || '').trim()
            }))"""
        )

        adaylar = []

        for item in links:

            link = item["url"]
            text = item["text"]

            if not link or not text:
                continue

            if "fragman" in text.lower():
                continue

            if not re.search(
                r'\\b\\d+\\s*\\.??\\s*bölüm\\b',
                text,
                re.I
            ):
                continue

            if link.rstrip("/") == url.rstrip("/"):
                continue

            if link not in [x["url"] for x in adaylar]:
                adaylar.append(item)

        # Dizi henüz başlamamış olabilir
        if not adaylar:

            print(
                "[BÖLÜM BEKLENİYOR]",
                dizi["name"]
            )

            return {
                "unavailable": True,
                "name": dizi["name"]
            }

        # Sayfada ilk gösterilen en yeni bölüm
        hedef = adaylar[0]["url"]
        bolum_adi = adaylar[0]["text"]

        print("[SON BÖLÜM]", hedef)

        await page.goto(
            hedef,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        # Bölüm sayfasından güncel açıklama
        try:
            desc = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content")

            if desc:
                aciklama = desc

        except Exception:
            pass

        # Yayın tarihini bul
        tarih = ""

        try:

            tarih = await page.locator(
                'meta[property="article:published_time"]'
            ).first.get_attribute("content") or ""

        except Exception:
            pass

        if not tarih:
            try:
                tarih = await page.locator(
                    'meta[property="og:updated_time"]'
                ).first.get_attribute("content") or ""
            except Exception:
                pass

        if tarih:
            tarih = tarih[:10]

        # Sayfa HTML içindeki HLS adresleri
        html = await page.content()

        html = (
            unescape(html)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        for adres in re.findall(
            r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
            html,
            re.I
        ):
            adres_yakala(adres)

        # Oynatmayı tetikle
        for selector in [
            ".jw-icon-play",
            ".vjs-big-play-button",
            ".plyr__control--overlaid",
            "button[aria-label*='Oynat']"
        ]:

            try:

                element = page.locator(
                    selector
                ).first

                if await element.count():

                    await element.click(
                        timeout=2500,
                        force=True
                    )

                    await page.wait_for_timeout(7000)
                    break

            except Exception:
                pass

        # Video elementini oynatmayı dene
        try:

            await page.locator(
                "video"
            ).first.evaluate(
                "(v) => v.play()"
            )

            await page.wait_for_timeout(7000)

        except Exception:
            pass

        # Son ağ isteklerini tekrar tara
        html = await page.content()

        html = (
            unescape(html)
            .replace("\\/", "/")
            .replace("\\u0026", "&")
        )

        for adres in re.findall(
            r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
            html,
            re.I
        ):
            adres_yakala(adres)

        if not hls_adresleri:

            print(
                "[HLS BULUNAMADI]",
                dizi["name"]
            )

            return None

        sirali = sorted(
            hls_adresleri,
            key=lambda x: (
                "master.m3u8" not in x.lower(),
                len(x)
            )
        )

        print("[HLS BULUNDU]", sirali[0])

        return {
            "name": dizi["name"],
            "logo": logo,
            "description": aciklama,
            "episode": bolum_adi,
            "date": tarih,
            "url": sirali[0]
        }

    except Exception as e:

        print("[HATA]", dizi["name"], str(e))
        return None

    finally:
        await page.close()


# ==================================================
# M3U KAYITLARINI KORUYARAK YERLEŞTİR
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

    # EPG ve başlık satırlarını koru
    ilk_extinf = next(
        (
            i for i, s in enumerate(satirlar)
            if s.startswith("#EXTINF:")
        ),
        len(satirlar)
    )

    baslik = satirlar[:ilk_extinf]
    govde = satirlar[ilk_extinf:]

    # Kayıtları ayır
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
    anchor = None

    for i, record in enumerate(records):

        if (
            grup_bul(record) == SHOW_GROUP
            and "BİLGİLENDİRME" in kanal_adi(record).upper()
        ):

            anchor = i
            break

    if anchor is None:

        print(
            "[HATA] SHOWTV bilgilendirme kaydı bulunamadı!"
        )

        print("Dosya değiştirilmedi.")
        return False

    # Önceki SHOW DİZİ bilgilendirmesini koru
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

    # Yalnızca hedef grubun eski kayıtlarını çıkar
    digerleri = [
        r for r in records
        if grup_bul(r) != TARGET_GROUP
    ]

    # Yeni anchor konumunu tekrar bul
    anchor = None

    for i, record in enumerate(digerleri):

        if (
            grup_bul(record) == SHOW_GROUP
            and "BİLGİLENDİRME" in kanal_adi(record).upper()
        ):

            anchor = i
            break

    if anchor is None:
        return False

    # Yeni kayıtları oluştur
    yeni_kayitlar = [info]

    for dizi in yeni_diziler:
        yeni_kayitlar.append(
            dizi_kaydi(dizi)
        )

    # SHOWTV info kaydının hemen arkasına yerleştir
    son_records = (
        digerleri[:anchor + 1]
        + yeni_kayitlar
        + digerleri[anchor + 1:]
    )

    # Yedek oluştur
    shutil.copy2(
        M3U_FILE,
        M3U_FILE + ".bak"
    )

    sonuc = list(baslik)

    for record in son_records:
        sonuc.extend(record)

    yeni_metin = newline.join(sonuc) + newline

    temp = M3U_FILE + ".tmp"

    encoding = (
        "utf-8-sig" if bom else "utf-8"
    )

    with open(temp, "wb") as f:
        f.write(yeni_metin.encode(encoding))

    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("SHOW DİZİ GÜNCELLEME TAMAMLANDI")
    print("===================================")
    print("Grup:", TARGET_GROUP)
    print("Yer: SHOWTV bilgilendirmesinin sonrası")
    print("Dizi sayısı:", len(yeni_diziler))
    print("Bilgilendirme: KORUNDU")
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

                    print("\nGÜNCELLEME İPTAL!")
                    print("Mevcut liste korunuyor.")
                    return

                if sonuc.get("unavailable"):
                    continue

                yeni_diziler.append(sonuc)

        finally:
            await browser.close()

        if not yeni_diziler:

            print("Henüz yayınlanmış bölüm bulunamadı.")
            return

        listeyi_guncelle(yeni_diziler)


if __name__ == "__main__":
    asyncio.run(main())
