import asyncio
import os
import re
import shutil
import codecs
import json
from html import unescape
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ==================================================
# SHOW TV DİZİ OTOMATİK GÜNCELLEYİCİ
# ==================================================

M3U_FILE = "showdizi.m3u"
BASE = "https://www.showtv.com.tr"

SHOW_GROUP = "🟪◆ SHOWTV DİZİLERİ ⭕"
TARGET_GROUP = "🟪◆ SHOW DİZİ 📺⭕"

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"

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
        f'#EXTINF:-1 tvg-name="***** SHOW TV DİZİ *****" tvg-logo="{INFO_LOGO}" group-title="{TARGET_GROUP}",BİLGİLENDİRME',
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
# DİZİ SAYFASINDAN SON BÖLÜMÜ BUL
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
        print(f"\n[DİZİ] {dizi['name']}")

        # ShowTV'de tanıtım sayfası bazen boş geliyor, 3 farklı URL dene
        denenecek = [
            f"{BASE}/dizi/tanitim/{dizi['slug']}",
            f"{BASE}/dizi/{dizi['slug']}",
            f"{BASE}/dizi/tanitim/{dizi['slug']}/bolumler",
        ]

        logo = ""
        aciklama = ""
        adaylar = {}  # bolum_no -> {url, text}

        for url in denenecek:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)
                # Lazy-load kartlar için aşağı kaydır
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2500)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass
            except Exception as e:
                print(f"  Sayfa açılmadı {url}: {e}")
                continue

            # Logo / açıklama ilk sayfadan al
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

            # 1) Normal linkleri tara
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
                # Kendisi değil, bölüm linki olmalı
                if link.rstrip("/") == url.rstrip("/"):
                    continue

                bolum_no = None

                # A) Yazıda "12. Bölüm" varsa
                m = re.search(r'(\d+)\s*\.?\s*bölüm', text, re.I)
                if m:
                    bolum_no = int(m.group(1))
                # B) URL'de /12-bolum, /bolum-12, /12.bolum, /bolum/12
                if bolum_no is None:
                    m2 = re.search(r'/(?:bolum[-_/])?(\d+)(?:-bolum|/bolum)?(?:/|$)', low_link)
                    # Sadece slug'dan sonra bölüm numarası geliyorsa al
                    # Örn: /dizi/tanitim/kizilcik-serbeti/125-bolum
                    m3 = re.search(rf"{re.escape(dizi['slug'])}[^0-9]*(\d+)", low_link)
                    if m3:
                        # Tanıtım sayfasının kendisi değilse
                        if "/bolum" in low_link or "-bolum" in low_link or re.search(r'/\d+/?$', low_link):
                            bolum_no = int(m3.group(1))
                if bolum_no is None:
                    continue
                if bolum_no <= 0 or bolum_no > 500:
                    continue

                if bolum_no not in adaylar:
                    adaylar[bolum_no] = {"url": link, "text": text or f"{bolum_no}. Bölüm"}

            # 2) Sayfa kaynağında __NEXT_DATA__ / JSON içinde bölüm linki varsa
            if not adaylar:
                try:
                    html = await page.content()
                    # /dizi/.../xxx-bolum kalıplarını ham html'den de ara
                    for mm in re.finditer(rf'https?://www\.showtv\.com\.tr/[^\s"\'<>]*{re.escape(dizi["slug"])}[^\s"\'<>]*?(\d+)[^\s"\'<>]*?bolum[^\s"\'<>]*', html, re.I):
                        full = mm.group(0).replace("\\/", "/")
                        try:
                            no = int(mm.group(1))
                            if no not in adaylar and "fragman" not in full.lower():
                                adaylar[no] = {"url": full, "text": f"{no}. Bölüm"}
                        except Exception:
                            pass
                except Exception:
                    pass

            if adaylar:
                print(f"  {len(adaylar)} aday bulundu, kaynak: {url}")
                break

        if not adaylar:
            print(f"[BÖLÜM BEKLENİYOR] {dizi['name']} - link bulunamadı, eski kayıt korunacak")
            return {"unavailable": True, "name": dizi["name"]}

        son_bolum = max(adaylar)
        hedef = adaylar[son_bolum]["url"]
        bolum_adi = adaylar[son_bolum]["text"]
        # Bölüm adı düzgün değilse düzelt
        if not re.search(r'bölüm', bolum_adi, re.I):
            bolum_adi = f"{son_bolum}. Bölüm"

        print(f"[SON BÖLÜM] {son_bolum} - {hedef}")

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

        # HLS tara
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
            print(f"[HLS BULUNAMADI] {dizi['name']} - eski kayıt korunacak")
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
# M3U KAYITLARINI KORUYARAK YERLEŞTİR
# ==================================================

