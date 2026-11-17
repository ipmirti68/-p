import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from playwright.async_api import async_playwright

# ==================================================
# 【entity-STAR TV¦canonical_name=STAR TV】 DIZI OTOMATIK GUNCELLEYICI
# ==================================================

M3U_FILE = "mirti68.m3u"
BASE = "https://www.startv.com.tr"

STAR_GROUP = "🟪◆  STAR DIZI 📺⭕"
ANCHOR_GROUPS = [
    "🟪◆  NOW DIZI 📺⭕",
    "🟪◆  ATV DİZİ 📺⭕",
    "🟪◆ SHOW DİZİ 📺⭕",
]

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"

DIZILER = [
    {"slug": "sahipsizler", "name": "SAHIPSIZLER"},
    {"slug": "kral-kaybederse", "name": "KRAL KAYBEDERSE"},
    {"slug": "ruya-gibi", "name": "RUYA GIBI"},
    {"slug": "carsı-pazarı", "name": "CARSI PAZARI"},
    {"slug": "asik-kral", "name": "ASIK KRAL"},
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
        f'#EXTINF:-1 tvg-name="***** STAR DIZI *****" tvg-logo="{INFO_LOGO}" group-title="{STAR_GROUP}",BILGILENDIRME',
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
        f'group-title="{STAR_GROUP}",{guvenli(gorunen)}'
    )
    return [extinf, d["url"]]

async def meta(page, selector):
    try:
        v = await page.locator(selector).first.get_attribute("content")
        return v or ""
    except Exception:
        return ""

# ==================================================
# DIZI SAYFASINDAN SON BOLUMU BUL
# ==================================================

async def dizi_bul(browser, dizi):
    page = await browser.new_page(user_agent=UA)
    hls_urls = []

    def yakala(adres):
        adres = temizle(adres).replace("\\/", "/").replace("\\u0026", "&")
        if ".m3u8" in adres.lower() and adres.startswith("http"):
            if adres not in hls_urls:
                hls_urls.append(adres)

    page.on("request", lambda r: yakala(r.url))
    page.on("response", lambda r: yakala(r.url))

    try:
        print(f"\n[DIZI] {dizi['name']}")

        denenecek = [
            f"{BASE}/dizi/{dizi['slug']}",
            f"{BASE}/diziler/{dizi['slug']}",
            f"{BASE}/dizi/{dizi['slug']}/bolumler",
        ]

        logo = ""
        description = ""
        date = ""
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
                logo = await meta(page, 'meta[property="og:image"]') or await meta(page, 'meta[name="twitter:image"]')
            if not description:
                description = await meta(page, 'meta[name="description"]')

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
        episode = adaylar[son_bolum]["text"]
        if not re.search(r'bölüm', episode, re.I):
            episode = f"{son_bolum}. Bolum"

        print(f"[SON BOLUM] {son_bolum} - {hedef}")

        await page.goto(hedef, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        description = await meta(page, 'meta[name="description"]') or description
        date = await meta(page, 'meta[property="article:published_time"]')
        if not date:
            date = await meta(page, 'meta[property="og:updated_time"]')
        if date:
            date = date[:10]

        html = (await page.content()).replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&")
        for url in re.findall(r'https://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?', html, re.I):
            yakala(url)

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

        html = (await page.content()).replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&")
        for url in re.findall(r'https://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?', html, re.I):
            yakala(url)

        if not hls_urls:
            print("[HLS BULUNAMADI] Sayfa acik bir M3U8 adresi sunmadi; bu kayit atlandi.")
            return {"unavailable": True, "name": dizi["name"]}

        stream_url = hls_urls[0]
        print("[HLS BULUNDU]", stream_url)
        print("[LOGO]", logo or "Bulunamadi")
        print("[TARIH]", date or "Bulunamadi")
        return {
            "name": dizi["name"],
            "episode": episode,
            "date": date,
            "logo": logo or (BASE + "/favicon.ico"),
            "description": description,
            "url": stream_url,
        }
    except Exception as exc:
        print("[HATA]", dizi["name"], str(exc))
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
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()

    first_extinf = next((i for i, line in enumerate(lines) if line.startswith("#EXTINF:")), len(lines))
    header, body = lines[:first_extinf], lines[first_extinf:]

    records, current = [], []
    for line in body:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []
        current.append(line)
    if current:
        records.append(current)

    eski_star = [r for r in records if grup_bul(r) == STAR_GROUP]
    info = None
    eski_diziler = []
    for r in eski_star:
        if "BILGILENDIRME" in kanal_adi(r).upper():
            info = r
        else:
            eski_diziler.append(r)
    if info is None:
        info = info_kaydi()

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

    others = [record for record in records if grup_bul(record) != STAR_GROUP]

    anchor = None
    for anchor_name in ANCHOR_GROUPS:
        matches = [i for i, record in enumerate(others) if grup_bul(record) == anchor_name]
        if matches:
            anchor = matches[-1]
            break
    if anchor is None:
        print("[HATA] Ekleme konumu bulunamadi. NOW / ATV / SHOW gruplarindan biri listede olmali.")
        print("Dosya degistirilmedi.")
        return False

    new_records = [info] + [dizi_kaydi(d) for d in yeni_diziler] + korunan
    final_records = others[:anchor + 1] + new_records + others[anchor + 1:]

    shutil.copy2(M3U_FILE, M3U_FILE + ".bak")
    output = list(header)
    for record in final_records:
        output.extend(record)

    temp = M3U_FILE + ".tmp"
    encoding = "utf-8-sig" if bom else "utf-8"
    with open(temp, "wb") as file:
        file.write((newline.join(output) + newline).encode(encoding))
    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("STAR DIZI GUNCELLEMESI TAMAMLANDI")
    print("Grup:", STAR_GROUP)
    print("Yenilenen dizi:", len(yeni_diziler))
    print("Korunan eski:", len(korunan))
    print("EPG basligi ve diger gruplar: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("===================================")
    return True

# ==================================================
# ANA PROGRAM
# ==================================================

async def main():
    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadi!")
        return
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        results = []
        bulunamayan = []
        try:
            for series in DIZILER:
                result = await dizi_bul(browser, series)
                if result is None:
                    bulunamayan.append(series["name"])
                    continue
                if result.get("unavailable"):
                    bulunamayan.append(series["name"])
                    continue
                results.append(result)
        finally:
            await browser.close()

    if not results:
        print("Hicbir dizide acik HLS adresi bulunamadi. M3U degistirilmedi.")
        return
    listeyi_guncelle(results, bulunamayan)

if __name__ == "__main__":
    asyncio.run(main())
