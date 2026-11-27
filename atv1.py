
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import requests
import urllib3

from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# AYARLAR
# =========================================================

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
TARAMA_ARALIGI = 3

# =========================================================
# GERÇEK ATV ADRES KONTROLÜ
# =========================================================

def gercek_atv_mi(url):
    if not isinstance(url, str):
        return False

    try:
        p = urlsplit(url)

        if p.scheme not in ("http", "https"):
            return False

        if p.netloc.lower() != "trkvz.daioncdn.net":
            return False

        if p.path not in (
            "/atv/atv_1080p.m3u8",
            "/atv/atv.m3u8"
        ):
            return False

        if not p.query:
            return False

        return True

    except Exception:
        return False


def adres_onceligi(url):
    if "/atv/atv_1080p.m3u8" in url:
        return 0

    if "/atv/atv.m3u8" in url:
        return 1

    return 99


# =========================================================
# ATV SAYFASINDAN YAYIN ADRESİNİ BUL
# =========================================================

def atv_adresi_bul():

    bulunan = set()
    cevap_durumlari = {}

    print("[SAYFA] ATV açılıyor...")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR",
            ignore_https_errors=True
        )

        page = context.new_page()

        # Tarayıcının gönderdiği gerçek istekleri yakala.
        def istek_yakala(request):
            url = request.url

            if gercek_atv_mi(url):
                bulunan.add(url)
                print("[İSTEK YAKALANDI]", url[:110])

        # Sunucudan dönen cevapları yakala.
        def cevap_yakala(response):
            url = response.url

            if gercek_atv_mi(url):
                bulunan.add(url)
                cevap_durumlari[url] = response.status
                print("[CEVAP]", response.status, url[:100])

        page.on("request", istek_yakala)
        page.on("response", cevap_yakala)

        # Sayfa açılmadan önce performans gözlemleyicisi ekle.
        page.add_init_script("""
            window.__atvResources = [];

            try {
                const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name) {
                            window.__atvResources.push(entry.name);
                        }
                    }
                });

                observer.observe({entryTypes: ['resource']});
            } catch(e) {}
        """)

        try:
            page.goto(
                SAYFA_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("[OK] ATV sayfası açıldı.")

        except PlaywrightTimeout:
            print("[UYARI] Sayfa yüklemesi zaman aşımına uğradı.")
            print("[UYARI] Mevcut sayfa taranmaya devam edilecek.")

        except Exception as e:
            print("[HATA] Sayfa açılamadı:", e)
            browser.close()
            return None

        # Çerez penceresi varsa kapatmayı dene.
        print("[BEKLE] Çerez ve oynatıcı kontrolü...")

        try:
            seciciler = [
                "#onetrust-accept-btn-handler",
                "button#acceptAll",
                "button:has-text('Kabul Et')",
                "button:has-text('Tümünü Kabul Et')",
                "button:has-text('Kabul ediyorum')"
            ]

            for secici in seciciler:
                try:
                    eleman = page.locator(secici).first

                    if eleman.is_visible(timeout=1000):
                        eleman.click(timeout=2000)
                        print("[OK] Çerez onayı verildi.")
                        break

                except Exception:
                    pass

        except Exception:
            pass

        print("[BEKLE] ATV oynatıcısı taranıyor...")
        print("[BİLGİ] Tarama süresi:", TARAMA_SURESI, "saniye")

        baslangic = time.time()
        son_yazdirma = 0

        while time.time() - baslangic < TARAMA_SURESI:

            try:
                # Performance kayıtlarını al.
                kaynaklar = page.evaluate("""
                    () => {
                        let sonuc = [];

                        try {
                            performance
                                .getEntriesByType('resource')
                                .forEach(x => sonuc.push(x.name));
                        } catch(e) {}

                        try {
                            if (window.__atvResources) {
                                sonuc.push(...window.__atvResources);
                            }
                        } catch(e) {}

                        // Video kaynaklarını kontrol et.
                        try {
                            document.querySelectorAll('video').forEach(v => {
                                if (v.currentSrc) sonuc.push(v.currentSrc);
                                if (v.src) sonuc.push(v.src);

                                v.querySelectorAll('source').forEach(s => {
                                    if (s.src) sonuc.push(s.src);
                                });
                            });
                        } catch(e) {}

                        return [...new Set(sonuc)];
                    }
                """)

                for url in kaynaklar:
                    if gercek_atv_mi(url):
                        bulunan.add(url)

            except Exception:
                pass

            # Sayfanın ağ istekleri zaten Playwright tarafından
            # ayrıca takip ediliyor.

            gecen = int(time.time() - baslangic)

            if gecen - son_yazdirma >= 15:
                print(
                    "[TARAMA]",
                    gecen,
                    "saniye | Bulunan gerçek ATV:",
                    len(bulunan)
                )
                son_yazdirma = gecen

            # 1080P bulunduysa diğer adresleri de kısa süre
            # gözlemleyerek toplamayı tamamla.
            if any(
                "/atv/atv_1080p.m3u8" in u
                for u in bulunan
            ):
                if gecen >= 15:
                    break

            page.wait_for_timeout(TARAMA_ARALIGI * 1000)

        browser.close()

    print("[TARAMA TAMAMLANDI]", len(bulunan), "GERÇEK ATV ADRESİ")

    if not bulunan:
        return None

    # 1080P öncelikli sıralama.
    sirali = sorted(
        bulunan,
        key=adres_onceligi
    )

    print("[BULUNAN ADRESLER]")

    for i, url in enumerate(sirali, 1):
        print(i, url[:150])

    # Önce 1080P, yoksa ana playlist.
    for url in sirali:
        if adres_onceligi(url) == 0:
            print("[SEÇİLDİ] ATV 1080P")
            return url

    print("[SEÇİLDİ] ATV ana M3U8")
    return sirali[0]


# =========================================================
# YAYIN ADRESİNİ TEST ET
# =========================================================

def yayin_test(url):

    print("[TEST] ATV yayın adresi kontrol ediliyor...")

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": REFERER,
        "Origin": ORIGIN,
        "Accept": "*/*"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=25,
            verify=False
        )

        print("[HTTP]", response.status_code)

        if response.status_code != 200:
            print("[HATA] Yayın HTTP hatası:", response.status_code)
            return False

        icerik = response.text[:500].lstrip()

        if "#EXTM3U" not in icerik:
            print("[HATA] Geçerli HLS playlist bulunamadı.")
            return False

        print("[OK] Geçerli M3U8 yayını bulundu.")
        return True

    except Exception as e:
        print("[UYARI] Yayın HTTP testi başarısız:", e)
        print("[UYARI] Tarayıcıdan yakalanan adres kullanılmayacak.")
        return False


