import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# NOW TV DIZI OTOMATIK GUNCELLEYICI
# ==================================================

M3U_FILE = "mirti68.m3u"
BASE = "https://www.nowtv.com.tr"

NOW_GROUP = "🟪◆ NOWTV DIZILERI ⭕"
TARGET_GROUP = "🟪◆  NOW DIZI 📺⭕"

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"

DIZILER = [
    {"slug": "kiskanmak", "name": "KISKANMAK"},
    {"slug": "ben-leman", "name": "BEN LEMAN"},
    {"slug": "halef", "name": "HALEF"},
    {"slug": "cift-kisilik", "name": "CIFT KISILIK"},
    {"slug": "kizil-goncalar", "name": "KIZIL GONCALAR"},
]

# ==================================================
# YARDIMCILAR
# ==================================================

def temizle(text):
    return unescape(str(text or "")).strip()

def guvenli(v):
    return temizle(v).replace('"', "'").replace("\r", " ").replace("\n", " ")

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
        f'#EXTINF:-1 tvg-name="***** NOW DIZI *****" tvg-logo="{INFO_LOGO}" group-title="{TARGET_GROUP}",BILGILENDIRME',
        INFO_URL
    ]

def dizi_kaydi(d):
    gorunen = d["name"]
    if d.get("episode"):
        gorunen += " - " + d["episode"]
    if d.get("date"):
        gorunen += " - " + d["date"]
    extinf = (
        f'#EXTINF:-1 tvg-id="" tvg-name="{guvenli(gorunen)}" '
        f'tvg-logo="{guvenli(d["logo"])}" tvg-description="{guvenli(d["description"])}" '
        f'group-title="{TARGET_GROUP}",{guvenli(gorunen)}'
    )
    return [extinf, d["url"]]

# ==================================================
# DIZI SAYFASINDAN SON BOLUMU BUL
# ==================================================

