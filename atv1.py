
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import requests
import urllib3

from urllib.parse import urlsplit, urljoin
from playwright.sync_api import sync_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================
# AYARLAR
# =====================================================

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"
ORIGIN = "https://www.atv.com.tr"
REFERER = SAYFA_URL

DOSYA = "mirti68.m3u"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
KANAL = "ATVᴴᴰ⭕"
TVG_ID = "atv.tr"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TIMEOUT = 25
ILK_BEKLEME = 10000
TARAMA_SURESI = 30000

session = requests.Session()

session.headers.update({
    "User-Agent": UA,
    "Referer": REFERER,
    "Origin": ORIGIN,
    "Accept": "*/*",
})

aday_basliklari = {}


# =====================================================
# LOG
# =====================================================

def yaz(mesaj):
    print(mesaj, flush=True)


# =====================================================
# URL KONTROL
# =====================================================

def guvenli_url(url):

    try:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}{p.path}"

    except Exception:
        return url


def gercek_atv_mi(url):

    try:

        p = urlsplit(url)

        return (
            p.scheme in ("http", "https")
            and p.netloc.lower() == "trkvz.daioncdn.net"
            and p.path.lower().startswith("/atv/")
            and p.path.lower().endswith(".m3u8")
        )

    except Exception:
        return False


def kalite_puani(url):

    yol = urlsplit(url).path.lower()

    if "1080p" in yol:
        return 100

    if "720p" in yol:
        return 80

    if "576p" in yol:
        return 60

    if "480p" in yol:
        return 40

    return 10


# =====================================================
# ADAY EKLE
# =====================================================

def aday_ekle(url, headers=None, kaynak=""):

    if not isinstance(url, str):
        return

    url = url.strip()

    if not gercek_atv_mi(url):
        return

    if url not in aday_basliklari:

        aday_basliklari[url] = headers or {}

        yaz("")
        yaz("[GERÇEK ATV ADAYI]")
        yaz("[KAYNAK] " + kaynak)
        yaz("[URL] " + guvenli_url(url))
        yaz("[KALİTE] " + str(kalite_puani(url)))


# =====================================================
# PLAYWRIGHT TARAMASI
# =====================================================

