
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import re
import json
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse, urljoin

from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - TRT 1 DİZİ OTOMATİK GÜNCELLEYİCİ
# ==================================================

M3U_FILE = "trt1dizi.m3u"

BASE = "https://www.trt1.com.tr"

TARGET_GROUP = "🟪◆  TRT DİZİ 📺⭕"

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
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

DIZILER = [
    {
        "slug": "evlilik-guzeldir",
        "name": "EVLİLİK GÜZELDİR",
        "url": BASE + "/diziler/evlilik-guzeldir",
    },
    {
        "slug": "mehmed-fetihler-sultani",
        "name": "MEHMED FETİHLER SULTANI",
        "url": BASE + "/diziler/mehmed-fetihler-sultani",
    },
    {
        "slug": "gonul-dagi",
        "name": "GÖNÜL DAĞI",
        "url": BASE + "/diziler/gonul-dagi",
    },
    {
        "slug": "tasacak-bu-deniz",
        "name": "TAŞACAK BU DENİZ",
        "url": BASE + "/diziler/tasacak-bu-deniz",
    },
    {
        "slug": "teskilat",
        "name": "TEŞKİLAT",
        "url": BASE + "/diziler/teskilat",
    },
    {
        "slug": "kod-adi-kirlangic",
        "name": "KOD ADI KIRLANGIÇ",
        "url": BASE + "/diziler/kod-adi-kirlangic",
    },
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
            match = re.search(r'group-title="([^"]*)"', line)
            return match.group(1) if match else ""
    return ""


def kanal_adi(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip()
    return ""


def kayit_slug(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            match = re.search(r'tvg-name="([^"]*)"', line)
            if match:
                return match.group(1).lower()
    return ""


def info_kaydi():
    return [
        (
            f'#EXTINF:-1 tvg-name="***** TRT 1 DİZİ *****" '
            f'tvg-logo="{INFO_LOGO}" '
            f'group-title="{TARGET_GROUP}",BİLGİLENDİRME'
        ),
        INFO_URL,
    ]


def dizi_kaydi(dizi):
    ad = dizi["name"]

    if dizi.get("episode"):
        ad += " - " + dizi["episode"]

    if dizi.get("date"):
        ad += " - " + dizi["date"]

    extinf = (
        f'#EXTINF:-1 '
        f'tvg-id="" '
        f'tvg-name="{guvenli(ad)}" '
        f'tvg-logo="{guvenli(dizi.get("logo", ""))}" '
        f'tvg-description="{guvenli(dizi.get("description", ""))}" '
        f'group-title="{TARGET_GROUP}",'
        f'{guvenli(ad)}'
    )

    return [extinf, dizi["url"]]


def dizi_eslesiyor(record, dizi):
    metin = " ".join(record).lower()
    ad = kanal_adi(record).lower()
    tvg = kayit_slug(record)

    slug = dizi["slug"].lower()
    isim = dizi["name"].lower()

    return (
        slug in metin
        or slug in tvg
        or ad.startswith(isim)
        or isim in ad
    )


def bolum_numarasi_bul(path, text=""):
    """
    TRT bağlantılarında karşılaşılabilecek örnekler:
    /diziler/gonul-dagi/232-bolum
    /diziler/gonul-dagi/bolum/232
    /diziler/gonul-dagi/232-bolum/izle
    """

    path = unescape(str(path or "")).lower()
    text = unescape(str(text or "")).lower()

    if "bolum" not in path and "bölüm" not in text:
        return None

    desenler = [
        r"/bolum/(\d+)(?:/|$)",
        r"/(\d+)-bolum(?:/|$)",
        r"/bolumler/(\d+)(?:/|$)",
        r"/(\d+)/bolum(?:/|$)",
    ]

    for desen in desenler:
        match = re.search(desen, path)
        if match:
            return int(match.group(1))

    match = re.search(r"(\d+)\s*\.?\s*bölüm", text, re.I)
    if match:
        return int(match.group(1))

    return None


def m3u_kayitlarini_oku():
    if not os.path.exists(M3U_FILE):
        return ["#EXTM3U"], []

    with open(M3U_FILE, "rb") as file:
        raw = file.read()

    metin = raw.decode("utf-8-sig", errors="replace")
    satirlar = metin.splitlines()

    ilk_extinf = next(
        (
            i for i, satir in enumerate(satirlar)
            if satir.startswith("#EXTINF:")
        ),
        len(satirlar),
    )

    baslik = satirlar[:ilk_extinf]
    govde = satirlar[ilk_extinf:]

    if not baslik:
        baslik = ["#EXTM3U"]

    records = []
    current = []

    for line in govde:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []

        current.append(line)

    if current:
        records.append(current)

    return baslik, records


# ==================================================
# HLS ADRESİ YAKALAMA
# ==================================================

def hls_adresi_mi(url):
    url = temizle(url).replace("\\/", "/")
    return (
        url.startswith("http")
        and ".m3u8" in url.lower()
    )


def html_hls_adreslerini_bul(html):
    html = temizle(html)
    html = html.replace("\\/", "/")
    html = html.replace("\\u0026", "&")
    html = html.replace("&amp;", "&")

    bulunanlar = set()

    desenler = [
        r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?',
        r'https?:\\?/\\?/[^"\'<> ]+?\.m3u8(?:\?[^"\'<> ]*)?',
    ]

    for desen in desenler:
        for adres in re.findall(desen, html, re.I):
            adres = adres.replace("\\/", "/").rstrip("\\,;")
            if hls_adresi_mi(adres):
                bulunanlar.add(adres)

    return bulunanlar


# ==================================================
# EN GÜNCEL BÖLÜMÜ BUL
# ==================================================

async def dizi_bul(browser, dizi):

    page = await browser.new_page(user_agent=UA)
    hls_adresleri = set()

    def yakala(url):
        url = temizle(url)
        url = url.replace("\\/", "/")
        url = url.replace("\\u0026", "&")

        if hls_adresi_mi(url):
            hls_adresleri.add(url)

    page.on("request", lambda request: yakala(request.url))
    page.on("response", lambda response: yakala(response.url))

    try:
        print("\n" + "=" * 55)
        print("[TRT DİZİ]", dizi["name"])
        print("=" * 55)

        denenecek_sayfalar = [
            dizi["url"],
            dizi["url"] + "/bolumler",
        ]

        adaylar = {}

        # --------------------------------------------------
        # BÖLÜM LİNKLERİNİ BUL
        # --------------------------------------------------

        for liste_url in denenecek_sayfalar:

            print("[SAYFA]", liste_url)

            try:
                await page.goto(
                    liste_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                await page.wait_for_timeout(3500)

            except Exception as hata:
                print("[SAYFA AÇILAMADI]", str(hata))
                continue

            try:
                links = await page.locator("a[href]").evaluate_all(
                    """
                    els => els.map(a => ({
                        url: a.href,
                        text: (
                            a.innerText ||
                            a.textContent ||
                            ''
                        ).trim()
                    }))
                    """
                )
            except Exception:
                links = []

            for item in links:
                link = temizle(item.get("url"))
                text = temizle(item.get("text"))

                path = urlparse(link).path.lower()

                if dizi["slug"] not in path:
                    continue

                bolum_no = bolum_numarasi_bul(path, text)

                if bolum_no is None:
                    continue

                if bolum_no not in adaylar:
                    adaylar[bolum_no] = link

            # Sayfa HTML içindeki bağlantıları da kontrol et
            try:
                html = await page.content()

                html = html.replace("\\/", "/")
                html = html.replace("\\u0026", "&")

                url_matches = re.findall(
                    r'https?://[^\s"\'<>]+',
                    html,
                    re.I,
                )

                for link in url_matches:
                    link = link.rstrip("\\,;")
                    path = urlparse(link).path.lower()

                    if dizi["slug"] not in path:
                        continue

                    bolum_no = bolum_numarasi_bul(path)

                    if bolum_no is not None:
                        adaylar.setdefault(bolum_no, link)

            except Exception:
                pass

            if adaylar:
                break

        if not adaylar:
            print("[BÖLÜM BULUNAMADI]", dizi["name"])
            return None

        son_bolum = max(adaylar)
        hedef_url = adaylar[son_bolum]

        print("[SON BÖLÜM]", son_bolum)
        print("[BÖLÜM SAYFASI]", hedef_url)

        # --------------------------------------------------
        # SON BÖLÜM SAYFASINI AÇ
        # --------------------------------------------------

        await page.goto(
            hedef_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await page.wait_for_timeout(5000)

        # --------------------------------------------------
        # LOGO
        # --------------------------------------------------

        logo = ""

        logo_selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
        ]

        for selector in logo_selectors:
            try:
                logo = await page.locator(
                    selector
                ).first.get_attribute("content")

                if logo:
                    logo = urljoin(BASE, logo)
                    break

            except Exception:
                pass

        if not logo:
            try:
                logo = await page.locator(
                    "img"
                ).first.get_attribute("src")

                if logo:
                    logo = urljoin(BASE, logo)

            except Exception:
                pass

        if not logo:
            logo = BASE + "/favicon.ico"

        # --------------------------------------------------
        # AÇIKLAMA
        # --------------------------------------------------

        description = ""

        for selector in [
            'meta[name="description"]',
            'meta[property="og:description"]',
        ]:
            try:
                description = (
                    await page.locator(
                        selector
                    ).first.get_attribute("content")
                    or ""
                )

                if description:
                    break

            except Exception:
                pass

        # --------------------------------------------------
        # YAYIN TARİHİ
        # --------------------------------------------------

        tarih = ""

        for selector in [
            'meta[property="article:published_time"]',
            'meta[property="og:updated_time"]',
            'meta[name="date"]',
        ]:
            try:
                tarih = (
                    await page.locator(
                        selector
                    ).first.get_attribute("content")
                    or ""
                )

                if tarih:
                    break

            except Exception:
                pass

        if tarih:
            tarih = tarih[:10]

        # --------------------------------------------------
        # HLS ADRESLERİNİ TARA
        # --------------------------------------------------

        for tur in range(3):

            print("[HLS TARAMA]", tur + 1)

            try:
                html = await page.content()
                hls_adresleri.update(
                    html_hls_adreslerini_bul(html)
                )
            except Exception:
                pass

            # Video oynatmayı dene
            try:
                await page.locator(
                    "video"
                ).first.evaluate(
                    "(video) => video.play()"
                )
            except Exception:
                pass

            # Player oynat butonlarını dene
            selectors = [
                ".jw-icon-play",
                ".vjs-big-play-button",
                ".plyr__control--overlaid",
                "button[aria-label*='Oynat']",
                "button[title*='Oynat']",
                ".play-button",
                "[class*='play-button']",
            ]

            for selector in selectors:
                try:
                    button = page.locator(selector).first

                    if await button.count():
                        await button.click(
                            timeout=2500,
                            force=True,
                        )

                        await page.wait_for_timeout(3000)
                        break

                except Exception:
                    pass

            await page.wait_for_timeout(4000)

            try:
                html = await page.content()
                hls_adresleri.update(
                    html_hls_adreslerini_bul(html)
                )
            except Exception:
                pass

            if hls_adresleri:
                break

        if not hls_adresleri:
            print("[HLS BULUNAMADI]", dizi["name"])
            return None

        # --------------------------------------------------
        # EN UYGUN HLS ADRESİNİ SEÇ
        # --------------------------------------------------

        def hls_puanla(url):
            alt = url.lower()

            puan = 0

            if "master.m3u8" in alt:
                puan += 100

            if "playlist.m3u8" in alt:
                puan += 80

            if "index.m3u8" in alt:
                puan += 60

            if "manifest" in alt:
                puan += 20

            return puan

        sirali = sorted(
            hls_adresleri,
            key=lambda url: (
                -hls_puanla(url),
                len(url),
            ),
        )

        sonuc_url = sirali[0]

        print("[HLS BULUNDU]", sonuc_url)
        print("[LOGO]", logo)
        print("[TARİH]", tarih or "Bulunamadı")

        return {
            "slug": dizi["slug"],
            "name": dizi["name"],
            "episode": f"{son_bolum}. BÖLÜM",
            "date": tarih,
            "logo": logo,
            "description": description,
            "url": sonuc_url,
        }

    except Exception as hata:
        print("[DİZİ HATASI]", dizi["name"], str(hata))
        return None

    finally:
        await page.close()


# ==================================================
# TRT M3U DOSYASINI GÜNCELLE
# ==================================================

def listeyi_guncelle(yeni_diziler):

    baslik, eski_records = m3u_kayitlarini_oku()

    # Önceki TRT bilgi kaydını koru
    eski_info = None

    for record in eski_records:
        if (
            grup_bul(record) == TARGET_GROUP
            and "BİLGİLENDİRME" in kanal_adi(record).upper()
        ):
            eski_info = record
            break

    if eski_info is None:
        eski_info = info_kaydi()

    # Başarılı bulunan diziler
    yeni_sluglar = {
        dizi["slug"]: dizi
        for dizi in yeni_diziler
    }

    # Başarısız dizilerin eski kayıtlarını koru
    korunan_eski_diziler = []

    for dizi in DIZILER:

        if dizi["slug"] in yeni_sluglar:
            continue

        for record in eski_records:

            if grup_bul(record) != TARGET_GROUP:
                continue

            if dizi_eslesiyor(record, dizi):
                korunan_eski_diziler.append(record)
                print(
                    "[ESKİ KAYIT KORUNDU]",
                    dizi["name"],
                )
                break

    # TRT grubundaki bilinmeyen kayıtları koru
    bilinen_kayitlar = []

    for record in eski_records:

        if grup_bul(record) != TARGET_GROUP:
            continue

        if "BİLGİLENDİRME" in kanal_adi(record).upper():
            continue

        bilinen_dizi_mi = any(
            dizi_eslesiyor(record, dizi)
            for dizi in DIZILER
        )

        if not bilinen_dizi_mi:
            bilinen_kayitlar.append(record)

    # Yeni TRT kayıtlarını hazırla
    yeni_records = [eski_info]

    for dizi in DIZILER:

        if dizi["slug"] in yeni_sluglar:
            yeni_records.append(
                dizi_kaydi(yeni_sluglar[dizi["slug"]])
            )

    # Başarısız dizilerin eski kayıtlarını ekle
    yeni_records.extend(korunan_eski_diziler)

    # Bilinmeyen TRT kayıtlarını da koru
    yeni_records.extend(bilinen_kayitlar)

    # Aynı kayıtları tekrarlama
    temiz_records = []
    gorulen = set()

    for record in yeni_records:
        anahtar = "\n".join(record)

        if anahtar in gorulen:
            continue

        gorulen.add(anahtar)
        temiz_records.append(record)

    # Hiçbir dizi bulunmadı ve eski kayıt da yoksa yazma
    if not yeni_diziler and not korunan_eski_diziler:
        print("[HATA] Yeni veya korunacak TRT dizisi bulunamadı.")
        print("[BİLGİ] Dosya değiştirilmedi.")
        return False

    # Yedek al
    if os.path.exists(M3U_FILE):
        shutil.copy2(
            M3U_FILE,
            M3U_FILE + ".bak",
        )

    # Dosyayı yaz
    sonuc_satirlari = list(baslik)

    for record in temiz_records:
        sonuc_satirlari.extend(record)

    yeni_metin = "\n".join(sonuc_satirlari) + "\n"

    temp_file = M3U_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(yeni_metin)

    os.replace(temp_file, M3U_FILE)

    print("\n" + "=" * 55)
    print("TRT 1 DİZİ GÜNCELLEMESİ TAMAMLANDI")
    print("=" * 55)
    print("Dosya:", M3U_FILE)
    print("Grup:", TARGET_GROUP)
    print("Başarılı güncellenen:", len(yeni_diziler))
    print("Eski kaydı korunan:", len(korunan_eski_diziler))
    print("Toplam TRT kaydı:", len(temiz_records) - 1)
    print("Bilgilendirme kaydı: VAR")
    print("Yedek:", M3U_FILE + ".bak")
    print("=" * 55)

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    print("=" * 55)
    print("MIRTI68 - TRT 1 DİZİ BOTU")
    print("=" * 55)

    yeni_diziler = []

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        try:
            for dizi in DIZILER:

                sonuc = await dizi_bul(
                    browser,
                    dizi,
                )

                if sonuc:
                    yeni_diziler.append(sonuc)
                else:
                    print(
                        "[ATLANDI] Eski kayıt varsa korunacak:",
                        dizi["name"],
                    )

        finally:
            await browser.close()

    print("\nBULUNAN DİZİ SAYISI:", len(yeni_diziler))

    listeyi_g
