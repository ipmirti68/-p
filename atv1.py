# atv1_daion.py - MIRTI68 - Mevcut listeyi BOZMADAN gunceller
# w = hepsini siler, a = surekli ekler / siser
# Bu: sadece ATV satirini degistirir, diger kanallara DOKUNMAZ

import asyncio, re, requests, os
from playwright.async_api import async_playwright

URL = "https://www.atv.com.tr/canli-yayin"
OUTPUT = "mirti68.m3u"  # mevcut listen

BLOCKED = ["google","doubleclick","yandex","sharethrough","inmobi","pubmatic","rubicon","zemanta","colossus","iqzone","krushmedia","adkernel","sync.","usync","cs.","match.","ads.","adman","criteo","outbrain","taboola","amazon-adsystem","media.net","aniview","eskimi","apester","kueez","cootlogix","omnitagjs","admatic","drift-pixel","serverbid","peer-39","tynt","e-planning","onetag","sundaysky","gumgum","rlcdn","adblockDetect","mraid.js"]
def is_ad(u): return any(k in u.lower() for k in BLOCKED)

def resolve_daion_variant(master_url):
    try:
        r = requests.get(master_url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        for q in ["atv_1080p.m3u8", "atv_720p.m3u8"]:
            m = re.findall(r'(' + re.escape(q) + r'[^\s"\']+)', r.text)
            if m:
                v = m[0]
                if v.startswith("http"): return v
                base = master_url.split("atv.m3u8")[0]
                if "?" not in v and "?" in master_url:
                    v = v + "?" + master_url.split("?",1)[1]
                return base + v
        return master_url
    except Exception: return master_url

def update_m3u_smart(output_path, new_atv_url):
    """Mevcut listeyi bozma: sadece ATV bloklarini sil, yeni ATV'yi en basa ekle"""
    if not os.path.exists(output_path):
        print(f" [!] {output_path} yok, sifirdan olusturuluyor")
        content = "#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/iptv-org/epg/master/epg.xml\"\n"
    else:
        with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    lines = content.splitlines()
    new_lines = []
    i = 0
    removed = 0
    while i < len(lines):
        line = lines[i]
        # ATV blogu mu? #EXTINF satirinda ATV yaziyorsa ve bir sonraki satir linkse, o 3-4 satiri atla
        if line.startswith("#EXTINF") and ('tvg-name="ATV"' in line or ',ATV' in line or ',ATV HD' in line):
            removed += 1
            i += 1
            # altindaki VLCCOPT ve URL satirlarini da atla
            while i < len(lines) and (lines[i].startswith("#EXTVLCOPT") or lines[i].startswith("http") or lines[i].strip() == ""):
                # bos satirda dur, bir sonraki EXTINF'e dokunma
                if lines[i].strip() == "":
                    break
                i += 1
            continue
        # Eski daion / ercdn ATV linki tek basina kalmissa (EXTINF'siz) onu da sil
        if line.startswith("http") and ("daioncdn.net/atv/" in line or "ercdn.net/atvhd" in line or "securevideotoken" in line):
            removed += 1
            i += 1
            continue
        new_lines.append(line)
        i += 1

    # Yeni ATV blogu
    atv_block = [
        '#EXTINF:-1 tvg-id="atv.tr" tvg-name="ATV" tvg-logo="https://i.tmgrup.com.tr/atv/logo.png" group-title="Ulusal",ATV',
        '#EXTVLCOPT:http-referrer=https://www.atv.com.tr/',
        '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
        new_atv_url,
    ]

    # #EXTM3U'dan hemen sonra ekle
    out = []
    inserted = False
    for line in new_lines:
        out.append(line)
        if not inserted and line.startswith("#EXTM3U"):
            out.extend(atv_block)
            inserted = True
    if not inserted:
        out = ["#EXTM3U"] + atv_block + out

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print(f" [OK] {removed} adet eski/olu ATV silindi, 1 adet yeni ATV eklendi")
    print(f" [OK] Diger kanallar aynen korundu - toplam satir: {len(out)}")
    return removed

async def main():
    print(" [*] ATV DAION araniyor...")
    found=[]; seen=set()
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True)
        page=await b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        async def on_resp(r):
            u=r.url
            if ".m3u8" in u and u not in seen:
                seen.add(u); found.append(u)
        page.on("response", on_resp)
        async def rh(route):
            await route.abort() if is_ad(route.request.url) else await route.continue_()
        await page.route("**/*", rh)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(15)
        except Exception as e: print(" Sayfa hatasi:", e)
        finally: await b.close()

    daion_1080 = next((u for u in found if "daioncdn.net" in u and "atv_1080p" in u), None)
    daion_720 = next((u for u in found if "daioncdn.net" in u and "atv_720p" in u), None)
    daion_master = next((u for u in found if "daioncdn.net" in u and "/atv/atv.m3u8" in u), None)

    if daion_1080: final = daion_1080
    elif daion_720: final = daion_720
    elif daion_master: final = resolve_daion_variant(daion_master)
    else:
        print(" [!] DAION bulunamadi"); return

    print(f" [SECILDI] {final[:120]}")
    update_m3u_smart(OUTPUT, final)
    print(" [BITTI] Simdi oynaticiyi kapatip ac, liste guncellenecek.")

if __name__=="__main__": asyncio.run(main())