def playwright_tara():

    yaz("")
    yaz("======================================")
    yaz("[1] ATV BOOKMARKLET TARAMASI")
    yaz("======================================")

    aday_basliklari.clear()

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--autoplay-policy=no-user-gesture-required"
                ]
            )

            context = browser.new_context(
                user_agent=UA,
                ignore_https_errors=True,
                viewport={
                    "width": 1366,
                    "height": 768
                }
            )

            page = context.new_page()

            # -----------------------------------------
            # NETWORK
            # -----------------------------------------

            def request_yakala(request):

                try:

                    aday_ekle(
                        request.url,
                        request.headers,
                        "NETWORK"
                    )

                except Exception:
                    pass

            def response_yakala(response):

                try:

                    aday_ekle(
                        response.url,
                        response.request.headers,
                        "RESPONSE"
                    )

                except Exception:
                    pass

            page.on("request", request_yakala)
            page.on("response", response_yakala)

            # -----------------------------------------
            # SAYFAYI AÇ
            # -----------------------------------------

            try:

                yaz("[SAYFA] ATV açılıyor...")

                page.goto(
                    SAYFA_URL,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                yaz("[OK] ATV sayfası açıldı.")

            except Exception as hata:

                yaz("[SAYFA UYARI] " + str(hata)[:300])

            # -----------------------------------------
            # VİDEOYU BAŞLAT
            # -----------------------------------------

            try:

                page.evaluate("""
                    () => {

                        document.querySelectorAll('video')
                        .forEach(v => {

                            v.muted = true;

                            v.play().catch(() => {});

                        });

                    }
                """)

            except Exception:
                pass

            page.wait_for_timeout(ILK_BEKLEME)

            # -----------------------------------------
            # OYNATMA BUTONLARI
            # -----------------------------------------

            try:

                page.evaluate("""
                    () => {

                        const seciciler = [
                            '.vjs-big-play-button',
                            '.jw-icon-playback',
                            '.plyr__control--overlaid',
                            'button[aria-label*="Oynat"]',
                            'button[aria-label*="Play"]'
                        ];

                        seciciler.forEach(secici => {

                            document.querySelectorAll(secici)
                            .forEach(el => {

                                try {
                                    el.click();
                                } catch(e) {}

                            });

                        });

                    }
                """)

            except Exception:
                pass

            yaz("[BEKLE] ATV oynatıcısı taranıyor...")

            page.wait_for_timeout(TARAMA_SURESI)

            # -----------------------------------------
            # BOOKMARKLET MANTIĞI
            # -----------------------------------------

            try:

                sonuclar = page.evaluate(r"""
                    () => {

                        let u = new Set();

                        // Performance
                        performance
                        .getEntriesByType('resource')
                        .forEach(r => {

                            if (r.name.includes('.m3u8')) {
                                u.add(r.name);
                            }

                        });

                        // HTML
                        let h = document.documentElement.innerHTML;

                        let re = /https?:\/\/[^"'\s<>]+\.m3u8[^"'\s<>]*/gi;

                        let m = h.match(re);

                        if (m) {
                            m.forEach(x => u.add(x));
                        }

                        // Video ve source
                        document.querySelectorAll('video, source')
                        .forEach(v => {

                            if (v.src) {
                                u.add(v.src);
                            }

                            if (v.currentSrc) {
                                u.add(v.currentSrc);
                            }

                        });

                        return [...u];

                    }
                """)

                for url in sonuclar:

                    aday_ekle(
                        url,
                        {},
                        "BOOKMARKLET"
                    )

            except Exception as hata:

                yaz("[BOOKMARKLET HATA] " + str(hata)[:300])

            # -----------------------------------------
            # ÇEREZLER
            # -----------------------------------------

            try:

                for cookie in context.cookies():

                    session.cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie.get("domain"),
                        path=cookie.get("path", "/")
                    )

                yaz("[OK] Çerezler aktarıldı.")

            except Exception:
                pass

            browser.close()

        adaylar = list(aday_basliklari.keys())

        adaylar.sort(
            key=kalite_puani,
            reverse=True
        )

        yaz("")
        yaz(f"[TARAMA TAMAMLANDI] {len(adaylar)} GERÇEK ATV ADRESİ")

        return adaylar

    except Exception as hata:

        yaz("[PLAYWRIGHT HATA] " + str(hata)[:500])

        return list(aday_basliklari.keys())


# =====================================================
# BAŞLIKLARI UYGULA
# =====================================================

def baslik_uygula(url):

    session.headers.clear()

    session.headers.update({
        "User-Agent": UA,
        "Referer": REFERER,
        "Origin": ORIGIN,
        "Accept": "*/*"
    })

    gelen = aday_basliklari.get(url, {})

    izinli = (
        "user-agent",
        "referer",
        "origin",
        "accept",
        "accept-language"
    )

    for isim, deger in gelen.items():

        if isim.lower() in izinli and deger:

            session.headers[isim] = deger


# =====================================================
# HLS OKU
# =====================================================

def hls_oku(url):

    try:

        r = session.get(
            url,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )

        yaz(
            f"[HLS HTTP] {r.status_code} "
            f"| {guvenli_url(r.url)}"
        )

        if r.status_code != 200:

            r.close()

            return None, None

        icerik = r.text.lstrip("\ufeff \r\n\t")
        son_url = r.url

        r.close()

        if not icerik.startswith("#EXTM3U"):

            yaz("[HATA] Geçerli HLS playlist değil.")

            return None, None

        return icerik, son_url

    except requests.RequestException as hata:

        yaz("[HLS HATA] " + str(hata)[:250])

        return None, None


# =====================================================
# URI BUL
# =====================================================

def uri_bul(satir):

    m = re.search(
        r'URI="([^"]+)"',
        satir
    )

    return m.group(1) if m else None


# =====================================================
# SEGMENT TEST
# =====================================================

