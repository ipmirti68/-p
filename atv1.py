# atv1_daion.py - MIRTI68 - SADECE DAION 1080p
import asyncio, re, requests
from playwright.async_api import async_playwright

URL = "https://www.atv.com.tr/canli-yayin"
OUTPUT = "mirti68.m3u"

BLOCKED = ["google","doubleclick","yandex","sharethrough","inmobi","pubmatic","rubicon","zemanta","colossus","iqzone","krushmedia","adkernel","sync.","usync","cs.","match.","ads.","adman","criteo","outbrain","taboola","amazon-adsystem","media.net","aniview","eskimi","apester","kueez","cootlogix","omnitagjs","admatic","drift-pixel","serverbid","peer-39","tynt","e-planning","onetag","sundaysky","gumgum","rlcdn","adblockDetect","mraid.js"]
def is_ad(u): return any(k in u.lower() for k in BLOCKED)

def resolve_daion_variant(master_url):
    """daion master m3u8'in icinden _1080p varyantini cikar"""
    try:
        r = requests.get(master_url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        txt = r.text
        # icinde atv_1080p.m3u8?... var mi?
        m = re.findall(r'(atv_1080p\.m3u8[^\s"\']+)', txt)
        if m:
            variant = m[0]
            # goreceli ise mutlak yap
            if variant.startswith("http"):
                return variant
            base = master_url.split("atv.m3u8")[0]  # .../atv/
            # master'da query varsa onu da tasi
            if "?" in master_url:
                q = master_url.split("?",1)[1]
                # variant zaten query iceriyorsa ekleme
                if "?" not in variant:
                    variant = variant + "?" + q
            return base + variant
        # 720p dene
        m2 = re.findall(r'(atv_720p\.m3u8[^\s"\']+)', txt)
        if m2:
            return master_url.split("atv.m3u8")[0] + m2[0]
        return master_url
    except Exception as e:
        print(f" [VARYANT HATASI] {e}")
        return master_url

async def main():
    print(" [*] ATV DAION araniyor...")
    found=[]; seen=set()
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True)
        page=await b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        async def on_resp(r):
            u=r.url
            if ".m3u8" in u and u not in seen:
                seen.add(u); found.append(u); print(f" [BULUNDU] {u[:130]}")
        page.on("response", on_resp)
        async def rh(route):
            await route.abort() if is_ad(route.request.url) else await route.continue_()
        await page.route("**/*", rh)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(15)
        except Exception as e: print(" Sayfa hatasi:", e)
        finally: await b.close()

    print(f"\n [*] Toplam {len(found)} link")
    for u in found: print("  -", u[:130])

    # ONCELIK SIRASI - ERCDN EN SONA ATILDI
    # 1. daion + _1080p (senin istedigin)
    # 2. daion + _720p
    # 3. daion + atv.m3u8 (master, icinden varyant cikartilacak)
    # 4. ercdn (sadece yedek)
    daion_1080 = next((u for u in found if "daioncdn.net" in u and "atv_1080p" in u), None)
    daion_720 = next((u for u in found if "daioncdn.net" in u and "atv_720p" in u), None)
    daion_master = next((u for u in found if "daioncdn.net" in u and "/atv/atv.m3u8" in u), None)

    final = None
    kaynak = ""
    if daion_1080:
        final = daion_1080; kaynak = "DAION 1080p direkt"
    elif daion_720:
        final = daion_720; kaynak = "DAION 720p direkt"
    elif daion_master:
        print(f" [*] Master bulundu, icinden 1080p cikartiliyor: {daion_master[:100]}")
        final = resolve_daion_variant(daion_master); kaynak = "DAION master -> 1080p cozuldu"
    else:
        print(" [!] DAION bulunamadi, yedek ERCDN kullaniliyor (bos gorunebilir)")
        final = next((u for u in found if "ercdn" in u and "atvhd" in u), found[0] if found else None)
        kaynak = "ERCDN YEDEK"

    if not final:
        print(" [HATA] Hic link yok"); return

    print(f"\n [SECILDI - {kaynak}]")
    print(final)

    # Test
    try:
        r = requests.get(final, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        print(f" [TEST] HTTP {r.status_code} - {len(r.text)} karakter - #EXTM3U var mi? {'#EXTM3U' in r.text}")
    except Exception as e: print(f" [TEST] {e}")

    m3u = '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/iptv-org/epg/master/epg.xml"\n'
    m3u += '#EXTINF:-1 tvg-id="atv.tr" tvg-name="ATV" tvg-logo="https://i.tmgrup.com.tr/atv/logo.png" group-title="Ulusal",ATV\n'
    m3u += '#EXTVLCOPT:http-referrer=https://www.atv.com.tr/\n'
    m3u += '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36\n'
    m3u += f"{final}\n"

    open(OUTPUT,"a",encoding="utf-8").write(m3u)
    print(f" [OK] {OUTPUT} yazildi")
    print(" NOT: Bu link de token'li, 1-2 saate duser. Bos gorunurse scripti tekrar calistir.")

if __name__=="__main__": asyncio.run(main())
