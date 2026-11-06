# atv1_daion.py - MIRTI68 - SADECE DAION 1080p (v3 - BODY + RESPONSE + TOKEN)
import asyncio, re, requests, os
from playwright.async_api import async_playwright

URL = "https://www.atv.com.tr/canli-yayin"
OUTPUT = "mirti68.m3u"

BLOCKED = ["google","doubleclick","yandex","sharethrough","inmobi","pubmatic","rubicon","zemanta","colossus","iqzone","krushmedia","adkernel","sync.","usync","cs.","match.","ads.","adman","criteo","outbrain","taboola","amazon-adsystem","media.net","aniview","eskimi","apester","kueez","cootlogix","omnitagjs","admatic","drift-pixel","serverbid","peer-39","tynt","e-planning","onetag","sundaysky","gumgum","rlcdn","adblockDetect","mraid.js"]
def is_ad(u):
    # DIKKAT: daion / ercdn / tmgrup / securevideotoken ASLA engellenmez
    if "daioncdn" in u or "ercdn" in u or "tmgrup" in u or "securevideotoken" in u:
        return False
    return any(k in u.lower() for k in BLOCKED)

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
    except Exception as e:
        print(f" [VARYANT HATASI] {e}")
        return master_url

def call_secure_token(token_url):
    """securevideotoken linkinden token'li daion linkini cikar"""
    try:
        r = requests.get(token_url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        # donen icerikte daion linki olabilir
        m = re.findall(r'https://[^\s"\'\\]+daioncdn[^\s"\'\\]+', r.text)
        if m: return m[0]
        # bazen json: {"url": "..."}
        m2 = re.findall(r'https://[^\s"\'\\]+\.m3u8[^\s"\'\\]*', r.text)
        if m2: return m2[0]
        return None
    except Exception as e:
        print(f" [TOKEN HATASI] {e}")
        return None

def update_m3u_smart(output_path, new_atv_url):
    if not os.path.exists(output_path):
        content = "#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/iptv-org/epg/master/epg.xml\"\n"
    else:
        with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    lines = content.splitlines(); new_lines=[]; i=0; removed=0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF") and ('tvg-name="ATV"' in line or ',ATV' in line or ',ATV HD' in line):
            removed+=1; i+=1
            while i < len(lines) and (lines[i].startswith("#EXTVLCOPT") or lines[i].startswith("http") or lines[i].strip()==""):
                if lines[i].strip()=="": break
                i+=1
            continue
        if line.startswith("http") and ("daioncdn.net/atv/" in line or "ercdn.net/atvhd" in line or "securevideotoken" in line):
            removed+=1; i+=1; continue
        new_lines.append(line); i+=1
    atv_block = [
        '#EXTINF:-1 tvg-id="atv.tr" tvg-name="ATV" tvg-logo="https://i.tmgrup.com.tr/atv/logo.png" group-title="Ulusal",ATV',
        '#EXTVLCOPT:http-referrer=https://www.atv.com.tr/',
        '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
        new_atv_url,
    ]
    out=[]; inserted=False
    for line in new_lines:
        out.append(line)
        if not inserted and line.startswith("#EXTM3U"):
            out.extend(atv_block); inserted=True
    if not inserted: out = ["#EXTM3U"] + atv_block + out
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out)+"\n")
    print(f" [OK] {removed} adet eski/olu ATV silindi, 1 adet yeni ATV eklendi")
    print(f" [OK] Diger kanallar aynen korundu - toplam satir: {len(out)}")

async def main():
    print(" [*] ATV DAION araniyor...")
    found=[]; seen=set()
    def add(u, src=""):
        if u and ".m3u8" in u and u not in seen:
            seen.add(u); found.append(u); print(f" [BULUNDU-{src}] {u[:140]}")

    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True)
        page=await b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        # 1) RESPONSE
        async def on_resp(r): add(r.url, "RESP")
        page.on("response", on_resp)
        # 2) REQUEST - secure token istegi bile yakalanir
        def on_req(req): add(req.url, "REQ")
        page.on("request", on_req)
        async def rh(route):
            await route.abort() if is_ad(route.request.url) else await route.continue_()
        await page.route("**/*", rh)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            print(" [+] Sayfa acildi, player bekleniyor (25sn)...")
            await asyncio.sleep(10)
            # Player'a tiklamaya calis - token o zaman uretiliyor
            try:
                await page.mouse.click(640, 360)
            except: pass
            await asyncio.sleep(15)
            # 3) BODY - sayfa kaynagindaki gomulu daion linkleri
            html = await page.content()
            for m in re.findall(r'https://[^\s"\'\\]+daioncdn[^\s"\'\\]*\.m3u8[^\s"\'\\]*', html):
                add(m.replace("\\u0026","&").replace("&amp;","&"), "BODY")
            for m in re.findall(r'https://[^\s"\'\\]+securevideotoken[^\s"\'\\]+', html):
                print(f" [TOKEN LINKI] {m[:140]}")
                tok = call_secure_token(m.replace("\\u0026","&").replace("&amp;","&"))
                if tok: add(tok, "TOKEN-COZULDU")
        except Exception as e: print(" Sayfa hatasi:", e)
        finally: await b.close()

    print(f"\n [*] Toplam {len(found)} link")
    for u in found: print("  -", u[:140])

    daion_1080 = next((u for u in found if "daioncdn" in u and "atv_1080p" in u), None)
    daion_720 = next((u for u in found if "daioncdn" in u and "atv_720p" in u), None)
    # master: /atv/atv.m3u8 - ama _1080p olmayan
    daion_master = next((u for u in found if "daioncdn" in u and "/atv/atv.m3u8" in u), None)

    final=None; kaynak=""
    if daion_1080: final=daion_1080; kaynak="DAION 1080p direkt"
    elif daion_720: final=daion_720; kaynak="DAION 720p direkt"
    elif daion_master:
        print(f" [*] Master bulundu, icinden 1080p cikartiliyor")
        final=resolve_daion_variant(daion_master); kaynak="DAION master -> 1080p"
    else:
        print(" [!] DAION bulunamadi!")
        print("     Sebep genelde: sayfa bot olarak algiladi veya player baslatilmadi")
        print("     Cozum: 1 dk bekleyip tekrar dene, veya headless=False yap")
        # yedek ercdn varsa yine de yaz ama uyar
        ercdn = next((u for u in found if "ercdn" in u and "atvhd" in u), None)
        if ercdn:
            print(" [!] Yedek ERCDN yaziliyor (bos gorunebilir)")
            final=ercdn; kaynak="ERCDN YEDEK"
        else:
            print(" [HATA] Hic link yok, dosya degistirilmedi")
            return

    print(f"\n [SECILDI - {kaynak}]"); print(final)
    try:
        r=requests.get(final, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        print(f" [TEST] HTTP {r.status_code} - {len(r.text)} karakter - #EXTM3U var mi? {'#EXTM3U' in r.text}")
    except Exception as e: print(f" [TEST] {e}")

    update_m3u_smart(OUTPUT, final)
    print(" [BITTI] Oynaticiyi kapatip ac.")

if __name__=="__main__": asyncio.run(main())
