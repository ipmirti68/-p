
import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - SHOW TV DİZİ OTOMATİK GÜNCELLEYİCİ
# BAĞIMSIZ M3U SİSTEMİ
# ==================================================

M3U_FILE = "showdizi.m3u"
BASE = "https://www.showtv.com.tr"

TARGET_GROUP = "🟪◆ SHOW DİZİ 📺⭕"

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)

DIZILER = [
    {"slug": "sevdan-bir-ates", "name": "SEVDAN BİR ATEŞ"},
    {"slug": "kizilcik-serbeti", "name": "KIZILCIK ŞERBETİ"},
    {"slug": "muhtemel-ask", "name": "MUHTEMEL AŞK"},
    {"slug": "menekse", "name": "MENEKŞE"},
    {"slug": "cevher", "name": "CEVHER"},
]

# ==================================================
# YARDIMCILAR
# ==================================================

def temizle(text):
    return unescape(str(text or "")).strip()


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
            m = re.search(r'group-title="([^"]*)"', line)
            return m.group(1) if m else ""
    return ""


def kanal_adi(record):
    for line in record:
        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip()
    return ""


def dizi_adi_eslesiyor(kayit_adi, dizi_adi):
    return kayit_adi.upper().startswith(dizi_adi.upper())


def info_kaydi():
    return [
        (
            f'#EXTINF:-1 tvg-name="***** SHOW TV DİZİ *****" '
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
        f'#EXTINF:-1 tvg-id="" '
        f'tvg-name="{guvenli(gorunen)}" '
        f'tvg-logo="{guvenli(d.get("logo", ""))}" '
        f'tvg-description="{guvenli(d.get("description", ""))}" '
        f'group-title="{TARGET_GROUP}",{guvenli(gorunen)}'
    )

    return [extinf, d["url"]]


# ==================================================
# ESKİ M3U KAYITLARINI OKU
# ==================================================

def m3u_oku():
    if not os.path.exists(M3U_FILE):
        return ["#EXTM3U"], [], "\n", False

    with open(M3U_FILE, "rb") as f:
        raw = f.read()

    bom = raw.startswith(codecs.BOM_UTF8)
    metin = raw.decode("utf-8-sig", errors="replace")

    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()

    ilk_extinf = next(
        (
            i for i, satir in enumerate(satirlar)
            if satir.startswith("#EXTINF:")
        ),
        len(satirlar)
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

    return baslik, records, newline, bom


# ==================================================
# DİZİ SAYFASINDAN SON BÖLÜMÜ BUL
# ==================================================

async def dizi_bul(browser, dizi):

    page = await browser.new_page(user_agent=UA)
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

    page.on("request", lambda r: adres_yakala(r.url))
    page.on("response", lambda r: adres_yakala(r.url))

    try:
        print(f"\n[DİZİ] {dizi['name']}")

        denenecek = [
            f"{BASE}/dizi/tanitim/{dizi['slug']}",
            f"{BASE}/dizi/{dizi['slug']}",
            f"{BASE}/dizi/tanitim/{dizi['slug']}/bolumler",
        ]

        logo = ""
        aciklama = ""
        adaylar = {}

        for url in denenecek:

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                await page.wait_for_timeout(4000)

                try:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(2500)

                    await page.evaluate(
                        "window.scrollTo(0, 0)"
                    )
                    await page.wait_for_timeout(1500)

                except Exception:
                    pass

            except Exception as e:
                print(f"  Sayfa açılamadı: {url}")
                print(" ", str(e)[:250])
                continue

            # LOGO
            if not logo:
                for selector in [
                    'meta[property="og:image"]',
                    'meta[name="twitter:image"]'
                ]:
                    try:
                        value = await page.locator(
                            selector
                        ).first.get_attribute("content")

                        if value:
                            logo = value
                            break

                    except Exception:
                        pass

            # AÇIKLAMA
            if not aciklama:
                try:
                    aciklama = (
                        await page.locator(
                            'meta[name="description"]'
                        ).first.get_attribute("content")
                        or ""
                    )
                except Exception:
                    pass

            # SAYFADAKİ BÖLÜM LİNKLERİ
            try:
                links = await page.locator(
                    "a[href]"
                ).evaluate_all(
                    """els => els.map(a => ({
                        url: a.href,
                        text: (a.innerText || a.textContent || '').trim()
                    }))"""
                )

            except Exception:
                links = []

            for item in links:

                link = item.get("url", "")
                text = item.get("text", "")

                low_link = link.lower()
                low_text = text.lower()

                if "fragman" in low_text or "fragman" in low_link:
                    continue

                if dizi["slug"] not in low_link:
                    continue

                if link.rstrip("/") == url.rstrip("/"):
                    continue

                bolum_no = None

                # Metinde bölüm numarası
                m = re.search(
                    r'(\d+)\s*\.?\s*bölüm',
                    text,
                    re.I
                )

                if m:
                    bolum_no = int(m.group(1))

                # URL'den bölüm numarası
                if bolum_no is None:

                    m3 = re.search(
                        rf"{re.escape(dizi['slug'])}[^0-9]*(\d+)",
                        low_link
                    )

                    if m3:
                        if (
                            "/bolum" in low_link
                            or "-bolum" in low_link
                            or re.search(r'/\d+/?$', low_link)
                        ):
                            bolum_no = int(m3.group(1))

                if bolum_no is None:
                    continue

                if bolum_no <= 0 or bolum_no > 500:
                    continue

                if bolum_no not in adaylar:
                    adaylar[bolum_no] = {
                        "url": link,
                        "text": text or f"{bolum_no}. Bölüm"
                    }

            # HAM HTML İÇİNDE BÖLÜM LİNKİ ARA
            if not adaylar:
                try:
                    html = await page.content()

                    html = (
                        unescape(html)
                        .replace("\\/", "/")
                        .replace("\\u0026", "&")
                    )

                    pattern = (
                        rf'https?://www\.showtv\.com\.tr/'
                        rf'[^\s"\'<>]*'
                        rf'{re.escape(dizi["slug"])}'
                        rf'[^\s"\'<>]*?'
                        rf'(\d+)'
                        rf'[^\s"\'<>]*?bolum'
                        rf'[^\s"\'<>]*'
                    )

                    for mm in re.finditer(
                        pattern,
                        html,
                        re.I
                    ):
                        full = mm.group(0)

                        try:
                            no = int(mm.group(1))

                            if (
                                no not in adaylar
                                and "fragman" not in full.lower()
                            ):
                                adaylar[no] = {
                                    "url": full,
                                    "text": f"{no}. Bölüm"
                                }

                        except Exception:
                            pass

                except Exception:
                    pass

            if adaylar:
                print(
                    f"  {len(adaylar)} bölüm adayı bulundu."
                )
                break

        if not adaylar:
            print(
                f"[BÖLÜM BULUNAMADI] {dizi['name']} "
                "- eski kayıt korunacak."
            )

            return {
                "unavailable": True,
                "name": dizi["name"]
            }

        # EN SON BÖLÜM
        son_bolum = max(adaylar)

        hedef = adaylar[son_bolum]["url"]
        bolum_adi = adaylar[son_bolum]["text"]

        if not re.search(r'bölüm', bolum_adi, re.I):
            bolum_adi = f"{son_bolum}. Bölüm"

        print(f"[SON BÖLÜM] {son_bolum}")
        print("[BÖLÜM URL]", hedef)

        await page.goto(
            hedef,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        # BÖLÜM AÇIKLAMASI
        try:
            desc = await page.locator(
                'meta[name="description"]'
            ).first.get_attribute("content")

            if desc:
                aciklama = desc

        except Exception:
            pass

        if not logo:
            logo = BASE + "/favicon.ico"

        # TARİH
        tarih = ""

        for selector in [
            'meta[property="article:published_time"]',
            'meta[property="og:updated_time"]'
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

        # HLS ADRESLERİNİ TARA
        for _ in range(2):

            try:
                html = await page.content()

                html = (
                    unescape(html)
                    .replace("\\/", "/")
                    .replace("\\u0026", "&")
                )

                bulunanlar = re.findall(
                    r'https?://[^\s"\'<>]+?\.m3u8'
                    r'(?:\?[^\s"\'<>]*)?',
                    html,
                    re.I
                )

                for adres in bulunanlar:
                    adres_yakala(adres)

            except Exception:
                pass

            # OYNATMA BUTONLARINI DENE
            for selector in [
                ".jw-icon-play",
                ".vjs-big-play-button",
                ".plyr__control--overlaid",
                "button[aria-label*='Oynat']"
            ]:
                try:
                    el = page.locator(selector).first

                    if await el.count():
                        await el.click(
                            timeout=2500,
                            force=True
                        )

                        await page.wait_for_timeout(7000)
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

                await page.wait_for_timeout(7000)

            except Exception:
                pass

        if not hls_adresleri:
            print(
                f"[HLS BULUNAMADI] {dizi['name']} "
                "- eski kayıt korunacak."
            )

            return {
                "unavailable": True,
                "name": dizi["name"]
            }

        # MASTER M3U8 ÖNCELİKLİ
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

        print("[HATA]", dizi["name"], str(e)[:300])

        return {
            "unavailable": True,
            "name": dizi["name"]
        }

    finally:
        await page.close()


# ==================================================
# BAĞIMSIZ M3U GÜNCELLEME
# ==================================================

def listeyi_guncelle(yeni_diziler, bulunamayan_isimler):

    baslik, records, newline, bom = m3u_oku()

    eski_info = None
    eski_diziler = []
    digerleri = []

    # MEVCUT KAYITLARI AYIR
    for record in records:

        grup = grup_bul(record)

        if grup == TARGET_GROUP:

            ad = kanal_adi(record)

            if "BİLGİLENDİRME" in ad.upper():
                eski_info = record

            else:
                eski_diziler.append(record)

        else:
            digerleri.append(record)

    if eski_info is None:
        eski_info = info_kaydi()

    # YENİLENEN DİZİLER
    yeni_isimler = {
        d["name"].upper()
        for d in yeni_diziler
    }

    # BULUNAMAYAN DİZİLERİN ESKİ KAYITLARINI KORU
    korunan = []

    for record in eski_diziler:

        ad = kanal_adi(record)

        for isim in bulunamayan_isimler:

            if dizi_adi_eslesiyor(ad, isim):

                korunan.append(record)

                print(
                    f"[ESKİ KAYIT KORUNDU] {ad}"
                )

                break

    # TANIMLANMAMIŞ ESKİ SHOW KAYITLARINI KORU
    bilinen_isimler = [
        d["name"].upper()
        for d in DIZILER
    ]

    for record in eski_diziler:

        ad = kanal_adi(record).upper()

        bilinen = any(
            ad.startswith(isim)
            for isim in bilinen_isimler
        )

        if not bilinen:
            korunan.append(record)

    # YENİ M3U KAYITLARI
    yeni_kayitlar = [eski_info]

    for dizi in yeni_diziler:
        yeni_kayitlar.append(
            dizi_kaydi(dizi)
        )

    yeni_kayitlar.extend(korunan)

    # DOSYAYI OLUŞTUR
    son_records = yeni_kayitlar + digerleri

    sonuc = list(baslik)

    for record in son_records:
        sonuc.extend(record)

    yeni_metin = newline.join(sonuc) + newline

    # YEDEK AL
    if os.path.exists(M3U_FILE):
        shutil.copy2(
            M3U_FILE,
            M3U_FILE + ".bak"
        )

    temp = M3U_FILE + ".tmp"

    encoding = "utf-8-sig" if bom else "utf-8"

    with open(temp, "wb") as f:
        f.write(
            yeni_metin.encode(encoding)
        )

    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("SHOW TV DİZİ GÜNCELLEME TAMAMLANDI")
    print("===================================")
    print("Dosya:", M3U_FILE)
    print("Grup:", TARGET_GROUP)
    print("Yenilenen dizi:", len(yeni_diziler))
    print("Korunan eski kayıt:", len(korunan))
    print("Bilgilendirme kaydı: HAZIR")
    print("Diğer gruplar: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("===================================")

    return True


# ==================================================
# ANA PROGRAM
# ==================================================

async def main():

    print("===================================")
    print("MIRTI68 - SHOW TV DİZİ BOTU")
    print("===================================")

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        yeni_diziler = []
        bulunamayan = []

        try:

            for dizi in DIZILER:

                sonuc = await dizi_bul(
                    browser,
                    dizi
                )

                if not sonuc or sonuc.get("unavailable"):

                    bulunamayan.append(
                        dizi["name"]
                    )

                    continue

                yeni_diziler.append(sonuc)

        finally:
            await browser.close()

    # HİÇ YENİ BÖLÜM BULUNAMADIYSA DOSYAYA DOKUNMA
    if not yeni_diziler:

        print("\nYeni HLS bağlantısı bulunamadı.")
        print("Eski M3U dosyası aynen korunuyor.")
        return

    # BAĞIMSIZ DOSYAYI GÜNCELLE
    listeyi_guncelle(
        yeni_diziler,
        bulunamayan
    )


if __name__ == "__main__":
    asyncio.run(main())
