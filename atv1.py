#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MIRTI68 - ATV Canli - atv1.py - GRUP ALTINA EKLE, TEKRAR EKLEME

import os
import sys
import time
import requests
import urllib3
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"
ORIGIN = "https://www.atv.com.tr"
REFERER = SAYFA_URL
DOSYA = "mirti68.m3u"
KANAL = "ATVᴴᴰ⭕"
TVG_ID = "atv.tr"
LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"
GRUP = "🟨◆  ULUSALᴴᴰ ⭕"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TARAMA_SURESI = 120
TARAYICI_CEREZLERI = {}

def gercek_atv_mi(url):
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        if p.scheme not in ("http", "https"):
            return False
        # Daion'un alt domainleri de olabilir, daraltma
        if "daioncdn.net" not in p.netloc.lower():
            return False
        if ".m3u8" not in p.path.lower():
            return False
        # atv ile ilgili olmayan m3u8'leri ele
        if "/atv/" not in p.path.lower() and "atv" not in p.path.lower():
            return False
        if not p.query:
            return False
        return True
    except Exception:
        return False

def adres_onceligi(url):
    u = url.lower()
    if "/atv/atv_1080p.m3u8" in u:
        return 0
    if "/atv/atv.m3u8" in u:
        return 1
    if "atv_720p" in u:
        return 2
    if "atv_480p" in u:
        return 3
    if "atv" in u:
        return 4
    return 99

def atv_adresi_bul():
    global TARAYICI_CEREZLERI
    bulunan = set()
    tum_m3u8 = set()

    print("[SAYFA] ATV aciliyor...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required"
            ]
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR",
            ignore_https_errors=True
        )
        page = context.new_page()

        page.add_init_script("""
            window.__atvResources = [];
            try {
                const obs = new PerformanceObserver((list) => {
                    for (const e of list.getEntries()) {
                        if (e.name) window.__atvResources.push(e.name);
                    }
                });
                obs.observe({entryTypes: ['resource']});
            } catch(e) {}
        """)

        def istek_yakala(request):
            url = request.url
            if ".m3u8" in url:
                tum_m3u8.add(url)
                print("[M3U8 ISTEK]", url[:200])
            if gercek_atv_mi(url) and url not in bulunan:
                bulunan.add(url)
                print("[ISTEK YAKALANDI]", url[:180])

        def cevap_yakala(response):
            url = response.url
            if ".m3u8" in url:
                print("[M3U8 CEVAP]", response.status, url[:180])
            if gercek_atv_mi(url) and url not in bulunan:
                bulunan.add(url)

        page.on("request", istek_yakala)
        page.on("response", cevap_yakala)

        try:
            page.goto(SAYFA_URL, wait_until="domcontentloaded", timeout=60000)
            print("[OK] ATV sayfasi acildi.")
        except PlaywrightTimeout:
            print("[UYARI] Sayfa yuklemesi zaman asimina ugradi, tarama devam ediyor.")
        except Exception as e:
            print("[HATA] Sayfa acilamadi:", e)
            browser.close()
            return None

        # Cerez onayi
        for secici in ["#onetrust-accept-btn-handler", "button:has-text('Kabul Et')", "button:has-text('Tumunu Kabul Et')", "button:has-text('Kabul ediyorum')"]:
            try:
                eleman = page.locator(secici).first
                if eleman.is_visible(timeout=1000):
                    eleman.click(timeout=2000)
                    print("[OK] Cerez onayi verildi.")
                    break
            except Exception:
                pass

        # Oynaticiyi calistir
        for frame in page.frames:
            try:
                frame.evaluate("""
                    () => {
                        document.querySelectorAll('video').forEach(v => {
                            try { v.muted = true; v.volume = 0; v.setAttribute('playsinline',''); v.play().catch(()=>{}); } catch(e) {}
                        });
                        return true;
                    }
                """)
            except Exception:
                pass

        # Oynat dugmeleri
        for frame in page.frames:
            for secici in ["button[aria-label*='Play']", ".vjs-big-play-button", ".jw-display-icon-container", ".plyr__control--overlaid", "[class*='playButton']"]:
                try:
                    dugme = frame.locator(secici).first
                    if dugme.is_visible(timeout=500):
                        dugme.click(timeout=1500)
                        print("[OYUNCU] Oynat dugmesine basildi.")
                        break
                except Exception:
                    pass

        print("[BEKLE] Yayin kaynaklari taraniyor... Suresi:", TARAMA_SURESI)
        baslangic = time.time()
        son_yazdirma = 0

        while time.time() - baslangic < TARAMA_SURESI:
            for frame in page.frames:
                try:
                    kaynaklar = frame.evaluate("""
                        () => {
                            let sonuc = [];
                            try { performance.getEntriesByType('resource').forEach(x => { if(x.name) sonuc.push(x.name); }); } catch(e) {}
                            try { if(window.__atvResources) sonuc.push(...window.__atvResources); } catch(e) {}
                            try {
                                document.querySelectorAll('video').forEach(v => {
                                    if(v.currentSrc) sonuc.push(v.currentSrc);
                                    if(v.src) sonuc.push(v.src);
                                });
                            } catch(e) {}
                            return [...new Set(sonuc)];
                        }
                    """)
                    for url in kaynaklar:
                        if ".m3u8" in url and url not in tum_m3u8:
                            tum_m3u8.add(url)
                            print("[PERFORMANCE M3U8]", url[:200])
                        if gercek_atv_mi(url) and url not in bulunan:
                            bulunan.add(url)
                            print("[PERFORMANCE 【entity-ATV¦canonical_name=ATV】]", url[:180])
                except Exception:
                    pass

                try:
                    frame.evaluate("() => { document.querySelectorAll('video').forEach(v => { try { if(v.paused){ v.muted=true; v.play().catch(()=>{}); } } catch(e){} }); }")
                except Exception:
                    pass

            gecen = int(time.time() - baslangic)
            if gecen - son_yazdirma >= 15:
                print("[TARAMA]", gecen, "sn | 【entity-ATV¦canonical_name=ATV】:", len(bulunan), "| Tum M3U8:", len(tum_m3u8))
                son_yazdirma = gecen

            if any("/【entity-atv¦canonical_name=ATV】/atv_1080p.m3u8" in u for u in bulunan) and gecen >= 20:
                break
            page.wait_for_timeout(3000)

        try:
            TARAYICI_CEREZLERI = {c["name"]: c["value"] for c in context.cookies() if "【entity-atv¦canonical_name=ATV】.com.tr" in c.get("domain","") or "daioncdn.net" in c.get("domain","")}
        except Exception:
            TARAYICI_CEREZLERI = {}
        browser.close()

    print("[TARAMA TAMAMLANDI] 【entity-ATV¦canonical_name=ATV】:", len(bulunan), "Tum M3U8:", len(tum_m3u8))
    if tum_m3u8 and not bulunan:
        print("[IPUCU] 【entity-ATV¦canonical_name=ATV】 filtresi disinda kalan M3U8'ler:")
        for u in list(tum_m3u8)[:20]:
            print(" -", u[:250])

    if not bulunan:
        print("[SONUC] 【entity-ATV¦canonical_name=ATV】 adresi bulunamadi.")
        return None

    sirali = sorted(bulunan, key=adres_onceligi)
    for i, url in enumerate(sirali, 1):
        print(i, url[:200])
    return sirali[0]

