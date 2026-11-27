
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import subprocess
import requests
import urllib3

from urllib.parse import urljoin, urlsplit
from playwright.sync_api import sync_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# AYARLAR
# =========================================================

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"
ORIGIN = "https://www.atv.com.tr"
REFERER = SAYFA_URL

DOSYA = "mirti68.m3u"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
KANAL = "ATVᴴᴰ⭕"
TVG_ID = "atv.tr"

LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TIMEOUT = 25
TARAMA_SURESI = 45000

# =========================================================
# OTURUM
# =========================================================

session = requests.Session()

session.headers.update({
    "User-Agent": UA,
    "Referer": REFERER,
    "Origin": ORIGIN,
    "Accept": "*/*",
})

aday_basliklari = {}


def yaz(mesaj):
    print(mesaj, flush=True)


def guvenli_url(url):
    try:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}{p.path}"
    except Exception:
        return url


def m3u8_mi(url):
    try:
        p = urlsplit(url)
        return (
            p.scheme in ("http", "https")
            and ".m3u8" in p.path.lower()
        )
    except Exception:
        return False


def atv_puani(url):
    """
    ATV ile ilişkili olabilecek adreslere öncelik verir.
    Bilinmeyen CDN adreslerini de tamamen elemez.
    """

    p = urlsplit(url)

    host = p.netloc.lower()
    yol = p.path.lower()
    tam = url.lower()

    puan = 0

    if "trkvz.daioncdn.net" in host:
        puan += 100

    if "daioncdn" in host:
        puan += 60

    if "trkvz" in host:
        puan += 50

    if "/atv/" in yol:
        puan += 100

    if "atv" in host:
        puan += 50

    if "atv" in tam:
        puan += 20

    return puan


# =========================================================
# PLAYWRIGHT TARAMASI
# =========================================================

def playwright_tara():

    yaz("")
    yaz("========================================")
    yaz("[1] PLAYWRIGHT ATV TARAMASI")
    yaz("========================================")

    bulunan = []

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

            def adres_ekle(url, headers=None, kaynak="REQUEST"):

                if not m3u8_mi(url):
                    return

                if url not in bulunan:

                    bulunan.append(url)

                    aday_basliklari[url] = headers or {}

                    yaz("")
                    yaz(f"[M3U8 {len(bulunan)}] {kaynak}")
                    yaz("[ADRES] " + guvenli_url(url))
                    yaz("[HOST] " + urlsplit(url).netloc)

                    puan = atv_puani(url)

                    yaz(f"[ATV PUANI] {puan}")

            # Ağ isteklerini yakala

            def request_yakala(request):

                try:
                    adres_ekle(
                        request.url,
                        request.headers,
                        "REQUEST"
                    )
                except Exception:
                    pass

            # Sunucu cevaplarını da kontrol et

            def response_yakala(response):

                try:
                    adres_ekle(
                        response.url,
                        response.request.headers,
                        "RESPONSE"
                    )
                except Exception:
                    pass

            page.on("request", request_yakala)
            page.on("response", response_yakala)

            # ATV sayfasını aç

            try:

                yaz("[SAYFA] ATV açılıyor...")

                page.goto(
                    SAYFA_URL,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                yaz("[OK] ATV sayfası açıldı.")

            except Exception as hata:

                yaz("[SAYFA UYARISI] " + str(hata)[:300])

            # Oynatıcıları başlatmayı dene

            try:

                page.evaluate("""
                    () => {

                        document.querySelectorAll('video').forEach(v => {

                            v.muted = true;

                            v.play().catch(() => {});

                        });

                    }
                """)

            except Exception:
                pass

            # Yayın adreslerini bekle

            yaz("")
            yaz("[TARAMA] M3U8 adresleri bekleniyor...")
            yaz(f"[BEKLEME] {TARAMA_SURESI // 1000} saniye")

            page.wait_for_timeout(TARAMA_SURESI)

            # Tarayıcı performans kayıtlarını kontrol et

            try:

                performans = page.evaluate("""
                    () => performance
                        .getEntriesByType('resource')
                        .map(x => x.name)
                """)

                for url in performans:

                    if m3u8_mi(url):
                        adres_ekle(
                            url,
                            {},
                            "PERFORMANCE"
                        )

            except Exception as hata:

                yaz("[PERFORMANCE UYARI] " + str(hata)[:200])

            # Çerezleri requests oturumuna aktar

            try:

                for cookie in context.cookies():

                    session.cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie.get("domain"),
                        path=cookie.get("path", "/")
                    )

                yaz("[OK] Tarayıcı çerezleri aktarıldı.")

            except Exception as hata:

                yaz("[COOKIE UYARI] " + str(hata)[:200])

            browser.close()

        # ATV puanına göre sırala

        bulunan.sort(
            key=atv_puani,
            reverse=True
        )

        yaz("")
        yaz(f"[TARAMA TAMAMLANDI] {len(bulunan)} M3U8 bulundu.")

        return bulunan

    except Exception as hata:

        yaz("[PLAYWRIGHT HATASI] " + str(hata)[:500])

        return bulunan


