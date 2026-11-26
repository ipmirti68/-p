
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import subprocess
import requests
import urllib3

from pathlib import Path
from urllib.parse import urljoin, urlsplit

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

# ==================================================
# MIRTI68 - ATV GÜNCEL YAYIN SİSTEMİ
# PLAYWRIGHT + STREAMLINK + HLS TEST
# ==================================================

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"

M3U_DOSYA = "mirti68.m3u"

GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
KANAL = "ATVᴴᴰ⭕"
TVG_ID = "atv.tr"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

REFERER = SAYFA_URL
ORIGIN = "https://www.atv.com.tr"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TIMEOUT = 30
TARAMA_SURESI = 30000


# ==================================================
# HTTP OTURUMU
# ==================================================

session = requests.Session()

session.headers.update({
    "User-Agent": USER_AGENT,
    "Referer": REFERER,
    "Origin": ORIGIN,
    "Accept": "*/*",
    "Connection": "keep-alive"
})


# ==================================================
# GÜVENLİ URL GÖSTERİMİ
# ==================================================

def guvenli_adres(adres):

    try:

        p = urlsplit(adres)

        return (
            p.scheme + "://" +
            p.netloc +
            p.path
        )

    except Exception:

        return "Adres gizlendi"


# ==================================================
# ATV M3U8 ADRES KONTROLÜ
# ==================================================

def atv_hls_mi(adres):

    if not adres:
        return False

    try:

        p = urlsplit(adres)

        return (
            p.scheme in ("http", "https")
            and "trkvz.daioncdn.net" in p.netloc.lower()
            and "/atv/" in p.path.lower()
            and ".m3u8" in p.path.lower()
        )

    except Exception:

        return False


# ==================================================
# PLAYWRIGHT İLE GÜNCEL ADRESİ YAKALA
# ==================================================

def playwright_ile_yayin_al():

    print("")
    print("[1] ATV resmî sayfası taranıyor...")

    try:

        from playwright.sync_api import sync_playwright

    except ImportError:

        print("[HATA] Playwright bulunamadı.")

        return None

    bulunan_adresler = []
    yakalanan_basliklar = {}

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )

            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={
                    "width": 1365,
                    "height": 768
                },
                ignore_https_errors=True
            )

            page = context.new_page()

            # ------------------------------------------
            # HLS İSTEKLERİNİ YAKALA
            # ------------------------------------------

            def istek_yakala(istek):

                url = istek.url

                if not atv_hls_mi(url):
                    return

                if url not in bulunan_adresler:

                    bulunan_adresler.append(url)

                    try:

                        yakalanan_basliklar[url] = (
                            istek.headers
                        )

                    except Exception:

                        yakalanan_basliklar[url] = {}

                    print(
                        "[M3U8 YAKALANDI]",
                        guvenli_adres(url)
                    )

            page.on(
                "request",
                istek_yakala
            )

            # ------------------------------------------
            # SAYFAYI AÇ
            # ------------------------------------------

            try:

                page.goto(
                    SAYFA_URL,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                print("[OK] ATV sayfası açıldı.")

            except Exception as hata:

                print(
                    "[UYARI] Sayfa yükleme:",
                    str(hata)[:400]
                )

            # ------------------------------------------
            # VİDEO OYNATMAYI TETİKLE
            # ------------------------------------------

            try:

                page.evaluate("""
                    () => {
                        document.querySelectorAll('video').forEach(v => {
                            v.muted = true;
                            const p = v.play();
                            if (p && p.catch) p.catch(() => {});
                        });
                    }
                """)

            except Exception:

                pass

            # ------------------------------------------
            # YAYIN İSTEKLERİNİ BEKLE
            # ------------------------------------------

            print("[BİLGİ] M3U8 isteği bekleniyor...")

            page.wait_for_timeout(
                TARAMA_SURESI
            )

            # ------------------------------------------
            # ÇEREZLERİ AKTAR
            # ------------------------------------------

            try:

                cerezler = context.cookies()

                for cookie in cerezler:

                    try:

                        session.cookies.set(
                            cookie["name"],
                            cookie["value"],
                            domain=cookie.get("domain"),
                            path=cookie.get("path", "/")
                        )

                    except Exception:

                        pass

                print(
                    "[OK] Çerez sayısı:",
                    len(cerezler)
                )

            except Exception as hata:

                print(
                    "[UYARI] Çerez aktarımı:",
                    str(hata)[:300]
                )

            browser.close()

        # ------------------------------------------
        # ADRES BULUNDU MU?
        # ------------------------------------------

        if not bulunan_adresler:

            print(
                "[HATA] Tarayıcı M3U8 adresi yakalayamadı."
            )

            return None

        adres = bulunan_adresler[-1]

        # ------------------------------------------
        # İSTEK BAŞLIKLARINI AKTAR
        # ------------------------------------------

        basliklar = yakalanan_basliklar.get(
            adres,
            {}
        )

        for isim in (
            "user-agent",
            "referer",
            "origin",
            "accept",
            "accept-language"
        ):

            deger = basliklar.get(isim)

            if deger:

                session.headers[isim] = deger

        print("[BAŞARILI] Güncel ATV adresi yakalandı.")
        print("[URL]", guvenli_adres(adres))

        return adres

    except Exception as hata:

        print(
            "[PLAYWRIGHT HATASI]",
            str(hata)[:1000]
        )

        return None


# ==================================================
# STREAMLINK YEDEK YÖNTEM
# ==================================================

def streamlink_bul():

    yol = shutil.which("streamlink")

    if yol:

        print("[OK] Streamlink bulundu.")

        return yol

    print("[UYARI] Streamlink bulunamadı.")

    return None


def streamlink_ile_yayin_al():

    print("")
    print("[2] Streamlink yedek yöntem deneniyor...")

    streamlink = streamlink_bul()

    if not streamlink:
        return None

    komut = [
        streamlink,
        "--loglevel", "error",
        "--http-header", f"Referer={REFERER}",
        "--http-header", f"Origin={ORIGIN}",
        "--http-header", f"User-Agent={USER_AGENT}",
        "--stream-url",
        SAYFA_URL,
        "best"
    ]

    try:

        sonuc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            timeout=60
        )

        print(
            "[STREAMLINK ÇIKIŞ]",
            sonuc.returncode
        )

        if sonuc.returncode != 0:

            print("[HATA] Streamlink başarısız.")

            if sonuc.stderr:

                print(
                    sonuc.stderr[-1000:]
                )

            return None

        for satir in sonuc.stdout.splitlines():

            satir = satir.strip()

            if atv_hls_mi(satir):

                print("[OK] Streamlink adresi bulundu.")

                print(
                    "[URL]",
                    guvenli_adres(satir)
                )

                return satir

        print("[HATA] Streamlink M3U8 bulamadı.")

        return None

    except Exception as hata:

        print("[STREAMLINK HATASI]", hata)

        return None