def listeyi_guncelle(yeni_diziler, bulunamayan_isimler):
    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
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

    # SHOWTV bilgilendirme anchor
    anchor = None
    for i, record in enumerate(records):
        if grup_bul(record) == SHOW_GROUP and "BİLGİLENDİRME" in kanal_adi(record).upper():
            anchor = i
            break
    if anchor is None:
        print("[HATA] SHOWTV bilgilendirme kaydı bulunamadı!")
        print("Dosya değiştirilmedi.")
        return False

    # Eski SHOW DİZİ kayıtları
    eski_show = [r for r in records if grup_bul(r) == TARGET_GROUP]
    eski_info = None
    eski_diziler = []  # BİLGİLENDİRME hariç eski dizi kayıtları
    for r in eski_show:
        if "BİLGİLENDİRME" in kanal_adi(r).upper():
            eski_info = r
        else:
            eski_diziler.append(r)

    if eski_info is None:
        eski_info = info_kaydi()

    # Yeni bulunan dizi isimleri
    yeni_isimler = set(d["name"] for d in yeni_diziler)

    # Bulunamayan dizilerin ESKİ kaydını koru
    korunan = []
    for r in eski_diziler:
        ad = kanal_adi(r)
        # Eski kayıtta hangi dizi olduğunu bul
        koru = False
        for isim in bulunamayan_isimler:
            # "KIZILCIK ŞERBETİ - 125. Bölüm" içinde "KIZILCIK ŞERBETİ" var mı?
            if isim in ad:
                koru = True
                break
        if koru:
            korunan.append(r)
            print(f"  KORUNDU (eski): {ad}")

    # Sadece hedef grubu çıkar, diğerleri kalsın
    digerleri = [r for r in records if grup_bul(r) != TARGET_GROUP]

    # Anchor'ı tekrar bul
    anchor = None
    for i, record in enumerate(digerleri):
        if grup_bul(record) == SHOW_GROUP and "BİLGİLENDİRME" in kanal_adi(record).upper():
            anchor = i
            break
    if anchor is None:
        return False

    yeni_kayitlar = [eski_info]
    for dizi in yeni_diziler:
        yeni_kayitlar.append(dizi_kaydi(dizi))
    # Korunan eski kayıtları da ekle - tekrar olmasın diye yeni isimlerde yoklar zaten
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
    print("SHOW DİZİ GÜNCELLEME TAMAMLANDI")
    print("===================================")
    print("Grup:", TARGET_GROUP)
    print("Yenilenen:", len(yeni_diziler))
    print("Korunan eski:", len(korunan))
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
        bulunamayan = []

        try:
            for dizi in DIZILER:
                sonuc = await dizi_bul(browser, dizi)
                # Artık iptal yok - biri patlarsa diğerine devam
                if sonuc is None:
                    print(f"{dizi['name']} atlandı, diğerine geçiliyor")
                    bulunamayan.append(dizi["name"])
                    continue
                if sonuc.get("unavailable"):
                    bulunamayan.append(dizi["name"])
                    continue
                yeni_diziler.append(sonuc)
        finally:
            await browser.close()

        # Hiçbiri bulunamadıysa bile dosyayı bozma, eski kayıtlar aynen kalsın
        if not yeni_diziler and not bulunamayan:
            print("Hiç dizi işlenemedi.")
            return

        # Yeni bulunan yoksa ama eskiler varsa, dosyayı boşuna yazma
        if not yeni_diziler:
            print("Henüz yayınlanmış yeni bölüm bulunamadı.")
            print("Eski liste aynen korunuyor, dosya değiştirilmedi.")
            return

        listeyi_guncelle(yeni_diziler, bulunamayan)

if __name__ == "__main__":
    asyncio.run(main())