def parca_test(url):

    try:

        r = session.get(
            url,
            timeout=TIMEOUT,
            verify=False,
            stream=True,
            headers={
                "Range": "bytes=0-16383"
            }
        )

        if r.status_code not in (200, 206):

            yaz(f"[PARÇA HTTP] {r.status_code}")

            r.close()

            return False

        veri = r.raw.read(16384)

        r.close()

        if len(veri) < 100:
            return False

        ilk = veri[:500].lower()

        if any(x in ilk for x in (
            b"<html",
            b"<!doctype",
            b"access denied",
            b"forbidden",
            b"cloudflare"
        )):
            return False

        return True

    except requests.RequestException as hata:

        yaz("[PARÇA HATA] " + str(hata)[:200])

        return False


# =====================================================
# HLS TEST
# =====================================================

def hls_test(url):

    yaz("")
    yaz("[TEST] " + guvenli_url(url))

    icerik, son_url = hls_oku(url)

    if not icerik:
        return False

    satirlar = [
        x.strip()
        for x in icerik.splitlines()
        if x.strip()
    ]

    varyantlar = []

    for i, satir in enumerate(satirlar):

        if satir.startswith("#EXT-X-STREAM-INF:"):

            m = re.search(
                r'BANDWIDTH=(\d+)',
                satir
            )

            hiz = int(m.group(1)) if m else 0

            if i + 1 < len(satirlar):

                alt = satirlar[i + 1]

                if not alt.startswith("#"):

                    varyantlar.append(
                        (hiz, urljoin(son_url, alt))
                    )

    medya = None
    medya_url = None

    if varyantlar:

        varyantlar.sort(
            key=lambda x: x[0],
            reverse=True
        )

        for hiz, alt_url in varyantlar:

            yaz(f"[VARYANT TEST] {hiz}")

            medya, medya_url = hls_oku(alt_url)

            if medya:
                break

        if not medya:

            yaz("[HATA] Alt playlist okunamadı.")

            return False

    else:

        medya = icerik
        medya_url = son_url

    medya_satirlari = [
        x.strip()
        for x in medya.splitlines()
        if x.strip()
    ]

    # AES anahtarı
    for satir in medya_satirlari:

        if satir.startswith("#EXT-X-KEY:"):

            if "METHOD=NONE" in satir:
                continue

            anahtar = uri_bul(satir)

            if anahtar:

                adres = urljoin(medya_url, anahtar)

                try:

                    r = session.get(
                        adres,
                        timeout=TIMEOUT,
                        verify=False
                    )

                    ok = (
                        r.status_code == 200
                        and len(r.content) >= 16
                    )

                    r.close()

                    if not ok:
                        return False

                except requests.RequestException:
                    return False

            elif "METHOD=AES-128" in satir:
                return False

    # INIT segment
    for satir in medya_satirlari:

        if satir.startswith("#EXT-X-MAP:"):

            uri = uri_bul(satir)

            if uri:

                adres = urljoin(medya_url, uri)

                if not parca_test(adres):
                    return False

            break

    # Video segment
    parcalar = [
        x for x in medya_satirlari
        if not x.startswith("#")
    ]

    if not parcalar:

        yaz("[HATA] Video parçası yok.")

        return False

    adres = urljoin(
        medya_url,
        parcalar[0]
    )

    if not parca_test(adres):

        yaz("[HATA] Video parçası alınamadı.")

        return False

    yaz("[OK] ATV HLS YAYINI ÇALIŞIYOR.")

    return True


# =====================================================
# YAYIN BUL
# =====================================================

def yayin_bul():

    adaylar = playwright_tara()

    if not adaylar:

        yaz("[BAŞARISIZ] Gerçek ATV adresi bulunamadı.")

        return None

    yaz("")
    yaz(f"[TOPLAM GERÇEK ATV ADAYI] {len(adaylar)}")

    for no, url in enumerate(adaylar, 1):

        yaz("")
        yaz(f"[ADAY TEST] {no}/{len(adaylar)}")

        baslik_uygula(url)

        if hls_test(url):

            yaz("[BAŞARILI] ATV adresi doğrulandı.")

            return url

    yaz("[BAŞARISIZ] ATV yayını doğrulanamadı.")

    return None