# ==================================================
# ATV YAYIN ADRESİNİ AL
# ==================================================

def atv_yayinini_al():

    adres = playwright_ile_yayin_al()

    if adres:

        return adres

    print("[UYARI] Playwright sonuç vermedi.")

    return streamlink_ile_yayin_al()


# ==================================================
# HLS PLAYLIST OKU
# ==================================================

def hls_oku(adres, baslik):

    try:

        cevap = session.get(
            adres,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )

        print(
            f"[{baslik}] HTTP:",
            cevap.status_code
        )

        if cevap.status_code != 200:

            return None, None

        icerik = cevap.text.lstrip(
            "\ufeff \r\n\t"
        )

        if not icerik.startswith("#EXTM3U"):

            print(
                f"[HATA] {baslik}: HLS biçimi değil."
            )

            return None, None

        return icerik, cevap.url

    except requests.RequestException as hata:

        print(
            f"[HATA] {baslik}:",
            str(hata)[:500]
        )

        return None, None


# ==================================================
# HLS URI BUL
# ==================================================

def hls_uri_bul(satir):

    eslesme = re.search(
        r'URI="([^"]+)"',
        satir
    )

    if eslesme:

        return eslesme.group(1)

    return None


# ==================================================
# YAYIN PARÇASI TESTİ
# ==================================================

def parca_test(adres, aciklama):

    print("")
    print("[TEST]", aciklama)

    print(
        "[URL]",
        guvenli_adres(adres)
    )

    try:

        cevap = session.get(
            adres,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True,
            stream=True
        )

        print(
            "[HTTP]",
            cevap.status_code
        )

        if cevap.status_code not in (200, 206):

            print("[HATA] Parça indirilemedi.")

            cevap.close()

            return False

        veri = cevap.raw.read(65536)

        cevap.close()

        print(
            "[İNDİRİLEN BYTE]",
            len(veri)
        )

        if len(veri) < 100:

            print("[HATA] Veri çok küçük.")

            return False

        ilk = veri[:500].lstrip().lower()

        if (
            ilk.startswith(b"<!doctype html")
            or ilk.startswith(b"<html")
            or b"access denied" in ilk
            or b"forbidden" in ilk
        ):

            print("[HATA] HTML hata sayfası döndü.")

            return False

        print("[OK] Yayın parçası indirilebildi.")

        return True

    except requests.RequestException as hata:

        print(
            "[PARÇA HATASI]",
            str(hata)[:500]
        )

        return False


