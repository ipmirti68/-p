
import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from playwright.async_api import async_playwright

# ==================================================
# MIRTI68 - STAR TV DİZİ OTOMATİK GÜNCELLEYİCİ
# BAĞIMSIZ M3U SİSTEMİ
# ==================================================

M3U_FILE = "stardizi.m3u"
BASE = "https://www.startv.com.tr"

STAR_GROUP = "🟪◆  STAR DIZI 📺⭕"

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)

DIZILER = [
    {"slug": "sahipsizler", "name": "SAHİPSİZLER"},
    {"slug": "baskalarinin-hayati", "name": "BAŞKALARININ HAYATI"},
    {"slug": "tuzlu-kahve", "name": "TUZLU KAHVE"},
    {"slug": "sevdigim-sensin", "name": "SEVDİĞİM SENSİN"},
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


def info_kaydi():
    return [
        (
            f'#EXTINF:-1 tvg-name="***** STAR DIZI *****" '
            f'tvg-logo="{INFO_LOGO}" '
            f'group-title="{STAR_GROUP}",BİLGİLENDİRME'
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
        f'group-title="{STAR_GROUP}",{guvenli(gorunen)}'
    )

    return [extinf, d["url"]]


async def meta(page, selector):
    try:
        value = await page.locator(
            selector
        ).first.get_attribute("content")

        return value or ""

    except Exception:
        return ""


def dizi_eslesiyor(kayit_adi, dizi_adi):
    return kayit_adi.upper().startswith(dizi_adi.upper())


# ==================================================
# M3U DOSYASINI OKU
# ==================================================

def m3u_oku():

    if not os.path.exists(M3U_FILE):
        return ["#EXTM3U"], [], "\n", False

    with open(M3U_FILE, "rb") as file:
        raw = file.read()

    bom = raw.startswith(codecs.BOM_UTF8)
    text = raw.decode("utf-8-sig", errors="replace")

    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()

    first_extinf = next(
        (
            i for i, line in enumerate(lines)
            if line.startswith("#EXTINF:")
        ),
        len(lines)
    )

    header = lines[:first_extinf]
    body = lines[first_extinf:]

    if not header:
        header = ["#EXTM3U"]

    records = []
    current = []

    for line in body:

        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []

        current.append(line)

    if current:
        records.append(current)

    return header, records, newline, bom


# ==================================================
# DİZİ SAYFASINDAN SON BÖLÜMÜ BUL
# ==================================================

async def dizi_bul(browser, dizi):

    page = await browser.new_page(user_agent=UA)
    hls_urls = []

    def yakala(adres):

        adres = (
            unescape(str(adres or ""))
            .replace("\\/", "/")
            .replace("\\u0026", "&")
            .replace("&amp;", "&")
            .strip()
        )

        if (
            ".m3u8" in adres.lower()
            and adres.startswith("http")
            and adres not in hls_urls
        ):
            hls_urls.append(adres)

    page.on("request", lambda r: yakala(r.url))
    page.on("response", lambda r: yakala(r.url))

    try:

        print(f"\n[DİZİ] {dizi['name']}")

        denenecek = [
            f"{BASE}/dizi/{dizi['slug']}",
            f"{BASE}/dizi/{dizi['slug']}/bolumler",
        ]

        logo = ""
        description = ""
        date = ""
        adaylar = {}

        # DİZİ SAYFALARINI DENE
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

                print("[SAYFA AÇILAMADI]", url)
                print(str(e)[:250])
                continue

            # LOGO
            if not logo:

                logo = (
                    await meta(
                        page,
                        'meta[property="og:image"]'
                    )
                    or await meta(
                        page,
                        'meta[name="twitter:image"]'
                    )
                )

            # AÇIKLAMA
            if not description:

                description = await meta(
                    page,
                    'meta[name="description"]'
                )

            # BÖLÜM LİNKLERİ
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

                # METİNDE BÖLÜM NUMARASI
                m = re.search(
                    r'(\d+)\s*\.?\s*bölüm',
                    text,
                    re.I
                )

                if m:
                    bolum_no = int(m.group(1))

                # URL'DE /BOLUMLER/51-BOLUM
                if bolum_no is None:

                    m2 = re.search(
                        r'/bolumler/(\d+)[-\w]*',
                        low_link
                    )

                    if m2:
                        bolum_no = int(m2.group(1))

                # SON BÖLÜM YAZISI
                if bolum_no is None:

                    if (
                        "son bölüm" in low_text
                        or "son bolum" in low_text
                    ):
                        bolum_no = 999

                if bolum_no is None:
                    continue

                if bolum_no <= 0 or bolum_no > 999:
                    continue

                if bolum_no not in adaylar:

                    adaylar[bolum_no] = {
                        "url": link,
                        "text": text or f"{bolum_no}. Bölüm"
                    }

            # HTML KAYNAĞINDA DA ARA
            if not adaylar:

                try:

                    html = await page.content()

                    html = (
                        unescape(html)
                        .replace("\\/", "/")
                        .replace("\\u0026", "&")
                        .replace("&amp;", "&")
                    )

                    pattern = (
                        rf'https?://www\.startv\.com\.tr/'
                        rf'[^\s"\'<>]*'
                        rf'{re.escape(dizi["slug"])}'
                        rf'[^\s"\'<>]*?'
                        rf'(\d+)'
                        rf'[^\s"\'<>]*?'
                        rf'bolum'
                        rf'[^\s"\'<>]*'
                    )

                    for match in re.finditer(
                        pattern,
                        html,
                        re.I
                    ):

                        full_url = match.group(0)
                        full_url = full_url.replace("\\/", "/")

                        try:
                            no = int(match.group(1))

                            if (
                                no not in adaylar
                                and "fragman" not in full_url.lower()
                            ):

                                adaylar[no] = {
                                    "url": full_url,
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

        # BÖLÜM BULUNAMADI
        if not adaylar:

            print(
                f"[BÖLÜM BULUNAMADI] {dizi['name']} "
                "- eski kayıt korunacak."
            )

            return {
                "unavailable": True,
                "name": dizi["name"]
            }

        # EN SON BÖLÜMÜ SEÇ
        son_bolum = max(adaylar)

        hedef = adaylar[son_bolum]["url"]
        episode = adaylar[son_bolum]["text"]

        if son_bolum == 999:

            episode = "Son Bölüm"

        elif not re.search(r'bölüm', episode, re.I):

            episode = f"{son_bolum}. Bölüm"

        print(f"[SON BÖLÜM] {son_bolum}")
        print("[BÖLÜM URL]", hedef)

        # BÖLÜM SAYFASINI AÇ
        await page.goto(
            hedef,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(6000)

        # BÖLÜM AÇIKLAMASI
        description = (
            await meta(
                page,
                'meta[name="description"]'
            )
            or description
        )

        # TARİH
        date = await meta(
            page,
            'meta[property="article:published_time"]'
        )

        if not date:

            date = await meta(
                page,
                'meta[property="og:updated_time"]'
            )

        if date:
            date = date[:10]

        # HLS ADRESLERİNİ TOPLA
        for _ in range(2):

            try:

                html = await page.content()

                html = (
                    unescape(html)
                    .replace("\\/", "/")
                    .replace("\\u0026", "&")
                    .replace("&amp;", "&")
                )

                bulunanlar = re.findall(
                    r'https?://[^\s"\'<>]+?\.m3u8'
                    r'(?:\?[^\s"\'<>]*)?',
                    html,
                    re.I
                )

                for adres in bulunanlar:
                    yakala(adres)

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

                    el = page.locator(
                        selector
                    ).first

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

        # HLS BULUNAMADI
        if not hls_urls:

            print(
                f"[HLS BULUNAMADI] {dizi['name']} "
                "- eski kayıt korunacak."
            )

            return {
                "unavailable": True,
                "name": dizi["name"]
            }

        # HLS ADRESİNİ PUANLA
        def skor(url):

            u = url.lower()
            score = 0

            if "mncdn.com" in u:
                score += 10

            if "smil" in u:
                score += 10

            if "playlist.m3u8" in u:
                score += 10

            if "master.m3u8" in u:
                score += 5

            return -score

        hls_urls.sort(key=skor)

        stream_url = hls_urls[0]

        print("[HLS BULUNDU]", stream_url)
        print("[LOGO]", logo or "Bulunamadı")
        print("[TARİH]", date or "Bulunamadı")

        return {
            "name": dizi["name"],
            "episode": episode,
            "date": date,
            "logo": logo or (BASE + "/favicon.ico"),
            "description": description,
            "url": stream_url
        }

    except Exception as exc:

        print("[HATA]", dizi["name"], str(exc)[:300])

        return {
            "unavailable": True,
            "name": dizi["name"]
        }

    finally:
        await page.close()


# ==================================================
# M3U KAYITLARINI KORUYARAK GÜNCELLE
# ==================================================

def listeyi_guncelle(yeni_diziler, bulunamayan_isimler):

    header, records, newline, bom = m3u_oku()

    eski_info = None
    eski_diziler = []
    digerleri = []

    # ESKİ KAYITLARI AYIR
    for record in records:

        grup = grup_bul(record)

        if grup == STAR_GROUP:

            ad = kanal_adi(record)

            if "BİLGİLENDİRME" in ad.upper() or "BILGILENDIRME" in ad.upper():

                eski_info = record

            else:

                eski_diziler.append(record)

        else:

            digerleri.append(record)

    if eski_info is None:
        eski_info = info_kaydi()

    # BULUNAMAYAN DİZİLERİN ESKİ KAYITLARINI KORU
    korunan = []

    for record in eski_diziler:

        ad = kanal_adi(record)

        for isim in bulunamayan_isimler:

            if dizi_eslesiyor(ad, isim):

                korunan.append(record)

                print(
                    f"[ESKİ KAYIT KORUNDU] {ad}"
                )

                break

    # TANIMLANMAMIŞ ESKİ STAR KAYITLARINI DA KORU
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

    # YENİ KAYITLARI HAZIRLA
    yeni_kayitlar = [eski_info]

    for dizi in yeni_diziler:

        yeni_kayitlar.append(
            dizi_kaydi(dizi)
        )

    yeni_kayitlar.extend(korunan)

    # STAR GRUBUNU DOSYANIN BAŞINA EKLE
    # DİĞER GRUPLARIN SIRASI VE KAYITLARI KORUNUR
    final_records = yeni_kayitlar + digerleri

    output = list(header)

    for record in final_records:
        output.extend(record)

    yeni_metin = newline.join(output) + newline

    # YEDEK AL
    if os.path.exists(M3U_FILE):

        shutil.copy2(
            M3U_FILE,
            M3U_FILE + ".bak"
        )

    temp = M3U_FILE + ".tmp"

    encoding = "utf-8-sig" if bom else "utf-8"

    with open(temp, "wb") as file:

        file.write(
            yeni_metin.encode(encoding)
        )

    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("STAR TV DİZİ GÜNCELLEMESİ TAMAMLANDI")
    print("===================================")
    print("Dosya:", M3U_FILE)
    print("Grup:", STAR_GROUP)
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
    print("MIRTI68 - STAR TV DİZİ BOTU")
    print("===================================")

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True
        )

        results = []
        bulunamayan = []

        try:

            for series in DIZILER:

                result = await dizi_bul(
                    browser,
                    series
                )

                if not result or result.get("unavailable"):

                    bulunamayan.append(
                        series["name"]
                    )

                    continue

                results.append(result)

        finally:

            await browser.close()

    # HİÇ YENİ HLS BULUNAMADIYSA DOSYAYA DOKUNMA
    if not results:

        print("\nHiçbir dizide HLS bağlantısı bulunamadı.")
        print("Eski M3U dosyası aynen korunuyor.")
        return

    # BAĞIMSIZ DOSYAYI GÜNCELLE
    listeyi_guncelle(
        results,
        bulunamayan
    )


if __name__ == "__main__":
    asyncio.run(main())
            
