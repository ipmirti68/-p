
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import requests
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

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

# İsteğe bağlı Secret. Otomatik tarama önceliklidir.
MANUEL_URL = os.environ.get("ATV_URL", "").strip()


# =====================================================
# ATV TÜRKİYE ADRES KONTROLÜ
# =====================================================

def atv_adresi_mi(url):
    if not isinstance(url, str):
        return False

    try:
        p = urlsplit(url)

        if p.scheme not in ("http", "https"):
            return False

        host = (p.hostname or "").lower()
        path = p.path.lower()

        if "atvavrupa" in url.lower():
            return False

        if not host.endswith("daioncdn.net"):
            return False

        return re.fullmatch(
            r"/atv/atv(_1080p)?\.m3u8",
            path
        ) is not None

    except Exception:
        return False


def kalite(url):
    if "atv_1080p.m3u8" in url.lower():
        return 2
    return 1


# =====================================================
# BOOKMARKLET GİBİ OTOMATİK ADRES TARAMA
# =====================================================

def yayin_adresi_bul():

    bulunan = set()

    def ekle(url, kaynak=""):
        if atv_adresi_mi(url):
            bulunan.add(url)
            print(
                f"[BULUNDU] {kaynak}: "
                f"{url[:180]}"
            )

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
            viewport={
                "width": 1920,
                "height": 1080
            }
        )

        page = context.new_page()

        # Bookmarklet gibi kaynakları izle
        page.add_init_script("""
            window.__atvKaynaklar = [];

            try {
                new PerformanceObserver(function(list) {
                    list.getEntries().forEach(function(r) {
                        if (r.name) {
                            window.__atvKaynaklar.push(r.name);
                        }
                    });
                }).observe({entryTypes: ['resource']});
            } catch(e) {}
        """)

        # Ağ isteklerini yakala
        page.on(
            "request",
            lambda req: ekle(req.url, "REQUEST")
        )

        page.on(
            "response",
            lambda res: ekle(res.url, "RESPONSE")
        )

        try:
            print("[BASLA] ATV canlı yayın sayfası açılıyor...")

            page.goto(
                SAYFA_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("[OK] ATV sayfası açıldı.")
            print("[TARAMA] Yayın kaynakları izleniyor...")

            for saniye in range(0, 120, 3):

                # Ana sayfa kaynakları
                try:
                    kaynaklar = page.evaluate("""
                        () => {
                            let sonuc = [];

                            try {
                                performance
                                    .getEntriesByType('resource')
                                    .forEach(r => sonuc.push(r.name));
                            } catch(e) {}

                            try {
                                sonuc.push(...window.__atvKaynaklar);
                            } catch(e) {}

                            document.querySelectorAll('video')
                                .forEach(v => {
                                    sonuc.push(v.currentSrc);
                                    sonuc.push(v.src);

                                    v.querySelectorAll('source')
                                        .forEach(s => sonuc.push(s.src));
                                });

                            return sonuc.filter(Boolean);
                        }
                    """)

                    for url in kaynaklar:
                        ekle(url, "PERFORMANCE/VIDEO")

                except Exception as e:
                    print("[UYARI] Ana sayfa taraması:", str(e)[:120])

                # Sayfadaki iframe kaynaklarını da kontrol et
                for frame in page.frames:
                    try:
                        kaynaklar = frame.evaluate("""
                            () => {
                                let sonuc = [];

                                try {
                                    performance
                                        .getEntriesByType('resource')
                                        .forEach(r => sonuc.push(r.name));
                                } catch(e) {}

                                document.querySelectorAll('video')
                                    .forEach(v => {
                                        sonuc.push(v.currentSrc);
                                        sonuc.push(v.src);
                                    });

                                return sonuc.filter(Boolean);
                            }
                        """)

                        for url in kaynaklar:
                            ekle(url, "IFRAME")

                    except Exception:
                        pass

                secenekler = sorted(
                    bulunan,
                    key=kalite,
                    reverse=True
                )

                print(
                    f"[TARAMA] {saniye} saniye | "
                    f"Bulunan ATV: {len(bulunan)}"
                )

                # Gerçek 1080P bulunduysa beklemeyi bitir
                if any(
                    kalite(url) == 2
                    for url in bulunan
                ):
                    print("[OK] ATV 1080P adresi yakalandı.")
                    break

                time.sleep(3)

        except Exception as e:
            print("[HATA] Tarayıcı:", e)

        finally:
            browser.close()

    # Gerçek adres bulunamadıysa Secret yedek olarak denenir
    if not bulunan and MANUEL_URL:
        print("[BİLGİ] ATV_URL Secret yedek olarak kontrol ediliyor.")
        ekle(MANUEL_URL, "SECRET")

    if not bulunan:
        return None

    sirali = sorted(
        bulunan,
        key=kalite,
        reverse=True
    )

    return sirali[0]


# =====================================================
# YAYIN TESTİ
# =====================================================

def yayin_test(url):

    print("[TEST] Yayın adresi kontrol ediliyor...")

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": REFERER,
        "Origin": ORIGIN,
        "Accept": "*/*"
    }

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=25,
            verify=True
        )

        print("[HTTP]", r.status_code)

        if r.status_code != 200:
            return False

        if "#EXTM3U" not in r.text[:3000]:
            print("[HATA] Geçerli HLS yanıtı değil.")
            return False

        print("[OK] Geçerli M3U8 adresi.")
        return True

    except Exception as e:
        print("[UYARI] Yayın testi başarısız:", e)
        return False