# ==================================================
# ŞİFRELEME ANAHTARI TESTİ
# ==================================================

def anahtar_test(adres):

    print("")
    print("[TEST] HLS şifreleme anahtarı")

    try:

        cevap = session.get(
            adres,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )

        print(
            "[ANAHTAR HTTP]",
            cevap.status_code
        )

        if cevap.status_code != 200:

            return False

        if len(cevap.content) < 16:

            print("[HATA] Anahtar verisi eksik.")

            return False

        print("[OK] Anahtar indirilebildi.")

        return True

    except requests.RequestException as hata:

        print(
            "[ANAHTAR HATASI]",
            str(hata)[:500]
        )

        return False


# ==================================================
# HLS YAYIN ZİNCİR TESTİ
# ==================================================

def hls_zincir_test(adres):

    print("")
    print("======================================")
    print("MIRTI68 ATV HLS ZİNCİR TESTİ")
    print("======================================")

    icerik, son_adres = hls_oku(
        adres,
        "ANA M3U8"
    )

    if not icerik:

        print("[BAŞARISIZ] Ana M3U8 okunamadı.")

        return False

    print("[OK] Ana M3U8 okundu.")

    satirlar = [
        x.strip()
        for x in icerik.splitlines()
        if x.strip()
    ]

    # ------------------------------------------
    # MASTER PLAYLIST
    # ------------------------------------------

    varyantlar = []

    for i, satir in enumerate(satirlar):

        if satir.startswith("#EXT-X-STREAM-INF:"):

            bant = re.search(
                r"BANDWIDTH=(\d+)",
                satir
            )

            hiz = int(bant.group(1)) if bant else 0

            if i + 1 < len(satirlar):

                alt = satirlar[i + 1]

                if not alt.startswith("#"):

                    varyantlar.append(
                        (
                            hiz,
                            urljoin(son_adres, alt)
                        )
                    )

    if varyantlar:

        varyantlar.sort(
            key=lambda x: x[0],
            reverse=True
        )

        alt_adres = varyantlar[0][1]

        print(
            "[OK] Master playlist bulundu."
        )

        print(
            "[VARYANT SAYISI]",
            len(varyantlar)
        )

        medya, medya_adresi = hls_oku(
            alt_adres,
            "ALT M3U8"
        )

        if not medya:

            print("[BAŞARISIZ] Alt M3U8 okunamadı.")

            return False

    else:

        print("[BİLGİ] Doğrudan medya playlist'i.")

        medya = icerik
        medya_adresi = son_adres

    # ------------------------------------------
    # ŞİFRELEME ANAHTARI
    # ------------------------------------------

    for satir in medya.splitlines():

        if not satir.startswith("#EXT-X-KEY:"):
            continue

        if "METHOD=NONE" in satir:
            continue

        anahtar = hls_uri_bul(satir)

        if anahtar:

            anahtar_adresi = urljoin(
                medya_adresi,
                anahtar
            )

            if not anahtar_test(anahtar_adresi):

                return False

        elif "METHOD=AES-128" in satir:

            print("[HATA] AES anahtar URI bulunamadı.")

            return False

    # ------------------------------------------
    # INIT SEGMENT
    # ------------------------------------------

    for satir in medya.splitlines():

        if satir.startswith("#EXT-X-MAP:"):

            uri = hls_uri_bul(satir)

            if uri:

                map_adresi = urljoin(
                    medya_adresi,
                    uri
                )

                if not parca_test(
                    map_adresi,
                    "INIT SEGMENT"
                ):

                    return False

            break

    # ------------------------------------------
    # İLK VİDEO PARÇASI
    # ------------------------------------------

    parca_adresi = None

    for satir in medya.splitlines():

        satir = satir.strip()

        if not satir or satir.startswith("#"):
            continue

        parca_adresi = urljoin(
            medya_adresi,
            satir
        )

        break

    if not parca_adresi:

        print("[HATA] Video parçası bulunamadı.")

        return False

    if not parca_test(
        parca_adresi,
        "İLK VİDEO PARÇASI"
    ):

        return False

    print("")
    print("[BAŞARILI] HLS zinciri test edildi.")

    return True