# =====================================================
# M3U SATIRLARI
# =====================================================

def atv_satirlari(url):

    return [
        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL}'
        ),
        f"#EXTVLCOPT:http-referrer={REFERER}",
        f"#EXTVLCOPT:http-origin={ORIGIN}",
        f"#EXTVLCOPT:http-user-agent={UA}",
        url
    ]


# =====================================================
# ATV KAYIT TANIMA
# =====================================================

def atv_blok_mu(blok):

    metin = "\n".join(blok)

    if f'tvg-id="{TVG_ID}"' in metin:
        return True

    if f'tvg-name="{KANAL}"' in metin:
        return True

    for satir in blok:

        if satir.startswith("#EXTINF:"):

            parca = satir.split(",", 1)

            if len(parca) > 1:

                if parca[1].strip() == KANAL:
                    return True

    return False


# =====================================================
# M3U GÜNCELLE
# =====================================================

def m3u_guncelle(url):

    yaz("")
    yaz("[3] M3U GÜNCELLEME")

    if not os.path.isfile(DOSYA):

        yaz("[HATA] mirti68.m3u bulunamadı.")

        return False

    gecici = DOSYA + ".tmp"

    try:

        with open(
            DOSYA,
            "r",
            encoding="utf-8-sig"
        ) as f:

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

        grup_indeksleri = []

        for i, blok in enumerate(bloklar):

            extinf = next(
                (
                    x for x in blok
                    if x.startswith("#EXTINF:")
                ),
                ""
            )

            grup = re.search(
                r'group-title="([^"]*)"',
                extinf
            )

            if grup and grup.group(1) == GRUP:
                grup_indeksleri.append(i)

        if not grup_indeksleri:

            yaz("[HATA] ULUSAL grubu bulunamadı.")

            return False

        son_grup = grup_indeksleri[-1]

        temiz_bloklar = []
        ekleme_indeksi = 0
        eski_atv = 0

        for i, blok in enumerate(bloklar):

            if atv_blok_mu(blok):

                eski_atv += 1
                continue

            temiz_bloklar.append(blok)

            if i <= son_grup:
                ekleme_indeksi += 1

        temiz_bloklar.insert(
            ekleme_indeksi,
            atv_satirlari(url)
        )

        with open(
            gecici,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n".join(baslik).rstrip() + "\n"
            )

            for blok in temiz_bloklar:

                f.write(
                    "\n".join(blok).rstrip() + "\n"
                )

        os.replace(
            gecici,
            DOSYA
        )

        yaz(f"[OK] Eski ATV kayıtları: {eski_atv}")
        yaz("[OK] Yeni ATV kaydı eklendi.")
        yaz("[OK] Diğer kanallar korundu.")
        yaz("[OK] EPG başlıkları korundu.")
        yaz("[OK] M3U güncellendi.")

        return True

    except Exception as hata:

        yaz("[M3U HATA] " + str(hata)[:500])

        if os.path.exists(gecici):

            try:
                os.remove(gecici)
            except OSError:
                pass

        return False


# =====================================================
# ANA PROGRAM
# =====================================================

def main():

    yaz("")
    yaz("########################################")
    yaz("#                                      #")
    yaz("#       MIRTI68 ATV 1080P SISTEMI      #")
    yaz("#                                      #")
    yaz("########################################")

    adres = yayin_bul()

    if not adres:

        yaz("[SONUÇ] ATV güncellenmedi.")
        yaz("[SONUÇ] Eski M3U korundu.")

        return 1

    yaz("")
    yaz("[SEÇİLEN TAM URL]")
    yaz(adres)

    if not m3u_guncelle(adres):

        yaz("[SONUÇ] M3U güncellenemedi.")

        return 1

    yaz("")
    yaz("########################################")
    yaz("#       ATV ISLEMI BASARILI            #")
    yaz("########################################")

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