# =========================================================
# STREAMLINK YEDEK TARAMASI
# =========================================================

def streamlink_tara():

    yaz("")
    yaz("========================================")
    yaz("[2] STREAMLINK YEDEK TARAMASI")
    yaz("========================================")

    yol = shutil.which("streamlink")

    if not yol:

        yaz("[UYARI] Streamlink bulunamadı.")

        return []

    komut = [
        yol,
        "--loglevel", "error",
        "--http-header", f"Referer={REFERER}",
        "--http-header", f"Origin={ORIGIN}",
        "--http-header", f"User-Agent={UA}",
        "--stream-url",
        SAYFA_URL,
        "best"
    ]

    try:

        sonuc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            timeout=90
        )

        bulunan = []

        for satir in sonuc.stdout.splitlines():

            satir = satir.strip()

            if m3u8_mi(satir):

                if satir not in bulunan:

                    bulunan.append(satir)

                    yaz("[STREAMLINK] M3U8 bulundu.")
                    yaz("[ADRES] " + guvenli_url(satir))

        if not bulunan:

            yaz("[STREAMLINK] Adres bulunamadı.")

        return bulunan

    except Exception as hata:

        yaz("[STREAMLINK HATASI] " + str(hata)[:300])

        return []


# =========================================================
# ADAY BAŞLIKLARINI UYGULA
# =========================================================

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
        "accept-language",
    )

    for isim, deger in gelen.items():

        if isim.lower() in izinli and deger:

            session.headers[isim] = deger


# =========================================================
# HLS PLAYLIST OKU
# =========================================================

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

            yaz("[HATA] Geçerli M3U8 içeriği değil.")

            return None, None

        return icerik, son_url

    except requests.RequestException as hata:

        yaz("[HLS HATA] " + str(hata)[:250])

        return None, None


# =========================================================
# HLS URI BUL
# =========================================================

def uri_bul(satir):

    m = re.search(
        r'URI="([^"]+)"',
        satir
    )

    return m.group(1) if m else None


# =========================================================
# VİDEO PARÇASI TESTİ
# =========================================================

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

            yaz("[PARÇA] Veri çok küçük.")

            return False

        ilk = veri[:500].lower()

        yasakli = (
            b"<html",
            b"<!doctype",
            b"access denied",
            b"forbidden",
            b"cloudflare"
        )

        if any(x in ilk for x in yasakli):

            yaz("[PARÇA] Sunucu hata sayfası döndürdü.")

            return False

        return True

    except requests.RequestException as hata:

        yaz("[PARÇA HATA] " + str(hata)[:200])

        return False


# =========================================================
# HLS YAYIN TESTİ
# =========================================================

def hls_test(url):

    yaz("")
    yaz("========================================")
    yaz("[HLS TEST]")
    yaz(guvenli_url(url))
    yaz("========================================")

    icerik, son_url = hls_oku(url)

    if not icerik:

        yaz("[HATA] Ana playlist okunamadı.")

        return False

    satirlar = [
        x.strip()
        for x in icerik.splitlines()
        if x.strip()
    ]

    varyantlar = []

    # Master playlist kontrolü

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
                        (
                            hiz,
                            urljoin(son_url, alt)
                        )
                    )

    # En yüksek kaliteden başlayarak dene

    medya = None
    medya_url = None

    if varyantlar:

        varyantlar.sort(
            key=lambda x: x[0],
            reverse=True
        )

        yaz(f"[VARYANT] {len(varyantlar)} kalite bulundu.")

        for hiz, alt_url in varyantlar:

            yaz(f"[VARYANT TEST] {hiz} bps")

            alt_icerik, alt_son_url = hls_oku(alt_url)

            if alt_icerik:

                medya = alt_icerik
                medya_url = alt_son_url

                yaz("[OK] Alt playlist açıldı.")

                break

        if not medya:

            yaz("[HATA] Hiçbir alt playlist açılamadı.")

            return False

    else:

        medya = icerik
        medya_url = son_url

    medya_satirlari = [
        x.strip()
        for x in medya.splitlines()
        if x.strip()
    ]

    # AES-128 anahtar kontrolü

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

                        yaz("[HATA] Anahtar alınamadı.")

                        return False

                except requests.RequestException:

                    yaz("[HATA] Anahtar isteği başarısız.")

                    return False

            elif "METHOD=AES-128" in satir:

                yaz("[HATA] AES-128 anahtar URI bulunamadı.")

                return False

    # INIT segment kontrolü

    for satir in medya_satirlari:

        if satir.startswith("#EXT-X-MAP:"):

            uri = uri_bul(satir)

            if uri:

                init_url = urljoin(medya_url, uri)

                yaz("[INIT TEST]")

                if not parca_test(init_url):

                    yaz("[HATA] INIT segment başarısız.")

                    return False

            break

    # Video parçalarını bul

    parcalar = [
        x for x in medya_satirlari
        if not x.startswith("#")
    ]

    if not parcalar:

        yaz("[HATA] Video parçası bulunamadı.")

        return False

    # İlk parçayı test et

    parca_url = urljoin(
        medya_url,
        parcalar[0]
    )

    yaz("[VIDEO PARÇA TEST]")

    if not parca_test(parca_url):

        yaz("[HATA] Video parçası indirilemedi.")

        return False

    yaz("")
    yaz("[OK] HLS PLAYLIST ÇALIŞIYOR.")
    yaz("[OK] VIDEO PARÇASI ALINDI.")

    return True