# ==================================================
# ATV M3U KAYDI
# ==================================================

def atv_m3u_kaydi(adres):

    return [

        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL}" '
            f'tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL}'
        ),

        f"#EXTVLCOPT:http-referrer={REFERER}",

        f"#EXTVLCOPT:http-origin={ORIGIN}",

        f"#EXTVLCOPT:http-user-agent={USER_AGENT}",

        adres
    ]


# ==================================================
# ATV KAYDINI TANIMA
# ==================================================

def atv_mi(blok):

    metin = "\n".join(blok)

    return (
        f'tvg-id="{TVG_ID}"' in metin
        or KANAL in metin
    )


# ==================================================
# HEDEF GRUP KONTROLÜ
# ==================================================

def hedef_grup_mu(blok):

    for satir in blok:

        if not satir.startswith("#EXTINF:"):
            continue

        eslesme = re.search(
            r'group-title="([^"]*)"',
            satir
        )

        if (
            eslesme
            and eslesme.group(1) == GRUP
        ):

            return True

    return False


# ==================================================
# M3U DOSYASINI GÜVENLİ GÜNCELLE
# ==================================================# ==================================================
# M3U DOSYASINI GÜVENLİ GÜNCELLE
# ==================================================

def m3u_guvenli_guncelle(yeni_kanal):

    dosya = "mirti68.m3u"
    gecici = dosya + ".tmp"

    if not os.path.exists(dosya):
        print("❌ M3U dosyası bulunamadı.")
        return False

    if not yeni_kanal or "#EXTINF" not in yeni_kanal:
        print("❌ Yeni kanal bilgisi geçersiz.")
        return False

    try:
        with open(dosya, "r", encoding="utf-8-sig") as f:
            satirlar = f.read().splitlines()

        bloklar = []
        baslik = []
        mevcut = []

        for satir in satirlar:
            if satir.startswith("#EXTINF"):
                if mevcut:
                    bloklar.append(mevcut)
                mevcut = [satir]

            elif mevcut:
                mevcut.append(satir)

            else:
                baslik.append(satir)

        if mevcut:
            bloklar.append(mevcut)

        # Eski ATV kaydını çıkar, diğer kanalları koru.
        yeni_bloklar = []

        for blok in bloklar:
            metin = "\n".join(blok)

            if (
                'tvg-id="atv.tr"' in metin
                or "ATVᴴᴰ⭕" in metin
            ):
                continue

            yeni_bloklar.append(blok)

        # Hedef grubu bul.
        hedef = 'group-title="🟨◆  ULUSALᴴᴰ ⭕"'
        son_indeks = None

        for indeks, blok in enumerate(yeni_bloklar):
            if hedef in blok[0]:
                son_indeks = indeks

        if son_indeks is None:
            print("❌ Hedef grup bulunamadı. M3U korunuyor.")
            return False

        # Yeni ATV kanalını ekle.
        yeni_satirlar = yeni_kanal.strip().splitlines()

        if not yeni_satirlar[0].startswith("#EXTINF"):
            print("❌ EXTINF satırı hatalı.")
            return False

        yeni_bloklar.insert(son_indeks + 1, yeni_satirlar)

        # Geçici dosyaya yaz.
        with open(gecici, "w", encoding="utf-8", newline="\n") as f:
            for satir in baslik:
                f.write(satir + "\n")

            for blok in yeni_bloklar:
                for satir in blok:
                    f.write(satir + "\n")

        # Geçici dosyayı kontrol et.
        with open(gecici, "r", encoding="utf-8") as f:
            kontrol = f.read()

        if kontrol.count('tvg-id="atv.tr"') != 1:
            raise ValueError("ATV kayıt kontrolü başarısız.")

        if "#EXTM3U" not in kontrol:
            raise ValueError("M3U başlığı eksik.")

        # Güvenli şekilde asıl dosyanın yerine koy.
        os.replace(gecici, dosya)

        print("✅ ATV kanalı güvenli şekilde güncellendi.")
        return True

    except Exception as hata:
        if os.path.exists(gecici):
            os.remove(gecici)

        print("❌ M3U güncellenemedi:", hata)
        print("Orijinal M3U dosyası korundu.")
        return False