async def dizi_bul(browser, dizi):
    page = await browser.new_page(user_agent=UA)
    hls_adresleri = set()

    def adres_yakala(adres):
        adres = temizle(adres).replace("\\/", "/").replace("\\u0026", "&")
        if ".m3u8" in adres.lower() and adres.startswith("http"):
            hls_adresleri.add(adres)

    page.on("request", lambda r: adres_yakala(r.url))
    page.on("response", lambda r: adres_yakala(r.url))

    try:
        print(f"\n[DIZI] {dizi['name']}")

        denenecek = [
            f"{BASE}/dizi/{dizi['slug']}",
            f"{BASE}/diziler/{dizi['slug']}",
            f"{BASE}/dizi/{dizi['slug']}/bolumler",
        ]

        logo = ""
        aciklama = ""
        adaylar = {}

        for url in denenecek:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2500)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass
            except Exception as e:
                print(f"  Sayfa acilmadi {url}: {e}")
                continue

            if not logo:
                for sel in ['meta[property="og:image"]', 'meta[name="twitter:image"]']:
                    try:
                        v = await page.locator(sel).first.get_attribute("content")
                        if v:
                            logo = v
                            break
                    except Exception:
                        pass
            if not aciklama:
                try:
                    aciklama = await page.locator('meta[name="description"]').first.get_attribute("content") or ""
                except Exception:
                    pass

            try:
                links = await page.locator("a[href]").evaluate_all(
                    """els => els.map(a => ({
                        url: a.href,
                        text: (a.innerText || a.textContent || '').trim()
                    }))"""
                )
            except Exception:
                links = []

            for item in links:
                link = item["url"] or ""
                text = item["text"] or ""
                low_link = link.lower()
                low_text = text.lower()
                if "fragman" in low_text or "fragman" in low_link:
                    continue
                if dizi["slug"] not in low_link:
                    continue
                if link.rstrip("/") == url.rstrip("/"):
                    continue

                bolum_no = None
                m = re.search(r'(\d+)\s*\.?\s*bölüm', text, re.I)
                if m:
                    bolum_no = int(m.group(1))
                if bolum_no is None:
                    m3 = re.search(rf"{re.escape(dizi['slug'])}[^0-9]*(\d+)", low_link)
                    if m3:
                        if "/bolum" in low_link or "-bolum" in low_link or re.search(r'/\d+/?$', low_link):
                            bolum_no = int(m3.group(1))
                if bolum_no is None:
                    continue
                if bolum_no <= 0 or bolum_no > 500:
                    continue
                if bolum_no not in adaylar:
                    adaylar[bolum_no] = {"url": link, "text": text or f"{bolum_no}. Bolum"}

            if adaylar:
                print(f"  {len(adaylar)} aday bulundu, kaynak: {url}")
                break

        if not adaylar:
            print(f"[BOLUM BEKLENIYOR] {dizi['name']} - link bulunamadi, eski kayit korunacak")
            return {"unavailable": True, "name": dizi["name"]}

        son_bolum = max(adaylar)
        hedef = adaylar[son_bolum]["url"]
        bolum_adi = adaylar[son_bolum]["text"]
        if not re.search(r'bölüm', bolum_adi, re.I):
            bolum_adi = f"{son_bolum}. Bolum"

        print(f"[SON BOLUM] {son_bolum} - {hedef}")

        await page.goto(hedef, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        try:
            desc = await page.locator('meta[name="description"]').first.get_attribute("content")
            if desc:
                aciklama = desc
        except Exception:
            pass

        if not logo:
            logo = BASE + "/favicon.ico"

        tarih = ""
        for sel in ['meta[property="article:published_time"]', 'meta[property="og:updated_time"]']:
            try:
                tarih = await page.locator(sel).first.get_attribute("content") or ""
                if tarih:
                    break
            except Exception:
                pass
        if tarih:
            tarih = tarih[:10]

        for _ in range(2):
            html = await page.content()
            html = unescape(html).replace("\\/", "/").replace("\\u0026", "&")
            for adres in re.findall(r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?', html, re.I):
                adres_yakala(adres)
            for selector in [".jw-icon-play", ".vjs-big-play-button", ".plyr__control--overlaid", "button[aria-label*='Oynat']"]:
                try:
                    el = page.locator(selector).first
                    if await el.count():
                        await el.click(timeout=2500, force=True)
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
            print(f"[HLS BULUNAMADI] {dizi['name']} - eski kayit korunacak")
            return {"unavailable": True, "name": dizi["name"]}

        sirali = sorted(hls_adresleri, key=lambda x: ("master.m3u8" not in x.lower(), len(x)))
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
        return {"unavailable": True, "name": dizi["name"]}
    finally:
        await page.close()

# ==================================================
# M3U KAYITLARINI KORUYARAK YERLESTIR
# ==================================================

def listeyi_guncelle(yeni_diziler, bulunamayan_isimler):
    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadi!")
        return False

    raw = open(M3U_FILE, "rb").read()
    bom = raw.startswith(codecs.BOM_UTF8)
    metin = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()

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

    anchor = None
    for i, record in enumerate(records):
        if grup_bul(record) == NOW_GROUP and "BILGILENDIRME" in kanal_adi(record).upper():
            anchor = i
            break
    if anchor is None:
        print("[HATA] NOWTV bilgilendirme kaydi bulunamadi!")
        print("Dosya degistirilmedi.")
        return False

    eski_show = [r for r in records if grup_bul(r) == TARGET_GROUP]
    eski_info = None
    eski_diziler = []
    for r in eski_show:
        if "BILGILENDIRME" in kanal_adi(r).upper():
            eski_info = r
        else:
            eski_diziler.append(r)
    if eski_info is None:
        eski_info = info_kaydi()

    korunan = []
    for r in eski_diziler:
        ad = kanal_adi(r)
        koru = False
        for isim in bulunamayan_isimler:
            if isim in ad:
                koru = True
                break
        if koru:
            korunan.append(r)
            print(f"  KORUNDU (eski): {ad}")

    digerleri = [r for r in records if grup_bul(r) != TARGET_GROUP]

    anchor = None
    for i, record in enumerate(digerleri):
        if grup_bul(record) == NOW_GROUP and "BILGILENDIRME" in kanal_adi(record).upper():
            anchor = i
            break
    if anchor is None:
        return False

    yeni_kayitlar = [eski_info]
    for dizi in yeni_diziler:
        yeni_kayitlar.append(dizi_kaydi(dizi))
    yeni_kayitlar.extend(korunan)

    son_records = digerleri[:anchor + 1] + yeni_kayitlar + digerleri[anchor + 1:]

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
    print("NOW DIZI GUNCELLEME TAMAMLANDI")
    print("===================================")
    print("Grup:", TARGET_GROUP)
    print("Yenilenen:", len(yeni_diziler))
    print("Korunan eski:", len(korunan))
    print("EPG basligi: KORUNDU")
    print("Diger gruplar: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("===================================")
    return True

# ==================================================
# ANA PROGRAM
# ==================================================

async def main():
    if not os.path.exists(M3U_FILE):
        print("[HATA] M3U dosyasi bulunamadi!")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yeni_diziler = []
        bulunamayan = []

        try:
            for dizi in DIZILER:
                sonuc = await dizi_bul(browser, dizi)
                if sonuc is None:
                    print(f"{dizi['name']} atlandi, digerine geciliyor")
                    bulunamayan.append(dizi["name"])
                    continue
                if sonuc.get("unavailable"):
                    bulunamayan.append(dizi["name"])
                    continue
                yeni_diziler.append(sonuc)
        finally:
            await browser.close()

        if not yeni_diziler:
            print("Henuz yayinlanmis yeni bolum bulunamadi.")
            print("Eski liste aynen korunuyor, dosya degistirilmedi.")
            return

        listeyi_guncelle(yeni_diziler, bulunamayan)

if __name__ == "__main__":
    asyncio.run(main())