# =====================================================
# M3U KAYDI
# =====================================================

def atv_m3u_kaydi(url):

    return [
        f'#EXTINF:-1 tvg-id="{TVG_ID}" tvg-name="{KANAL}" tvg-logo="{LOGO}" group-title="{GRUP}",{KANAL}',
        "#EXTVLCOPT:http-referrer=" + REFERER,
        "#EXTVLCOPT:http-origin=" + ORIGIN,
        "#EXTVLCOPT:http-user-agent=" + USER_AGENT,
        url
    ]


# =====================================================
# M3U GÜNCELLEME
# =====================================================

def m3u_guncelle(url):

    if not os.path.exists(DOSYA):
        print("[HATA] M3U bulunamadı:", DOSYA)
        return False

    with open(DOSYA, "r", encoding="utf-8-sig") as f:
        satirlar = f.read().splitlines()

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

    temiz = []
    silinen = 0

    for blok in bloklar:

        ilk_satir = blok[0].lower()
        metin = "\n".join(blok).lower()

        eski_atv = (
            'tvg-id="atv.tr"' in ilk_satir
            or 'tvg-name="atv' in ilk_satir
            or "atvᴴᴰ⭕" in ilk_satir
        )

        eski_avrupa = (
            "atvavrupa" in ilk_satir
            or "atvavrupa" in metin
        )

        if eski_atv or eski_avrupa:
            silinen += 1
            continue

        temiz.append(blok)

    print("[BİLGİ] Eski ATV kaydı temizlendi:", silinen)

    yeni_blok = atv_m3u_kaydi(url)

    hedefler = [
        i
        for i, blok in enumerate(temiz)
        if "group-title=" in blok[0]
        and "ULUSAL" in blok[0].upper()
    ]

    if hedefler:
        temiz.insert(
            hedefler[-1] + 1,
            yeni_blok
        )
        print("[OK] ATV ULUSAL grubuna eklendi.")
    else:
        temiz.append(yeni_blok)
        print("[UYARI] ULUSAL grubu bulunamadı, sona eklendi.")

    cikti = list(baslik)

    for blok in temiz:
        cikti.extend(blok)

    gecici = DOSYA + ".tmp"

    with open(
        gecici,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:
        f.write("\n".join(cikti) + "\n")

    os.replace(gecici, DOSYA)

    print("[OK] M3U güncellendi.")
    print("[OK] Diğer kanal kayıtları korundu.")

    return True


# =====================================================
# ANA İŞLEM
# =====================================================

def main():

    url = yayin_adresi_bul()

    if not url:
        print("[BAŞARISIZ] Gerçek ATV Türkiye adresi bulunamadı.")
        print("[KORUNDU] Eski M3U kaydı değiştirilmedi.")
        return 1

    print("[SEÇİLDİ]", url[:220])

    if "atv_1080p.m3u8" in url.lower():
        print("[KALİTE] 1080P")
    else:
        print("[KALİTE] Standart ATV yayını")

    if not yayin_test(url):
        print("[BAŞARISIZ] Yayın testi geçmedi.")
        print("[KORUNDU] Eski M3U kaydı değiştirilmedi.")
        return 1

    if not m3u_guncelle(url):
        return 1

    print("[TAMAMLANDI] ATV Türkiye güncellendi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
