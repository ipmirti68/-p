
import re
import sys
import time
from playwright.sync_api import sync_playwright

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"

M3U_DOSYA = "mirti68.m3u"

LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# =====================================================
# ATV YAYIN ADRESİ KONTROLÜ
# =====================================================

def atv_adresi_mi(url):
    if not isinstance(url, str):
        return False

    return (
        "trkvz.daioncdn.net" in url.lower()
        and re.search(
            r"/atv/atv(_1080p)?\.m3u8(?:\?|$)",
            url,
            re.IGNORECASE
        ) is not None
    )


def adres_tipi(url):
    if "atv_1080p.m3u8" in url:
        return 2
    if "atv.m3u8" in url:
        return 1
    return 0


# =====================================================
# BOOKMARKLET İLE AYNI TARAMA MANTIĞI
# =====================================================

def yayin_adresi_bul():

    bulunan = set()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        # Tarayıcı kaynaklarını kaydet
        page.add_init_script("""
            window.__atvKaynaklar = [];

            try {
                const eski = performance.getEntriesByType.bind(performance);

                const tara = () => {
                    try {
                        performance.getEntriesByType('resource')
                            .forEach(r => {
                                if (r.name)
                                    window.__atvKaynaklar.push(r.name);
                            });
                    } catch(e) {}
                };

                new PerformanceObserver(list => {
                    list.getEntries().forEach(r => {
                        if (r.name)
                            window.__atvKaynaklar.push(r.name);
                    });
                }).observe({entryTypes: ['resource']});

                setInterval(tara, 1000);
            } catch(e) {}
        """)

        # Ağ isteklerini de kaydet
        def istek_yakala(request):
            try:
                if atv_adresi_mi(request.url):
                    bulunan.add(request.url)
                    print("[İSTEK]", request.url[:120])
            except Exception:
                pass

        def cevap_yakala(response):
            try:
                if atv_adresi_mi(response.url):
                    bulunan.add(response.url)
                    print("[CEVAP]", response.url[:120])
            except Exception:
                pass

        page.on("request", istek_yakala)
        page.on("response", cevap_yakala)

        try:
            print("[BASLA] ATV canlı yayın sayfası açılıyor...")

            page.goto(
                SAYFA_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("[OK] ATV sayfası açıldı.")
            print("[TARAMA] Yayın kaynakları kontrol ediliyor...")

            # Bookmarklet gibi her 3 saniyede bir tara
            for saniye in range(0, 120, 3):

                try:
                    sonuc = page.evaluate("""
                        () => {
                            let found = [];

                            try {
                                performance
                                    .getEntriesByType('resource')
                                    .forEach(r => found.push(r.name));
                            } catch(e) {}

                            try {
                                if (window.__atvKaynaklar)
                                    found.push(...window.__atvKaynaklar);
                            } catch(e) {}

                            document.querySelectorAll('video')
                                .forEach(v => {
                                    found.push(v.currentSrc);
                                    found.push(v.src);

                                    v.querySelectorAll('source')
                                        .forEach(s => found.push(s.src));
                                });

                            return found.filter(Boolean);
                        }
                    """)

                    for url in sonuc:
                        if atv_adresi_mi(url):
                            bulunan.add(url)

                except Exception as e:
                    print("[UYARI] Tarama:", str(e)[:150])

                # En iyi kaliteyi seç
                sirali = sorted(
                    bulunan,
                    key=adres_tipi,
                    reverse=True
                )

                if sirali:
                    print(
                        f"[TARAMA] {saniye} saniye | "
                        f"{len(bulunan)} ATV adresi bulundu."
                    )
                else:
                    print(
                        f"[TARAMA] {saniye} saniye | "
                        "Henüz ATV adresi bulunamadı."
                    )

                if any("atv_1080p.m3u8" in x for x in bulunan):
                    print("[BİLGİ] 1080P adresi bulundu.")
                    break

                time.sleep(3)

        except Exception as e:
            print("[HATA] Sayfa tarama:", e)

        finally:
            browser.close()

    if not bulunan:
        return None

    sirali = sorted(
        bulunan,
        key=adres_tipi,
        reverse=True
    )

    for url in sirali:
        if "atv_1080p.m3u8" in url:
            print("[SEÇİLDİ] ATV 1080P")
            return url

    print("[SEÇİLDİ] ATV standart yayın")
    return sirali[0]


# =====================================================
# YAYIN TESTİ
# =====================================================

def yayin_test(url):

    from urllib.request import Request, urlopen

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": SAYFA_URL,
        "Origin": "https://www.atv.com.tr"
    }

    try:
        req = Request(url, headers=headers)

        with urlopen(req, timeout=20) as cevap:
            icerik = cevap.read(4096).decode(
                "utf-8",
                errors="ignore"
            )

            if cevap.status == 200 and "#EXTM3U" in icerik:
                print("[TEST OK] Yayın M3U8 olarak doğrulandı.")
                return True

            print("[TEST HATA] Geçerli M3U8 yanıtı alınamadı.")
            return False

    except Exception as e:
        print("[TEST HATA]", e)
        return False


