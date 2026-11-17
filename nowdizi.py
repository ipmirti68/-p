
import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - NOW TV DİZİ OTOMATİK GÜNCELLEYİCİ
# BAĞIMSIZ SÜRÜM
# ==================================================

M3U_FILE = "nowdizi.m3u"

BASE = "https://www.nowtv.com.tr"

TARGET_GROUP = "🟪◆  NOW DİZİ 📺⭕"

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

# ==================================================
# DİZİLER - VERDİĞİNİZ ADRESLER KORUNDU
# ==================================================

DIZILER = [
    {
        "page": "https://www.nowtv.com.tr/Halef-Koklerin-Cagrisi/izle",
        "name": "HALEF"
    },
    {
        "page": "https://www.nowtv.com.tr/Yeralti/izle",
        "name": "YERALTİ"
    },
    {
        "page": "https://www.nowtv.com.tr/Sevdam-Karadeniz/izle",
        "name": "SEVDAM KARADENİZ"
    },
    {
        "page": "https://www.nowtv.com.tr/Omur-Usta/izle",
        "name": "ÖMÜR USTA"
    },
    {
        "page": "https://www.nowtv.com.tr/Adana-Ayazi/izle",
        "name": "ADANA AYAZI"
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


def normalize(value):
    value = temizle(value).lower()
    value = value.replace("ı", "i")

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    ).strip()


def hls_duzelt(adres):
    return (
        temizle(adres)
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
            f'#EXTINF:-1 tvg-name="***** NOW DİZİ *****" '
            f'tvg-logo="{INFO_LOGO}" '
            f'group-title="{TARGET_GROUP}",BİLGİLENDİRME'
        ),
        INFO_URL
    ]


def dizi_kaydi(d):
    gorunen = d["name"]

    if d.get("episode"):
        gorunen += " - " + d["episode"]

    if d.get("date"):
        gorunen += " - " + d["date"]

    extinf = (
        f'#EXTINF:-1 '
        f'tvg-id="" '
        f'tvg-name="{guvenli(gorunen)}" '
        f'tvg-logo="{guvenli(d.get("logo", ""))}" '
        f'tvg-description="{guvenli(d.get("description", ""))}" '
        f'group-title="{TARGET_GROUP}",'
        f'{guvenli(gorunen)}'
    )

    return [
        extinf,
        d["url"]
    ]


def hls_html_bul(html):
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

    sonuc = []

    for adres in adresler:
        adres = hls_duzelt(adres)

        if (
            adres.startswith("http")
            and ".m3u8" in adres.lower()
        ):
            low = adres.lower()

            if any(x in low for x in [
                "fragman",
                "teaser",
                "tanitim"
            ]):
                continue

            sonuc.append(adres)

    return sonuc


def hls_sec(adresler):
    adresler = list(set(adresler))

    if not adresler:
        return None

    def skor(adres):
        low = adres.lower()

        if "smil/playlist.m3u8" in low:
            return 0

        if "master.m3u8" in low:
            return 1

        return 2

    adresler.sort(
        key=lambda x: (skor(x), len(x))
    )

    return adresler[0]


# ==================================================
# ESKİ KAYITLARI TANIMA
# ==================================================

def dizi_eslesiyor(record, dizi):

    if grup_bul(record) != TARGET_GROUP:
        return False

    ad = normalize(kanal_adi(record))
    hedef = normalize(dizi["name"])

    return ad.startswith(hedef)


def eski_dizi_kayitlari(records, dizi):
    return [
        r for r in records
        if dizi_eslesiyor(r, dizi)
    ]


# ==================================================
# /İZLE SAYFASINDAN SON 3 BÖLÜMÜ BUL
# ==================================================