def yayin_test(url):
    print("[TEST] 【entity-ATV¦canonical_name=ATV】 yayin adresi kontrol ediliyor...")
    headers = {"User-Agent": USER_AGENT, "Referer": REFERER, "Origin": ORIGIN, "Accept": "*/*"}
    try:
        r = requests.get(url, headers=headers, cookies=TARAYICI_CEREZLERI, timeout=25, verify=False)
        print("[HTTP]", r.status_code)
        if r.status_code != 200:
            return False
        icerik = r.text[:1000].lstrip()
        if "#EXTM3U" not in icerik:
            print("[HATA] Gecerli HLS playlist bulunamadi:", icerik[:200])
            return False
        print("[OK] Gecerli M3U8 yayini bulundu.")
        return True
    except Exception as e:
        print("[UYARI] Yayin testi basarisiz:", e)
        return False

def atv_m3u_kaydi(url):
    return [
        f'#EXTINF:-1 tvg-id="{TVG_ID}" tvg-name="{KANAL}" tvg-logo="{LOGO}" group-title="{GRUP}",{KANAL}',
        "#EXTVLCOPT:http-referrer=" + REFERER,
        "#EXTVLCOPT:http-origin=" + ORIGIN,
        "#EXTVLCOPT:http-user-agent=" + USER_AGENT,
        url
    ]

def m3u_guncelle(url):
    if not os.path.exists(DOSYA):
        print("[HATA] M3U dosyasi bulunamadi:", DOSYA)
        return False
    with open(DOSYA, "r", encoding="utf-8-sig") as f:
        satirlar = f.read().splitlines()

    baslik, bloklar, mevcut = [], [], []
    for satir in satirlar:
        if satir.startswith("#EXTINF:"):
            if mevcut:
                bloklar.append(mevcut)
            mevcut = [satir]
        elif mevcut:
            mevcut.append(satir)
        else:
            baslik.append(satir)
    if mevcut:
        bloklar.append(mevcut)

    temiz, silinen = [], 0
    for blok in bloklar:
        metin = "\n".join(blok).lower()
        if 'tvg-id="atv.tr"' in metin or "atvᴴᴰ⭕".lower() in metin or "atv_1080p.m3u8" in metin or "atvavrupa.m3u8" in metin or "daioncdn" in metin and "atv" in metin:
            silinen += 1
            continue
        temiz.append(blok)
    print(" Eski ATV kaydi:", silinen)

    hedef = [i for i, blok in enumerate(temiz) if "group-title=" in blok[0] and "ULUSAL" in blok[0].upper()]
    yeni_blok = atv_m3u_kaydi(url)
    if hedef:
        temiz.insert(hedef[-1] + 1, yeni_blok)
        print(" ATV ULUSAL grubuna eklendi.")
    else:
        temiz.append(yeni_blok)
        print("[UYARI] ULUSAL grubu bulunamadi, sona eklendi.")

    cikti = list(baslik)
    for blok in temiz:
        cikti.extend(blok)
    gecici = DOSYA + ".tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(cikti) + "\n")
    os.replace(gecici, DOSYA)
    print("[OK] M3U basariyla guncellendi.")
    return True

def main():
    print("======================================")
    print("       MIRTI68 ATV 1080P SISTEMI")
    print("======================================")
    url = atv_adresi_bul()
    if not url:
        print("[BASARISIZ] Gercek ATV adresi bulunamadi. Eski M3U korundu.")
        return 1
    if not yayin_test(url):
        print("[BASARISIZ] Yayin dogrulanamadi. Eski M3U korundu.")
        return 1
    if not m3u_guncelle(url):
        print("[BASARISIZ] M3U guncellenemedi.")
        return 1
    print("[TAMAMLANDI] ATV 1080P GUNCELLENDI")
    return 0

if __name__ == "__main__":
    sys.exit(main())
