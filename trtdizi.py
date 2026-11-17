import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# TRT1 DİZİ OTOMATİK GÜNCELLEYİCİ
# ==================================================

M3U_FILE = "mirti68.m3u"

BASE = "https://www.trt1.com.tr"

SHOW_GROUP = "🟪◆ SHOW DİZİ 📺⭕"
ATV_GROUP = "🟪◆  ATV DİZİ 📺⭕"
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
    "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)

DIZILER = [
    {
        "slug": "evlilik-guzeldir",
        "name": "EVLİLİK GÜZELDİR",
        "url": BASE + "/diziler/evlilik-guzeldir"
    },
    {
        "slug": "mehmed-fetihler-sultani",
        "name": "MEHMED FETİHLER SULTANI",
        "url": BASE + "/diziler/mehmed-fetihler-sultani"
    },
    {
        "slug": "gonul-dagi",
        "name": "GÖNÜL DAĞI",
        "url": BASE + "/diziler/gonul-dagi"
    },
    {
        "slug": "tasacak-bu-deniz",
        "name": "TAŞACAK BU DENİZ",
        "url": BASE + "/diziler/tasacak-bu-deniz"
    },
    {
        "slug": "teskilat",
        "name": "TEŞKİLAT",
        "url": BASE + "/diziler/teskilat"
    },
    {
        "slug": "kod-adi-kirlangic",
        "name": "KOD ADI KIRLANGIÇ",
        "url": BASE + "/diziler/kod-adi-kirlangic"
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
        f'#EXTINF:-1 tvg-name="***** TRT DİZİ *****" '
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
    return [extinf, d["url"]]

# ==================================================
# EN GÜNCEL BÖLÜMÜ BUL
# ==================================================

async def dizi_bul(browser, dizi):
    page = await browser.new_page(user_agent=UA)
    hls_adresleri = set()

    def yakala(url):
        url = temizle(url).replace("\\/", "/").replace("\\u0026", "&")
        if url.startswith("http") and ".m3u8" in url.lower():
            hls_adresleri.add(url)

    page.on("request", lambda r: yakala(r.url))
    page.on("response", lambda r: yakala(r.url))

    try:
        print("\n================================")
        print("[DİZİ]", dizi["name"])
        print("================================")

        # TRT1'de bölümler genelde ana dizi sayfasında listelenir
        # Önce ana sayfayı, bulamazsak /bolumler dene
        denenecek = [dizi["url"], dizi["url"] + "/bolumler"]
        adaylar = {}
        hedef_sayfa = None

        for liste_url in denenecek:
            await page.goto(liste_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            links = await page.locator("a[href]").evaluate_all(
                """els => els.map(a => ({
                    url: a.href,
                    text: (a.innerText || a.textContent || '').trim()
                }))"""
            )

            for item in links:
                link = item["url"]
                path = urlparse(link).path.lower()
                if dizi["slug"] not in path:
                    continue

                # TRT1 varyasyonları:
                # /diziler/gonul-dagi/123-bolum
                # /diziler/gonul-dagi/bolum/123
                # /diziler/gonul-dagi/123-bolum/izle
                match = re.search(r'/(?:bolum/)?(\d+)(?:-bolum)?(?:/izle)?/?$', path)
                if not match:
                    continue
                # Sadece bölüm linkleri, dizi ana sayfası değil
                if "/bolum" not in path and "/bolum/" not in path and "-bolum" not in path:
                    continue

                bolum_no = int(match.group(1))
                if bolum_no not in adaylar:
                    adaylar[bolum_no] = link

            if adaylar:
                hedef_sayfa = liste_url
                break

        if not adaylar:
            print("[HATA] Bölüm bağlantısı bulunamadı:", dizi["name"])
            return None

        son_bolum = max(adaylar)
        hedef = adaylar[son_bolum]

        print("[SON BÖLÜM]", son_bolum)
        print("[SAYFA]", hedef)

        await page.goto(hedef, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)

        # Logo
        logo = ""
        for selector in ['meta[property="og:image"]', 'meta[name="twitter:image"]']:
            try:
                logo = await page.locator(selector).first.get_attribute("content")
                if logo:
                    break
            except Exception:
                pass
        if not logo:
            logo = BASE + "/favicon.ico"

        # Açıklama
        description = ""
        try:
            description = await page.locator('meta[name="description"]').first.get_attribute("content") or ""
        except Exception:
            pass

        # Yayın tarihi
        tarih = ""
        for selector in ['meta[property="article:published_time"]', 'meta[property="og:updated_time"]']:
            try:
                tarih = await page.locator(selector).first.get_attribute("content") or ""
                if tarih:
                    break
            except Exception:
                pass
        if tarih:
            tarih = tarih[:10]

        # Sayfadaki HLS adreslerini tara
        for _ in range(2):
            html = await page.content()
            html = temizle(html).replace("\\/", "/").replace("\\u0026", "&")
            for adres in re.findall(r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?', html, re.I):
                yakala(adres)

            # Oynatmayı dene - TRT1 player
            for selector in [
                ".jw-icon-play",
                ".vjs-big-play-button",
                ".plyr__control--overlaid",
                "button[aria-label*='Oynat']",
                ".play-button",
                "[class*='play']"
            ]:
                try:
                    button = page.locator(selector).first
                    if await button.count():
                        await button.click(timeout=2500, force=True)
                        await page.wait_for_timeout(7000)
                        break
                except Exception:
                    pass

            try:
                await page.locator("video").first.evaluate("(v) => v.play()")
                await page.wait_for_timeout(7000)
            except Exception:
                pass

        if not hls_adresleri:
            print("[HLS BULUNAMADI]", dizi["name"])
            return None

        sirali = sorted(hls_adresleri, key=lambda x: ("master.m3u8" not in x.lower(), len(x)))
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
        print("[HATA]", dizi["name"], str(e))
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
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()

    # EPG başlığı korunur
    ilk_extinf = next((i for i, s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik = satirlar[:ilk_extinf]
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

    # Önceki TRT bilgilendirme kaydını koru
    info = None
    for record in records:
        if grup_bul(record) == TARGET_GROUP and "BİLGİLENDİRME" in kanal_adi(record).upper():
            info = record
            break
    if info is None:
        info = info_kaydi()

    # Sadece eski TRT grubunu kaldır, diğerleri aynen kalır
    digerleri = [r for r in records if grup_bul(r) != TARGET_GROUP]

    # Ekleme noktası: Önce SHOW DİZİ, yoksa ATV DİZİ
    anchor = None
    anchor_grup = None
    for grup in [SHOW_GROUP, ATV_GROUP]:
        for i, record in enumerate(digerleri):
            if grup_bul(record) == grup:
                anchor = i
                anchor_grup = grup
        if anchor is not None:
            break

    if anchor is None:
        print("[HATA] SHOW / ATV grubu bulunamadı!")
        print("Dosya değiştirilmedi.")
        return False

    # Eğer anchor SHOW ise son SHOW kaydını, ATV ise son ATV kaydını bul
    # ki TRT grubu grubun tamamının arkasına gelsin
    son_anchor = anchor
    for i, record in enumerate(digerleri):
        if grup_bul(record) == anchor_grup:
            son_anchor = i

    yeni_kayitlar = [info]
    for dizi in yeni_diziler:
        yeni_kayitlar.append(dizi_kaydi(dizi))

    son_records = digerleri[:son_anchor + 1] + yeni_kayitlar + digerleri[son_anchor + 1:]

    shutil.copy2(M3U_FILE, M3U_FILE + ".bak")

    sonuc = list(baslik)
    for record in son_records:
        sonuc.extend(record)

    yeni_metin = newline.join(sonuc) + newline
    temp = M3U_FILE + ".tmp"
    encoding = "utf-8-sig" if bom else "utf-8"
    with open(temp, "wb") as f:
        f.write(yeni_metin.encode(encoding))
    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("TRT DİZİ GÜNCELLEME TAMAMLANDI")
    print("===================================")
    print("Grup:", TARGET_GROUP)
    print("Konum:", anchor_grup, "grubunun hemen sonrası")
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
        browser = await p.chromium.launch(headless=True)
        yeni_diziler = []
        try:
            for dizi in DIZILER:
                sonuc = await dizi_bul(browser, dizi)
                if sonuc is None:
                    print("\nGÜNCELLEME İPTAL EDİLDİ!")
                    print("Mevcut liste korunuyor.")
                    return
                yeni_diziler.append(sonuc)
        finally:
            await browser.close()

        if len(yeni_diziler) == len(DIZILER):
            listeyi_guncelle(yeni_diziler)

if __name__ == "__main__":
    asyncio.run(main())