# =========================================================
# M3U KANAL KAYDI
# =========================================================

def atv_m3u_kaydi(url):

    return [
        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL}'
        ),
        "#EXTVLCOPT:http-referrer=" + REFERER,
        "#EXTVLCOPT:http-origin=" + ORIGIN,
        "#EXTVLCOPT:http-user-agent=" + USER_AGENT,
        url
    ]


# =========================================================
# ESKİ ATV KAYDINI BUL VE GÜNCELLE
# =========================================================

def m3u_guncelle(url):

    if not os.path.exists(DOSYA):
        print("[HATA] M3U dosyası bulunamadı:", DOSYA)
        return False

    print("[M3U] Dosya okunuyor...")

    with open(DOSYA, "r", encoding="utf-8-sig") as f:
        satirlar = f.read().splitlines()

    # M3U başlığını ve kanal bloklarını ayır.
    baslik = []
    bloklar = []
    mevcut = []

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

    # ATV'nin eski kaydını kaldır.
    temiz_bloklar = []
    silinen = 0

    for blok in bloklar:

        metin = "\n".join(blok).lower()

        atv_kaydi = (
            'tvg-id="atv.tr"' in metin
            or "atvᴴᴰ⭕".lower() in metin
            or "atv_1080p.m3u8" in metin
            or "atvavrupa.m3u8" in metin
        )

        if atv_kaydi:
            silinen += 1
            continue

        temiz_bloklar.append(blok)

    print("[M3U] Eski ATV kaydı:", silinen)

    # ULUSAL grubunun sonuna ekle.
    hedef = []

    for i, blok in enumerate(temiz_bloklar):

        ilk_satir = blok[0]

        if "group-title=" in ilk_satir and "ULUSAL" in ilk_satir.upper():
            hedef.append(i)

    yeni_blok = atv_m3u_kaydi(url)

    if hedef:
        ekleme_yeri = hedef[-1] + 1
        temiz_bloklar.insert(ekleme_yeri, yeni_blok)
        print("[M3U] ATV ULUSAL grubuna eklendi.")

    else:
        temiz_bloklar.append(yeni_blok)
        print("[UYARI] ULUSAL grubu bulunamadı.")
        print("[M3U] ATV dosyanın sonuna eklendi.")

    # Dosyayı yeniden oluştur.
    cikti = list(baslik)

    for blok in temiz_bloklar:
        cikti.extend(blok)

    gecici = DOSYA + ".tmp"

    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(cikti) + "\n")

    os.replace(gecici, DOSYA)

    print("[OK] M3U başarıyla güncellendi.")
    print("[KAYIT]", url[:150])

    return True


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    print("======================================")
    print("       MIRTI68 ATV 1080P SISTEMI")
    print("======================================")

    print("[1] ATV YAYIN ADRESİ TARAMASI")

    url = atv_adresi_bul()

    if not url:
        print("[BAŞARISIZ] Gerçek ATV adresi bulunamadı.")
        print("[SONUÇ] ATV güncellenmedi.")
        print("[SONUÇ] Eski M3U korundu.")
        return

    print("======================================")
    print("[2] YAYIN TESTİ")
    print("======================================")

    if not yayin_test(url):
        print("[BAŞARISIZ] Yayın doğrulanamadı.")
        print("[SONUÇ] Eski M3U korundu.")
        return

    print("======================================")
    print("[3] M3U GÜNCELLEME")
    print("======================================")

    if not m3u_guncelle(url):
        print("[BAŞARISIZ] M3U güncellenemedi.")
        return

    print("======================================")
    print("[TAMAMLANDI] ATV 1080P GÜNCELLENDİ")
    print("======================================")


if __name__ == "__main__":
    main()