# =====================================================
# M3U DOSYASINI GÜNCELLE
# =====================================================

def m3u_guncelle(url):

    try:
        with open(M3U_DOSYA, "r", encoding="utf-8-sig") as f:
            satirlar = f.read().splitlines()

    except FileNotFoundError:
        print("[HATA] mirti68.m3u bulunamadı.")
        return False

    # Eski ATV kaydını kaldır, diğer kanalları koru
    yeni_satirlar = []
    i = 0

    while i < len(satirlar):

        satir = satirlar[i]

        if (
            satir.startswith("#EXTINF")
            and (
                'tvg-id="atv.tr"' in satir.lower()
                or 'tvg-name="atv' in satir.lower()
            )
        ):
            i += 1

            while i < len(satirlar):
                if satirlar[i].startswith("#EXTINF"):
                    break
                if satirlar[i].strip() and not satirlar[i].startswith("#"):
                    i += 1
                    break
                i += 1

            continue

        yeni_satirlar.append(satir)
        i += 1

    kayit = [
        f'#EXTINF:-1 tvg-id="atv.tr" tvg-name="ATVᴴᴰ⭕" tvg-logo="{LOGO}" group-title="{GRUP}",ATVᴴᴰ⭕',
        "#EXTVLCOPT:http-referrer=https://www.atv.com.tr/canli-yayin",
        "#EXTVLCOPT:http-origin=https://www.atv.com.tr",
        f"#EXTVLCOPT:http-user-agent={USER_AGENT}",
        url
    ]

    # ULUSAL grubunun içine ekle
    eklendi = False

    for i, satir in enumerate(yeni_satirlar):
        if satir.startswith("#EXTINF") and GRUP in satir:
            yeni_satirlar[i + 1:i + 1] = kayit
            eklendi = True
            break

    # Grup bulunamazsa dosyanın sonuna ekle
    if not eklendi:
        yeni_satirlar.extend(kayit)

    with open(M3U_DOSYA, "w", encoding="utf-8") as f:
        f.write("\n".join(yeni_satirlar) + "\n")

    print("[OK] ATV kaydı güncellendi.")
    print("[OK] Diğer kanallar korundu.")

    return True


# =====================================================
# ANA İŞLEM
# =====================================================

def main():

    url = yayin_adresi_bul()

    if not url:
        print("[BAŞARISIZ] ATV adresi bulunamadı.")
        print("[KORUNDU] Eski M3U kaydı değiştirilmedi.")
        return 1

    print("[ADRES] ATV yayın adresi bulundu.")

    if not yayin_test(url):
        print("[BAŞARISIZ] Yayın testi geçmedi.")
        print("[KORUNDU] Eski M3U kaydı değiştirilmedi.")
        return 1

    if not m3u_guncelle(url):
        return 1

    print("[TAMAMLANDI] ATV başarıyla güncellendi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
