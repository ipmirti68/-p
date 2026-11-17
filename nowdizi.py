import asyncio
import os
import re
import shutil
import codecs
from html import unescape
from playwright.async_api import async_playwright

# ==================================================
# NOW TV DIZI - DUZELTILMIS SURUM
# ==================================================

M3U_FILE = "mirti68.m3u"
BASE = "https://www.nowtv.com.tr"

TARGET_GROUP = "🟪◆  NOW DİZİ 📺⭕"
# NOW ana kanalının olduğu grup - diziler bunun hemen altına eklenir
NOW_GROUP = "🟪◆  NOW DİZİ 📺⭕"

INFO_URL = "https://raw.githubusercontent.com/ipmirti68/-p/main/bilgi.mp4"
INFO_LOGO = "https://www.freepnglogos.com/uploads/turk-bayragi-png/turk-bayragi-hareketli-bayrak-gif-turkey-wavy-flag-png-27.png"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"

# SENIN VERDIGIN DOGRU SAYFALAR - slug ile arama yok, direkt /izle
DIZILER = [
    {"page": "https://www.nowtv.com.tr/Halef-Koklerin-Cagrisi/izle", "name": "HALEF"},
    {"page": "https://www.nowtv.com.tr/Yeralti/izle", "name": "YERALTİ"},
    {"page": "https://www.nowtv.com.tr/Sevdam-Karadeniz/izle", "name": "SEVDAM KARADENİZ"},
    {"page": "https://www.nowtv.com.tr/Omur-Usta/izle", "name": "ÖMÜR USTA"},
    {"page": "https://www.nowtv.com.tr/Adana-Ayazi/izle", "name": "ADANA AYAZI"},
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
# /izle SAYFASINDAN SON BOLUMU BUL
# ==================================================

async def dizi_bul(browser, dizi):
    page = await browser.new_page(user_agent=UA)
    hls_adresleri = set()

    def adres_yakala(adres):
        adres = temizle(adres).replace("\\/", "/").replace("\\u0026", "&")
        # Senin örneğin: ...smil/playlist.m3u8?st=...
        # Önce smil/playlist olanı tercih et, sonra diğer m3u8'leri al
        if ".m3u8" in adres.lower() and adres.startswith("http"):
            # reklam / fragman / teaser ele
            low = adres.lower()
            if "fragman" in low or "teaser" in low or "tanitim" in low:
                return
            hls_adresleri.add(adres)

    page.on("request", lambda r: adres_yakala(r.url))
    page.on("response", lambda r: adres_yakala(r.url))

    try:
        print(f"\n[DIZI] {dizi['name']} -> {dizi['page']}")

        await page.goto(dizi["page"], wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        # LOGO + ACIKLAMA - dizi sayfasından al
        logo = ""
        aciklama = ""
        try:
            logo = await page.locator('meta[property="og:image"]').first.get_attribute("content") or ""
        except: pass
        try:
            aciklama = await page.locator('meta[name="description"]').first.get_attribute("content") or ""
        except: pass
        if not logo:
            try:
                logo = await page.locator('meta[name="twitter:image"]').first.get_attribute("content") or ""
            except: pass

        # 1. SON BOLUM LINKINI BUL - sayfadaki "Son Bölüm İzle" / "Bölüm" linkleri
        son_bolum_url = None
        son_bolum_no = 0
        son_bolum_text = ""

        try:
            links = await page.locator("a[href]").evaluate_all(
                """els => els.map(a => ({
                    url: a.href,
                    text: (a.innerText || a.textContent || '').trim()
                }))"""
            )
        except:
            links = []

        for item in links:
            link = item["url"] or ""
            text = item["text"] or ""
            low_link = link.lower()
            low_text = text.lower()
            if "fragman" in low_text or "fragman" in low_link:
                continue
            # sadece /bolumler/ içeren linkler = gerçek bölüm
            if "/bolumler/" not in low_link:
                continue
            # bölüm no çıkar: /bolumler/4/ veya 4. Bölüm
            m = re.search(r'/bolumler/(\d+)', low_link)
            if not m:
                continue
            no = int(m.group(1))
            if no > son_bolum_no:
                son_bolum_no = no
                son_bolum_url = link
                son_bolum_text = text

        # Eğer link bulunamadıysa, sayfadaki butonlara tıkla
        if not son_bolum_url:
            print("  Link listede bulunamadi, buton deneniyor...")
            for sel in ["text=Son Bölüm İzle", "text=Son Bölümü İzle", "text=Bölümleri İzle", "a:has-text('İzle')"]:
                try:
                    await page.locator(sel).first.click(timeout=3000)
                    await page.wait_for_timeout(4000)
                    break
                except: pass
            # tıkladıktan sonra URL değiştiyse o URL bölüm sayfasıdır
            cur = page.url
            if "/bolumler/" in cur:
                son_bolum_url = cur
                m = re.search(r'/bolumler/(\d+)', cur)
                son_bolum_no = int(m.group(1)) if m else 0
        else:
            print(f"  [SON BOLUM] {son_bolum_no}. Bölüm -> {son_bolum_url}")

        if not son_bolum_url:
            print(f"[BOLUM BULUNAMADI] {dizi['name']} - eski kayit korunacak")
            return {"unavailable": True, "name": dizi["name"]}

        # 2. BÖLÜM SAYFASINA GİT VE m3u8 YAKALA
        await page.goto(son_bolum_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        # bölüm sayfasından daha iyi açıklama / tarih al
        try:
            desc = await page.locator('meta[name="description"]').first.get_attribute("content")
            if desc: aciklama = desc
        except: pass
        try:
            og_img = await page.locator('meta[property="og:image"]').first.get_attribute("content")
            if og_img: logo = og_img
        except: pass

        tarih = ""
        for sel in ['meta[property="article:published_time"]', 'meta[property="og:updated_time"]', 'meta[name="date"]']:
            try:
                tarih = await page.locator(sel).first.get_attribute("content") or ""
                if tarih: break
            except: pass
        if tarih:
            tarih = tarih[:10]  # 2026-11-17

        # Play'e bas + HTML tara
        for _ in range(2):
            html = await page.content()
            html = unescape(html).replace("\\/", "/").replace("\\u0026", "&")
            for adres in re.findall(r'https?://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?', html, re.I):
                adres_yakala(adres)
            for selector in [".jw-icon-play", ".vjs-big-play-button", ".plyr__control--overlaid", "button[aria-label*='Oynat']", "text=Oynat"]:
                try:
                    el = page.locator(selector).first
                    if await el.count():
                        await el.click(timeout=2500, force=True)
                        await page.wait_for_timeout(7000)
                        break
                except: pass
            try:
                await page.locator("video").first.evaluate("(v) => v.play()")
                await page.wait_for_timeout(7000)
            except: pass

        if not hls_adresleri:
            print(f"[HLS BULUNAMADI] {dizi['name']} - eski kayit korunacak")
            return {"unavailable": True, "name": dizi["name"]}

        # EN İYİ LİNKİ SEÇ: önce smil/playlist.m3u8 olanı, sonra master.m3u8
        def skor(u):
            u_low = u.lower()
            if "smil/playlist.m3u8" in u_low:
                return 0
            if "master.m3u8" in u_low:
                return 1
            return 2
        sirali = sorted(hls_adresleri, key=lambda x: (skor(x), len(x)))
        print("[HLS BULUNDU]", sirali[0][:120])

        episode = f"{son_bolum_no}. Bölüm" if son_bolum_no else son_bolum_text

        return {
            "name": dizi["name"],
            "logo": logo or BASE + "/favicon.ico",
            "description": aciklama,
            "episode": episode,
            "date": tarih,
            "url": sirali[0]
        }

    except Exception as e:
        print("[HATA]", dizi["name"], str(e))
        return {"unavailable": True, "name": dizi["name"]}
    finally:
        await page.close()

# ==================================================
# M3U - DIGER GRUPLARA DOKUNMADAN YERLESTIR
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

    # EPG + BASLIK KORU: ilk #EXTINF'e kadar her şey aynen kalır
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

    # Eski NOW DİZİ grubunu ayır
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
        if any(isim in ad for isim in bulunamayan_isimler):
            korunan.append(r)
            print(f"  KORUNDU (eski): {ad}")

    digerleri = [r for r in records if grup_bul(r) != TARGET_GROUP]

    # DİZİLER NEREYE EKLENECEK? NOW ana kanalının olduğu grubun sonuna
    # Yoksa en başa - ama diğer gruplar asla bozulmaz
    anchor = None
    for i, record in enumerate(digerleri):
        if grup_bul(record) == NOW_GROUP:
            anchor = i  # sonuncuyu bulmak için devam et, üzerine yazacağız
    # NOW_GROUP'un son kaydını bul
    if anchor is not None:
        last_now = max(i for i, r in enumerate(digerleri) if grup_bul(r) == NOW_GROUP)
        anchor = last_now
    else:
        # NOW grubu yoksa, ilk kaydın önüne koy
        anchor = -1

    yeni_kayitlar = [eski_info]
    for dizi in yeni_diziler:
        yeni_kayitlar.append(dizi_kaydi(dizi))
    yeni_kayitlar.extend(korunan)

    if anchor == -1:
        son_records = yeni_kayitlar + digerleri
    else:
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
                if sonuc.get("unavailable"):
                    bulunamayan.append(dizi["name"])
                    continue
                yeni_diziler.append(sonuc)
        finally:
            await browser.close()
        if not yeni_diziler:
            print("Yeni bolum bulunamadi. Dosya degistirilmedi.")
            return
        listeyi_guncelle(yeni_diziler, bulunamayan)

if __name__ == "__main__":
    asyncio.run(main())
