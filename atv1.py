# atv1_temiz.py - MIRTI68 ATV CANLI YAYIN (Temiz Log Versiyonu)
# Sadece m3u8 bulur, reklam/tracker hatalarini gostermez

import re
import asyncio
from playwright.async_api import async_playwright

URL = "https://www.atv.com.tr/canli-yayin"
OUTPUT = "mirti68.m3u"

# Reklam / tracker domainleri - bunlari hic loglama, hic bekleme
BLOCKED_KEYWORDS = [
    "google", "doubleclick", "g.doubleclick", "googlesyndication",
    "yandex", "sharethrough", "inmobi", "pubmatic", "rubicon",
    "zemanta", "colossus", "iqzone", "krushmedia", "adkernel",
    "sync.", "usync", "cs.", "match.", "ads.", "adman", "criteo",
    "outbrain", "taboola", "amazon-adsystem", "media.net",
    "aniview", "eskimi", "apester", "kueez", "cootlogix",
    "omnitagjs", "admatic", "drift-pixel", "serverbid",
    "peer-39", "tynt", "e-planning", "onetag", "sundaysky",
    "gumgum", "rlcdn", "adblockDetect", "mraid.js"
]

def is_ad(url: str) -> bool:
    u = url.lower()
    return any(k in u for k in BLOCKED_KEYWORDS)

async def main():
    print("="*45)
    print("       MIRTI68 - ATV CANLI YAYIN")
    print("="*45)
    print("[*] ATV sayfasi aciliyor...")

    found = []
    seen = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )

        # Sadece m3u8 iceren response'lari topla
        async def on_response(resp):
            url = resp.url
            if ".m3u8" in url and url not in seen:
                seen.add(url)
                found.append(url)
                print(f"[BULUNDU] {url}")

        page.on("response", on_response)

        # Reklam isteklerini engelle - sayfa daha hizli acilir, log kirlenmez
        async def route_handler(route):
            url = route.request.url
            if is_ad(url):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

        # requestfailed'i TAMAMEN sustur - artik loga dusmez
        # page.on("requestfailed", ...) EKLEMEDIK, o yuzden sessiz

        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            print("[+] Sayfa acildi, yayin adresleri bekleniyor...")
            await asyncio.sleep(12)  # token'li linkin olusmasi icin bekle
        except Exception as e:
            print(f"[!] Sayfa acilirken hata: {e}")
        finally:
            await browser.close()

    print(f"\n[*] Bulunan toplam M3U8: {len(found)}")

    # ATV secimi - once token'li daion linki, sonra digerleri
    atv_url = None
    for u in found:
        if "daioncdn.net/atv/atv.m3u8" in u and "app=" in u and len(u) > 60:
            atv_url = u
            break
    if not atv_url:
        for u in found:
            if "/atv/atv.m3u8" in u:
                atv_url = u
                break
    if not atv_url:
        for u in found:
            if "atvhd" in u and "st=" in u:
                atv_url = u
                break

    if atv_url:
        print("[SECILDI - DAION]")
        print("[+] ATV ADRESI BULUNDU:")
        print(atv_url)
        print("[OK] ATV listeye eklendi.")

        # M3U dosyasi yaz
        content = "#EXTM3U\n"
        content += f'#EXTINF:-1 tvg-name="ATV" tvg-logo="https://i.tmgrup.com.tr/atv/logo.png" group-title="Ulusal",ATV\n{atv_url}\n'
        # Diger bulunanlari da ekle (istege bagli)
        for u in found:
            if u != atv_url:
                name = "ATV HD" if "atvhd" in u else "ATV Yedek"
                content += f'#EXTINF:-1 tvg-name="{name}" group-title="Ulusal",{name}\n{u}\n'

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[OK] {OUTPUT}")
        print(f"[OK] Dosya boyutu: {len(content)} karakter")
    else:
        print("[HATA] ATV adresi bulunamadi!")

    print("="*45)
    print("          ISLEM TAMAMLANDI")
    print("="*45)

if __name__ == "__main__":
    asyncio.run(main())
