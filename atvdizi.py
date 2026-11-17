
import asyncio
import os
import re
import shutil
import codecs
import time
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - ATV DİZİ OTOMATİK GÜNCELLEYİCİ
# BAĞIMSIZ SÜRÜM
# ==================================================

M3U_FILE = "atvdizi.m3u"
BASE = "https://www.atv.com.tr"

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

MAX_EPISODES = 3

DIZILER = [
    {
        "slug": "alti-ustu-istanbul",
        "name": "ALTı ÜSTÜ İSTANBUL",
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


def hls_duzelt(url):
    return (
        temizle(url)
        .replace("\\/", "/")
        .replace("\\u0026", "&")
        .replace("&amp;", "&")
        .strip(" \t\r\n\"'")
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
        (
            f'#EXTINF:-1 tvg-name="***** ATV DİZİ *****" '
            f'tvg-logo="{INFO_LOGO}" '
            f'group-title="{TARGET_GROUP}",BİLGİLENDİRME'
        ),
        INFO_URL
    ]


def dizi_kaydi(d):
    ad = d["name"] + " - " + d["episode"]

    if d.get("date"):
        ad += " - " + d["date"]

    extinf = (
        f'#EXTINF:-1 '
        f'tvg-id="" '
        f'tvg-name="{guvenli(ad)}" '
        f'tvg-logo="{guvenli(d.get("logo", ""))}" '
        f'tvg-description="{guvenli(d.get("description", ""))}" '
        f'group-title="{TARGET_GROUP}",'
        f'{guvenli(ad)}'
    )

    return [extinf, d["url"]]


def html_hls_bul(html):
    html = (
        temizle(html)
        .replace("\\/", "/")
        .replace("\\u0026", "&")
        .replace("&amp;", "&")
    )

    adresler = re.findall(
        r'https?://[^"\'<>\s\\]+?\.m3u8'
        r'(?:\?[^"\'<>\s\\]*)?',
        html,
        re.I
    )

    return [
        hls_duzelt(x)
        for x in adresler
        if ".m3u8" in x.lower()
    ]


def en_iyi_hls(adresler):
    adresler = list(set(adresler))

    if not adresler:
        return None

    adresler.sort(
        key=lambda x: (
            "master.m3u8" not in x.lower(),
            -len(x)
        )
    )

    return adresler[0]


# ==================================================
# ESKİ M3U KAYITLARINI OKU
# ==================================================

def eski_listeyi_oku():

    if not os.path.exists(M3U_FILE):
        return ["#EXTM3U"], [], False, "\n"

    with open(M3U_FILE, "rb") as f:
        raw = f.read()

    bom = raw.startswith(codecs.BOM_UTF8)

    metin = raw.decode(
        "utf-8-sig",
        errors="replace"
    )

    newline = "\r\n" if "\r\n" in metin else "\n"

    satirlar = metin.splitlines()

    ilk_extinf = next(
        (
            i for i, s in enumerate(satirlar)
            if s.startswith("#EXTINF:")
        ),
        len(satirlar)
    )

    baslik = satirlar[:ilk_extinf]

    if not baslik:
        baslik = ["#EXTM3U"]

    govde = satirlar[ilk_extinf:]

    records = []
    current = []

    for line in govde:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []

        current.append(line)

    if current:
        records.append(current)

    return baslik, records, bom, newline


# ==================================================
# DİZİ KAYDINI ESKİ KAYITLA EŞLEŞTİR
# ==================================================

def dizi_eslesiyor(record, dizi):

    if grup_bul(record) != TARGET_GROUP:
        return False

    ad = kanal_adi(record).lower()
    hedef = dizi["name"].lower()

    ad = ad.replace("ı", "i")
    hedef = hedef.replace("ı", "i")

    return hedef in ad


def eski_dizi_kayitlari(records, dizi):
    return [
        r for r in records
        if dizi_eslesiyor(r, dizi)
    ]


def eski_bolum_no(record):

    ad = kanal_adi(record)

    m = re.search(
        r'(\d+)\s*\.?\s*BÖLÜM',
        ad,
        re.I
    )

    if m:
        return int(m.group(1))

    return None


# ==================================================
# BÖLÜM LİNKLERİNİ BUL
# ==================================================

async def bolumleri_bul(page, dizi):

    liste_url = dizi["url"].rstrip("/") + "/bolumler"

    print("[BÖLÜM LİSTESİ]", liste_url)

    try:
        await page.goto(
            liste_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

    except Exception as e:
        print("[LİSTE HATASI]", str(e))
        return []

    try:
        links = await page.locator(
            "a[href]"
        ).evaluate_all(
            """els => els.map(a => ({
                url: a.href,
                text: (a.innerText || a.textContent || '').trim()
            }))"""
        )

    except Exception as e:
        print("[LINK HATASI]", str(e))
        return []

    adaylar = {}

    for item in links:

        link = item.get("url", "")

        if not link:
            continue

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
        adaylar[bolum_no] = link

    sirali = sorted(
        adaylar.items(),
        key=lambda x: x[0],
        reverse=True
    )

    return sirali[:MAX_EPISODES]


# ==================================================
# BÖLÜM SAYFASINDAN HLS BUL
# ==================================================

async def bolum_tara(browser, dizi, bolum_no, bolum_url):

    page = await browser.new_page(
        user_agent=UA
    )

    hls_adresleri = set()

    def yakala(url):
        url = hls_duzelt(url)

        if (
            url.startswith("http")
            and ".m3u8" in url.lower()
        ):
            hls_adresleri.add(url)

    def request_yakala(request):
        try:
            yakala(request.url)
        except Exception:
            pass

    def response_yakala(response):
        try:
            yakala(response.url)
        except Exception:
            pass

    page.on("request", request_yakala)
    page.on("response", response_yakala)

    logo = ""
    description = ""
    tarih = ""

    try:

        print(
            "\n[BÖLÜM]",
            dizi["name"],
            bolum_no
        )

        await page.goto(
            bolum_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        # LOGO
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

        # AÇIKLAMA
        try:
            description = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content") or ""
        except Exception:
            pass

        # TARİH
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

        # İLK HTML TARAMASI
        html = await page.content()

        for adres in html_hls_bul(html):
            yakala(adres)

        # OYNATMA DENEMESİ
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
                        timeout=3000,
                        force=True
                    )

                    await page.wait_for_timeout(6000)
                    break

            except Exception:
                pass

        # VIDEO PLAY
        try:
            await page.locator(
                "video"
            ).first.evaluate(
                "(v) => v.play()"
            )

            await page.wait_for_timeout(6000)

        except Exception:
            pass

        # SON HTML TARAMASI
        html = await page.content()

        for adres in html_hls_bul(html):
            yakala(adres)

        sonuc = en_iyi_hls(hls_adresleri)

        if not sonuc:
            print("[HLS BULUNAMADI]", bolum_no)
            return None

        print("[HLS BULUNDU]", sonuc)

        return {
            "name": dizi["name"],
            "episode": f"{bolum_no}. BÖLÜM",
            "episode_no": bolum_no,
            "date": tarih,
            "logo": logo,
            "description": description,
            "url": sonuc
        }

    except Exception as e:

        print(
            "[BÖLÜM HATASI]",
            bolum_no,
            str(e)
        )

        return None

    finally:
        await page.close()


# ==================================================
# DİZİNİN SON 3 BÖLÜMÜNÜ TARA
# ==================================================

async def dizi_bul(browser, dizi):

    print("\n====================================")
    print("[ATV DİZİ]", dizi["name"])
    print("====================================")

    page = await browser.new_page(
        user_agent=UA
    )

    try:
        bolumler = await bolumleri_bul(
            page,
            dizi
        )

    finally:
        await page.close()

    if not bolumler:
        print("[BÖLÜM BULUNAMADI]", dizi["name"])
        return []

    print(
        "[SON BÖLÜMLER]",
        [no for no, url in bolumler]
    )

    sonuclar = []

    for bolum_no, bolum_url in bolumler:

        sonuc = await bolum_tara(
            browser,
            dizi,
            bolum_no,
            bolum_url
        )

        if sonuc:
            sonuclar.append(sonuc)

        await asyncio.sleep(1)

    sonuclar.sort(
        key=lambda x: x["episode_no"],
        reverse=True
    )

    return sonuclar[:MAX_EPISODES]


# ==================================================
# M3U DOSYASINI GÜNCELLE
# ==================================================

def listeyi_guncelle(yeni_sonuclar):

    baslik, records, bom, newline = eski_listeyi_oku()

    # Yeni sonuç bulunan dizileri belirle
    basarili = {
        dizi["slug"]: yeni_sonuclar.get(dizi["slug"], [])
        for dizi in DIZILER
    }

    if not any(basarili.values()):
        print("\n[İPTAL] Yeni HLS bulunamadı.")
        print("Mevcut dosya değiştirilmedi.")
        return False

    # Eski ATV kayıtları dışındaki kayıtlar korunur
    diger_kayitlar = [
        r for r in records
        if grup_bul(r) != TARGET_GROUP
    ]

    # Eski ATV kayıtlarını topla
    eski_atv = [
        r for r in records
        if grup_bul(r) == TARGET_GROUP
    ]

    # Bilgilendirme kaydını koru
    info = None

    for record in eski_atv:
        if "BİLGİLENDİRME" in kanal_adi(record).upper():
            info = record
            break

    if info is None:
        info = info_kaydi()

    yeni_atv = [info]

    for dizi in DIZILER:

        slug = dizi["slug"]
        yeni = basarili[slug]

        if yeni:

            # Başarılı taranan dizinin yeni bölümlerini ekle
            for sonuc in yeni:
                yeni_atv.append(
                    dizi_kaydi(sonuc)
                )

            print(
                "[GÜNCELLENDİ]",
                dizi["name"],
                len(yeni),
                "bölüm"
            )

        else:

            # Başarısız dizinin eski kayıtlarını koru
            eski = eski_dizi_kayitlari(
                records,
                dizi
            )

            yeni_atv.extend(eski)

            print(
                "[ESKİ KAYIT KORUNDU]",
                dizi["name"],
                len(eski),
                "kayıt"
            )

    # Yedek al
    if os.path.exists(M3U_FILE):
        shutil.copy2(
            M3U_FILE,
            M3U_FILE + ".bak"
        )

    # Bağımsız dosya: sadece ATV kayıtları
    son_records = yeni_atv

    sonuc_satirlari = list(baslik)

    for record in son_records:
        sonuc_satirlari.extend(record)

    yeni_metin = newline.join(sonuc_satirlari) + newline

    encoding = "utf-8-sig" if bom else "utf-8"

    temp = M3U_FILE + ".tmp"

    with open(temp, "wb") as f:
        f.write(
            yeni_metin.encode(encoding)
        )

    os.replace(temp, M3U_FILE)

    print("\n====================================")
    print("ATV DİZİ GÜNCELLEME TAMAMLANDI")
    print("====================================")
    print("Dosya:", M3U_FILE)
    print("Grup:", TARGET_GROUP)
    print("Dizi sayısı:", len(DIZILER))
    print("Son bölüm limiti:", MAX_EPISODES)
    print("Bilgilendirme: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("====================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    print("====================================")
    print("MIRTI68 - ATV DİZİ BOTU")
    print("====================================")

    yeni_sonuclar = {}

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        try:

            for dizi in DIZILER:

                sonuc = await dizi_bul(
                    browser,
                    dizi
                )

                yeni_sonuclar[dizi["slug"]] = sonuc

        finally:
            await browser.close()

    toplam = sum(
        len(x)
        for x in yeni_sonuclar.values()
    )

    print("\nTOPLAM BULUNAN BÖLÜM:", toplam)

    listeyi_guncelle(
        yeni_sonuclar
    )


if __name__ == "__main__":
    asyncio.run(main())
    
