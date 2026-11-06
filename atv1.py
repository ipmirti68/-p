# atv1.py - MIRTI68 - Senin bookmarklet mantigiyla calisir
# Mantik: performance + innerHTML + video tagi tara -> DAION 1080p sec -> listeyi bozmadan guncelle
import asyncio, re, requests, os
from playwright.async_api import async_playwright

URL = "https://www.atv.com.tr/canli-yayin"
OUTPUT = "mirti68.m3u"

# === SENIN BOOKMARKLET'ININ AYNISI, AMA ATV'YE OZEL - PLAYWRIGHT ICINDE CALISIR ===
BOOKMARKLET_JS = r"""
() => {
  let u = new Set();
  // 1) performance - networkte akan m3u8'ler
  try { performance.getEntriesByType('resource').forEach(r => {
    if (r.name.includes('.m3u8') || r.name.includes('.mpd')) u.add(r.name);
  }); } catch(e) {}
  // 2) sayfa kaynagi - BODY'ye gomulu linkler
  let h = document.documentElement.innerHTML;
  let re = /https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/gi;
  let m = h.match(re);
  if (m) m.forEach(x => u.add(x));
  // 3) securevideotoken linkleri de topla
  let re2 = /https?:\/\/[^"'\s]+securevideotoken[^"'\s]*/gi;
  let m2 = h.match(re2);
  let tokens = m2 ? [...new Set(m2)] : [];
  // 4) video / source taglari
  document.querySelectorAll('video,source').forEach(v => {
    if (v.src) u.add(v.src);
    if (v.currentSrc) u.add(v.currentSrc);
  });
  // 5) script taglarinin ici - player config genelde burada
  document.querySelectorAll('script').forEach(s => {
    let t = s.textContent || '';
    let mm = t.match(/https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/gi);
    if (mm) mm.forEach(x => u.add(x));
  });
  return { links: [...u], tokens: tokens };
}
"""

def clean(u):
    return u.replace("\\u0026","&").replace("&amp;","&").replace("\\/","/").strip().strip("'\"")

def resolve_daion_variant(master_url):
    try:
        r = requests.get(master_url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        for q in ["atv_1080p.m3u8","atv_720p.m3u8"]:
            m = re.findall(r'(' + re.escape(q) + r'[^\s"\']+)', r.text)
            if m:
                v = clean(m[0])
                if v.startswith("http"): return v
                base = master_url.split("atv.m3u8")[0]
                if "?" not in v and "?" in master_url: v = v + "?" + master_url.split("?",1)[1]
                return base + v
        return master_url
    except Exception as e:
        print(f" [VARYANT HATASI] {e}"); return master_url

def update_m3u_smart(output_path, new_atv_url):
    if not os.path.exists(output_path):
        content = "#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/iptv-org/epg/master/epg.xml\"\n"
    else:
        content = open(output_path, "r", encoding="utf-8", errors="ignore").read()
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
    open(output_path, "w", encoding="utf-8").write("\n".join(out)+"\n")
    print(f" [OK] {removed} adet eski/olu ATV silindi, 1 adet yeni ATV eklendi")
    print(f" [OK] Diger kanallar aynen korundu - toplam satir: {len(out)}")

async def main():
    print(" [*] ATV DAION araniyor - bookmarklet mantigi...")
    found=[]
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False)  # headless=False: site bot sanmasin, sen de goreceksin
        page = await b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        print(" [+] Sayfa acildi. Canliyi baslat butonuna basarsan daha iyi, 15sn bekleniyor...")
        await asyncio.sleep(15)
        # SENIN BOOKMARKLET'INI SAYFANIN ICINDE CALISTIR
        res = await page.evaluate(BOOKMARKLET_JS)
        found = [clean(x) for x in res.get("links",[])]
        tokens = [clean(x) for x in res.get("tokens",[])]
        print(f" [*] Bookmarklet {len(found)} link buldu, {len(tokens)} token linki")
        for u in found: print("  -", u[:140])
        # Token varsa onu da coz
        for t in tokens:
            try:
                r = requests.get(t, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
                for mm in re.findall(r'https://[^\s"\'\\]+daioncdn[^\s"\'\\]+', r.text):
                    c = clean(mm)
                    if c not in found: found.append(c); print(f"  - TOKENDEN: {c[:140]}")
            except Exception as e: print(f" [TOKEN] {e}")
        await b.close()

    daion_1080 = next((u for u in found if "daioncdn" in u and "atv_1080p" in u), None)
    daion_720 = next((u for u in found if "daioncdn" in u and "atv_720p" in u), None)
    daion_master = next((u for u in found if "daioncdn" in u and "/atv/atv.m3u8" in u), None)
    if daion_1080: final=daion_1080; kaynak="DAION 1080p"
    elif daion_720: final=daion_720; kaynak="DAION 720p"
    elif daion_master:
        print(" [*] Master bulundu, icinden 1080p cikartiliyor...")
        final=resolve_daion_variant(daion_master); kaynak="DAION master -> 1080p"
    else:
        print(" [!] DAION bulunamadi! Canliyi baslat butonuna basip tekrar dene.")
        if not found: print(" [HATA] Hic link yok"); return
        final=found[0]; kaynak="ILK BULUNAN (YEDEK)"
    print(f"\n [SECILDI - {kaynak}]\n{final}")
    try:
        r=requests.get(final, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        print(f" [TEST] HTTP {r.status_code} - #EXTM3U var mi? {'#EXTM3U' in r.text}")
    except Exception as e: print(f" [TEST] {e}")
    update_m3u_smart(OUTPUT, final)

if __name__=="__main__": asyncio.run(main())