async def bolum_linklerini_bul(page, dizi):

    print(
        "\n[DİZİ SAYFASI]",
        dizi["name"],
        dizi["page"]
    )

    try:
        await page.goto(
            dizi["page"],
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(4000)

    except Exception as e:
        print("[SAYFA HATASI]", str(e))
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
        text = item.get("text", "")

        if not link:
            continue

        low_link = link.lower()
        low_text = text.lower()

        if "fragman" in low_link or "fragman" in low_text:
            continue

        if "teaser" in low_link or "teaser" in low_text:
            continue

        if "/bolumler/" not in low_link:
            continue

        match = re.search(
            r"/bolumler/(\d+)",
            urlparse(link).path.lower()
        )

        if not match:
            continue

        bolum_no = int(match.group(1))

        adaylar[bolum_no] = {
            "url": link,
            "text": text
        }

    sirali = sorted(
        adaylar.items(),
        key=lambda x: x[0],
        reverse=True
    )

    # Sayfada link bulunamadıysa butonları dene
    if not sirali:

        print(
            "[BÖLÜM LİNKİ YOK] Butonlar deneniyor..."
        )

        for selector in [
            "text=Son Bölüm İzle",
            "text=Son Bölümü İzle",
            "text=Bölümleri İzle",
            "a:has-text('İzle')"
        ]:

            try:
                await page.locator(
                    selector
                ).first.click(timeout=3000)

                await page.wait_for_timeout(4000)

                current_url = page.url

                if "/bolumler/" in current_url.lower():

                    match = re.search(
                        r"/bolumler/(\d+)",
                        urlparse(current_url).path.lower()
                    )

                    if match:
                        no = int(match.group(1))

                        sirali = [
                            (
                                no,
                                {
                                    "url": current_url,
                                    "text": ""
                                }
                            )
                        ]

                        break

            except Exception:
                pass

    sirali = sirali[:MAX_EPISODES]

    print(
        "[BULUNAN BÖLÜMLER]",
        [no for no, item in sirali]
    )

    return sirali


# ==================================================
# TEK BÖLÜMDEN HLS BUL
# ==================================================

async def bolum_hls_bul(browser, dizi, bolum_no, bolum):

    page = await browser.new_page(
        user_agent=UA
    )

    hls_adresleri = set()

    def adres_yakala(adres):

        adres = hls_duzelt(adres)

        if (
            adres.startswith("http")
            and ".m3u8" in adres.lower()
        ):

            low = adres.lower()

            if any(x in low for x in [
                "fragman",
                "teaser",
                "tanitim"
            ]):
                return

            hls_adresleri.add(adres)

    def request_yakala(request):
        try:
            adres_yakala(request.url)
        except Exception:
            pass

    def response_yakala(response):
        try:
            adres_yakala(response.url)
        except Exception:
            pass

    page.on("request", request_yakala)
    page.on("response", response_yakala)

    try:

        bolum_url = bolum["url"]

        print(
            "\n[BÖLÜM TARAMA]",
            dizi["name"],
            bolum_no
        )

        await page.goto(
            bolum_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        # Logo
        logo = ""

        for selector in [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]'
        ]:

            try:
                logo = await page.locator(
                    selector
                ).first.get_attribute("content") or ""

                if logo:
                    break

            except Exception:
                pass

        # Açıklama
        aciklama = ""

        try:
            aciklama = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content") or ""

        except Exception:
            pass

        # Tarih
        tarih = ""

        for selector in [
            'meta[property="article:published_time"]',
            'meta[property="og:updated_time"]',
            'meta[name="date"]'
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

        # HTML taraması
        html = await page.content()

        for adres in hls_html_bul(html):
            adres_yakala(adres)

        # Oynatıcıyı başlat
        for selector in [
            ".jw-icon-play",
            ".vjs-big-play-button",
            ".plyr__control--overlaid",
            "button[aria-label*='Oynat']",
            "text=Oynat"
        ]:

            try:
                element = page.locator(
                    selector
                ).first

                if await element.count():

                    await element.click(
                        timeout=3000,
                        force=True
                    )

                    await page.wait_for_timeout(7000)
                    break

            except Exception:
                pass

        # Video oynatma denemesi
        try:
            await page.locator(
                "video"
            ).first.evaluate(
                "(v) => v.play()"
            )

            await page.wait_for_timeout(7000)

        except Exception:
            pass

        # Son HTML taraması
        html = await page.content()

        for adres in hls_html_bul(html):
            adres_yakala(adres)

        secilen = hls_sec(hls_adresleri)

        if not secilen:

            print(
                "[HLS BULUNAMADI]",
                dizi["name"],
                bolum_no
            )

            return None

        print(
            "[HLS BULUNDU]",
            dizi["name"],
            bolum_no,
            secilen[:120]
        )

        return {
            "name": dizi["name"],
            "episode": f"{bolum_no}. BÖLÜM",
            "episode_no": bolum_no,
            "date": tarih,
            "logo": logo or BASE + "/favicon.ico",
            "description": aciklama,
            "url": secilen
        }

    except Exception as e:

        print(
            "[BÖLÜM HATASI]",
            dizi["name"],
            bolum_no,
            str(e)
        )

        return None

    finally:
        await page.close()


# ==================================================
# BİR DİZİNİN SON 3 BÖLÜMÜNÜ TARA
# ==================================================

async def dizi_bul(browser, dizi):

    page = await browser.new_page(
        user_agent=UA
    )

    try:
        bolumler = await bolum_linklerini_bul(
            page,
            dizi
        )

    finally:
        await page.close()

    if not bolumler:

        print(
            "[DİZİ BULUNAMADI]",
            dizi["name"]
        )

        return {
            "unavailable": True,
            "name": dizi["name"],
            "episodes": []
        }

    sonuclar = []

    for bolum_no, bolum in bolumler:

        sonuc = await bolum_hls_bul(
            browser,
            dizi,
            bolum_no,
            bolum
        )

        if sonuc:
            sonuclar.append(sonuc)

        await asyncio.sleep(1)

    sonuclar.sort(
        key=lambda x: x["episode_no"],
        reverse=True
    )

    if not sonuclar:

        print(
            "[DİZİDE HLS YOK]",
            dizi["name"]
        )

        return {
            "unavailable": True,
            "name": dizi["name"],
            "episodes": []
        }

    return {
        "unavailable": False,
        "name": dizi["name"],
        "episodes": sonuclar[:MAX_EPISODES]
    }


# ==================================================
# M3U DOSYASINI OKU
# ==================================================

def m3u_oku():

    if not os.path.exists(M3U_FILE):
        return ["#EXTM3U"], [], False, "\n"

    with open(M3U_FILE, "rb") as f:
        raw = f.read()

    bom = raw.startswith(codecs.BOM_UTF8)

    metin = raw.decode(
        "utf-8-sig",
        errors="replace"
    )

    newline = (
        "\r\n" if "\r\n" in metin else "\n"
    )

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
# M3U DOSYASINI BAĞIMSIZ GÜNCELLE
# ==================================================

def listeyi_guncelle(sonuclar):

    baslik, records, bom, newline = m3u_oku()

    # Hiçbir dizide yeni HLS yoksa dosyayı değiştirme
    basarili = [
        sonuc for sonuc in sonuclar
        if not sonuc.get("unavailable")
        and sonuc.get("episodes")
    ]

    if not basarili:

        print("\n[YENİ BÖLÜM YOK]")
        print("Mevcut dosya değiştirilmedi.")

        return False

    # Eski NOW kayıtlarını ayır
    eski_now = [
        r for r in records
        if grup_bul(r) == TARGET_GROUP
    ]

    # Eski bilgilendirme kaydını koru
    eski_info = None

    for record in eski_now:

        if "BİLGİLENDİRME" in kanal_adi(record).upper():
            eski_info = record
            break

    if eski_info is None:
        eski_info = info_kaydi()

    yeni_now = [eski_info]

    # Her diziyi kendi sırasıyla işle
    for dizi in DIZILER:

        sonuc = next(
            (
                x for x in sonuclar
                if normalize(x["name"]) == normalize(dizi["name"])
            ),
            None
        )

        if sonuc and not sonuc.get("unavailable") and sonuc.get("episodes"):

            # Başarılı dizinin yeni bölümlerini ekle
            for bolum in sonuc["episodes"]:
                yeni_now.append(
                    dizi_kaydi(bolum)
                )

            print(
                "[GÜNCELLENDİ]",
                dizi["name"],
                len(sonuc["episodes"]),
                "bölüm"
            )

        else:

            # Başarısız dizinin eski kayıtlarını koru
            eski_kayitlar = eski_dizi_kayitlari(
                records,
                dizi
            )

            yeni_now.extend(eski_kayitlar)

            print(
                "[ESKİ KAYIT KORUNDU]",
                dizi["name"],
                len(eski_kayitlar),
                "kayıt"
            )

    # Yedek al
    if os.path.exists(M3U_FILE):

        shutil.copy2(
            M3U_FILE,
            M3U_FILE + ".bak"
        )

    # Bağımsız dosya: yalnızca NOW dizileri
    son_records = yeni_now

    satirlar = list(baslik)

    for record in son_records:
        satirlar.extend(record)

    yeni_metin = newline.join(satirlar) + newline

    encoding = "utf-8-sig" if bom else "utf-8"

    temp = M3U_FILE + ".tmp"

    with open(temp, "wb") as f:
        f.write(
            yeni_metin.encode(encoding)
        )

    os.replace(
        temp,
        M3U_FILE
    )

    print("\n====================================")
    print("NOW TV DİZİ GÜNCELLEME TAMAMLANDI")
    print("====================================")
    print("Dosya:", M3U_FILE)
    print("Grup:", TARGET_GROUP)
    print("Dizi sayısı:", len(DIZILER))
    print("Başarılı dizi:", len(basarili))
    print("Bölüm limiti:", MAX_EPISODES)
    print("Eski başarısız kayıtlar: KORUNDU")
    print("Bilgilendirme kaydı: KORUNDU")
    print("Bağımsız M3U: EVET")
    print("Yedek:", M3U_FILE + ".bak")
    print("====================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    print("====================================")
    print("MIRTI68 - NOW TV DİZİ BOTU")
    print("====================================")

    print("Çıktı:", M3U_FILE)
    print("Dizi sayısı:", len(DIZILER))
    print("Son bölüm limiti:", MAX_EPISODES)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        sonuclar = []

        try:

            for dizi in DIZILER:

                sonuc = await dizi_bul(
                    browser,
                    dizi
                )

                sonuclar.append(sonuc)

        finally:
            await browser.close()

    toplam = sum(
        len(x.get("episodes", []))
        for x in sonuclar
    )

    print("\nTOPLAM BULUNAN BÖLÜM:", toplam)

    listeyi_guncelle(
        sonuclar
    )


if __name__ == "__main__":
    asyncio.run(main())
    

    