# =========================================================
# ÇALIŞAN ATV YAYININI BUL
# =========================================================

def yayin_bul():

    adaylar = playwright_tara()

    for url in streamlink_tara():

        if url not in adaylar:

            adaylar.append(url)

    if not adaylar:

        yaz("")
        yaz("[BAŞARISIZ] Hiç M3U8 adresi bulunamadı.")

        return None

    # ATV adreslerine öncelik ver

    adaylar = sorted(
        adaylar,
        key=atv_puani,
        reverse=True
    )

    yaz("")
    yaz("========================================")
    yaz(f"[TOPLAM ADAY] {len(adaylar)}")
    yaz("========================================")

    for no, url in enumerate(adaylar, 1):

        yaz("")
        yaz(f"[ADAY TEST] {no}/{len(adaylar)}")

        yaz("[URL] " + guvenli_url(url))

        baslik_uygula(url)

        if hls_test(url):

            yaz("")
            yaz("[BAŞARILI] Çalışan yayın bulundu.")

            return url

    yaz("")
    yaz("[BAŞARISIZ] Çalışan yayın bulunamadı.")

    return None


# =========================================================
# ATV M3U SATIRLARI
# =========================================================

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


# =========================================================
# ATV KAYDINI TANIMA
# =========================================================

def atv_blok_mu(blok):

    metin = "\n".join(blok)

    if f'tvg-id="{TVG_ID}"' in metin:
        return True

    if f'tvg-name="{KANAL}"' in metin:
        return True

    for satir in blok:

        if satir.startswith("#EXTINF:"):

            isim = satir.split(",", 1)

            if len(isim) > 1:

                if isim[1].strip() == KANAL:
                    return True

    return False


# =========================================================
# M3U GÜNCELLE
# =========================================================

def m3u_guncelle(url):

    yaz("")
    yaz("========================================")
    yaz("[3] M3U GÜNCELLEME")
    yaz("========================================")

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

        # M3U başlığını ve yayın bloklarını ayır

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

        # Hedef grubun son konumunu bul

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

            yaz("[BİLGİ] Mevcut gruplara dokunulmadı.")

            return False

        son_grup = grup_indeksleri[-1]

        # Eski ATV kayıtlarını kaldır

        temiz_bloklar = []

        ekleme_indeksi = 0

        eski_atv = 0

        for i, blok in enumerate(bloklar):

            atv = atv_blok_mu(blok)

            if atv:

                eski_atv += 1

                continue

            temiz_bloklar.append(blok)

            if i <= son_grup:

                ekleme_indeksi += 1

        # Yeni ATV kaydını hedef gruba yerleştir

        yeni_blok = atv_satirlari(url)

        temiz_bloklar.insert(
            ekleme_indeksi,
            yeni_blok
        )

        # Dosyayı güvenli şekilde yaz

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

        # Eski dosyanın yerine geç

        os.replace(
            gecici,
            DOSYA
        )

        yaz("")
        yaz("[OK] ATV kaydı güncellendi.")
        yaz(f"[OK] Eski ATV kaydı: {eski_atv}")
        yaz("[OK] Yeni ATV kaydı eklendi.")
        yaz("[OK] Diğer kanallar korundu.")
        yaz("[OK] Diğer gruplar korundu.")
        yaz("[OK] EPG başlıkları korundu.")
        yaz("[OK] M3U dosyası kaydedildi.")

        return True

    except Exception as hata:

        yaz("[M3U HATASI] " + str(hata)[:500])

        if os.path.exists(gecici):

            try:
                os.remove(gecici)
            except OSError:
                pass

        return False


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    yaz("")
    yaz("########################################")
    yaz("#                                      #")
    yaz("#       MIRTI68 ATV YAYIN SISTEMI      #")
    yaz("#                                      #")
    yaz("########################################")

    yaz("[BAŞLA] ATV canlı yayın aranıyor.")

    adres = yayin_bul()

    if not adres:

        yaz("")
        yaz("[SONUÇ] ATV güncellenmedi.")
        yaz("[SONUÇ] Mevcut M3U korunuyor.")

        return 1

    yaz("")
    yaz("========================================")
    yaz("[SEÇİLEN ATV URL]")
    yaz(guvenli_url(adres))
    yaz("========================================")

    if not m3u_guncelle(adres):

        yaz("[SONUÇ] M3U güncellenemedi.")

        return 1

    yaz("")
    yaz("########################################")
    yaz("#                                      #")
    yaz("#       MIRTI68 ATV ISLEMI BASARILI    #")
    yaz("#                                      #")
    yaz("########################################")

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
