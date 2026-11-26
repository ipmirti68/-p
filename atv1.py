
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import subprocess
import requests
import urllib3

from urllib.parse import urljoin, urlsplit

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
TARAMA_SURESI = 30000

session = requests.Session()
session.headers.update({
    "User-Agent": UA,
    "Referer": REFERER,
    "Origin": ORIGIN,
    "Accept": "*/*"
})


def yaz(mesaj):
    print(mesaj, flush=True)


def guvenli_url(url):
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}{p.path}"


def atv_hls_mi(url):
    try:
        p = urlsplit(url)
        return (
            p.scheme in ("http", "https")
            and "trkvz.daioncdn.net" in p.netloc.lower()
            and "/atv/" in p.path.lower()
            and p.path.lower().endswith(".m3u8")
        )
    except Exception:
        return False


def playwright_tara():
    yaz("\n[1] PLAYWRIGHT ATV TARAMASI")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        yaz("[HATA] Playwright kurulu değil.")
        return []

    bulunan = []
    basliklar = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context = browser.new_context(
                user_agent=UA,
                ignore_https_errors=True
            )

            page = context.new_page()

            def yakala(request):
                url = request.url

                if atv_hls_mi(url) and url not in bulunan:
                    bulunan.append(url)
                    basliklar[url] = request.headers

                    yaz(
                        f"[M3U8 {len(bulunan)}] "
                        f"{guvenli_url(url)}"
                    )

            page.on("request", yakala)

            try:
                page.goto(
                    SAYFA_URL,
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                yaz("[OK] ATV sayfası açıldı.")
            except Exception as hata:
                yaz(f"[UYARI] Sayfa: {str(hata)[:200]}")

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

            yaz("[TARAMA] Yeni yayın adresleri bekleniyor...")
            page.wait_for_timeout(TARAMA_SURESI)

            try:
                for cookie in context.cookies():
                    session.cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie.get("domain"),
                        path=cookie.get("path", "/")
                    )
            except Exception:
                pass

            browser.close()

        if bulunan:
            for isim in (
                "user-agent", "referer",
                "origin", "accept", "accept-language"
            ):
                deger = basliklar.get(bulunan[-1], {}).get(isim)
                if deger:
                    session.headers[isim] = deger

        yaz(f"[TARAMA TAMAMLANDI] {len(bulunan)} adres bulundu.")
        return bulunan

    except Exception as hata:
        yaz(f"[PLAYWRIGHT HATASI] {str(hata)[:500]}")
        return bulunan


def streamlink_tara():
    yaz("\n[2] STREAMLINK YEDEK TARAMASI")

    yol = shutil.which("streamlink")
    if not yol:
        yaz("[UYARI] Streamlink bulunamadı.")
        return []

    komut = [
        yol, "--loglevel", "error",
        "--http-header", f"Referer={REFERER}",
        "--http-header", f"Origin={ORIGIN}",
        "--http-header", f"User-Agent={UA}",
        "--stream-url", SAYFA_URL, "best"
    ]

    try:
        sonuc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            timeout=60
        )

        for satir in sonuc.stdout.splitlines():
            satir = satir.strip()
            if atv_hls_mi(satir):
                yaz("[STREAMLINK] Adres bulundu.")
                return [satir]

        yaz("[STREAMLINK] Adres bulunamadı.")

    except Exception as hata:
        yaz(f"[STREAMLINK HATASI] {str(hata)[:300]}")

    return []


def hls_oku(url):
    try:
        r = session.get(
            url,
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )

        yaz(f"[HLS HTTP] {r.status_code}")

        if r.status_code != 200:
            return None, None

        icerik = r.text.lstrip("\ufeff \r\n\t")

        if not icerik.startswith("#EXTM3U"):
            return None, None

        return icerik, r.url

    except requests.RequestException as hata:
        yaz(f"[HLS HATA] {str(hata)[:200]}")
        return None, None


def uri_bul(satir):
    m = re.search(r'URI="([^"]+)"', satir)
    return m.group(1) if m else None


def parca_test(url):
    try:
        r = session.get(
            url,
            timeout=TIMEOUT,
            verify=False,
            stream=True
        )

        if r.status_code not in (200, 206):
            r.close()
            return False

        veri = r.raw.read(16384)
        r.close()

        if len(veri) < 100:
            return False

        ilk = veri[:500].lower()

        if any(x in ilk for x in (
            b"<html", b"<!doctype", b"access denied", b"forbidden"
        )):
            return False

        return True

    except requests.RequestException:
        return False


def hls_test(url):
    yaz("\n[TEST] " + guvenli_url(url))

    icerik, son_url = hls_oku(url)

    if not icerik:
        yaz("[HATA] Ana playlist okunamadı.")
        return False

    varyantlar = []

    satirlar = [
        x.strip() for x in icerik.splitlines() if x.strip()
    ]

    for i, satir in enumerate(satirlar):
        if satir.startswith("#EXT-X-STREAM-INF:"):
            m = re.search(r"BANDWIDTH=(\d+)", satir)
            hiz = int(m.group(1)) if m else 0

            if i + 1 < len(satirlar):
                alt = satirlar[i + 1]
                if not alt.startswith("#"):
                    varyantlar.append(
                        (hiz, urljoin(son_url, alt))
                    )

    if varyantlar:
        varyantlar.sort(reverse=True)
        medya = None
        medya_url = None

        for _, alt_url in varyantlar:
            medya, medya_url = hls_oku(alt_url)
            if medya:
                break

        if not medya:
            yaz("[HATA] Alt playlist okunamadı.")
            return False
    else:
        medya = icerik
        medya_url = son_url

    satirlar = [
        x.strip() for x in medya.splitlines() if x.strip()
    ]

    for satir in satirlar:
        if satir.startswith("#EXT-X-KEY:"):
            if "METHOD=NONE" in satir:
                continue

            anahtar = uri_bul(satir)

            if anahtar:
                adres = urljoin(medya_url, anahtar)
                try:
                    r = session.get(
                        adres, timeout=TIMEOUT, verify=False
                    )
                    ok = r.status_code == 200 and len(r.content) >= 16
                    r.close()
                    if not ok:
                        yaz("[HATA] Şifreleme anahtarı alınamadı.")
                        return False
                except requests.RequestException:
                    return False

            elif "METHOD=AES-128" in satir:
                return False

    for satir in satirlar:
        if satir.startswith("#EXT-X-MAP:"):
            uri = uri_bul(satir)
            if uri and not parca_test(urljoin(medya_url, uri)):
                yaz("[HATA] INIT segment testi başarısız.")
                return False
            break

    parcalar = [
        x for x in satirlar
        if not x.startswith("#")
    ]

    if not parcalar:
        yaz("[HATA] Video parçası bulunamadı.")
        return False

    if not parca_test(urljoin(medya_url, parcalar[0])):
        yaz("[HATA] Video parçası indirilemedi.")
        return False

    yaz("[OK] HLS YAYINI ÇALIŞIYOR.")
    return True


def yayin_bul():
    adaylar = playwright_tara()

    for url in streamlink_tara():
        if url not in adaylar:
            adaylar.append(url)

    if not adaylar:
        yaz("[BAŞARISIZ] ATV adresi bulunamadı.")
        return None

    yaz(f"\n[TOPLAM ADAY] {len(adaylar)}")

    for no, url in enumerate(reversed(adaylar), 1):
        yaz(f"\n[ADAY TEST] {no}/{len(adaylar)}")

        if hls_test(url):
            yaz("[BAŞARILI] Çalışan ATV adresi seçildi.")
            return url

    yaz("[BAŞARISIZ] Çalışan ATV adresi bulunamadı.")
    return None


def atv_satirlari(url):
    return [
        (
            f'#EXTINF:-1 tvg-id="{TVG_ID}" '
            f'tvg-name="{KANAL}" tvg-logo="{LOGO}" '
            f'group-title="{GRUP}",{KANAL}'
        ),
        f"#EXTVLCOPT:http-referrer={REFERER}",
        f"#EXTVLCOPT:http-origin={ORIGIN}",
        f"#EXTVLCOPT:http-user-agent={UA}",
        url
    ]


def m3u_guncelle(url):
    yaz("\n[3] M3U GÜNCELLEME")

    if not os.path.isfile(DOSYA):
        yaz("[HATA] mirti68.m3u bulunamadı.")
        return False

    try:
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

        hedef_indeksler = []

        for i, blok in enumerate(bloklar):
            extinf = next(
                (x for x in blok if x.startswith("#EXTINF:")),
                ""
            )

            grup = re.search(r'group-title="([^"]*)"', extinf)

            if grup and grup.group(1) == GRUP:
                hedef_indeksler.append(i)

        if not hedef_indeksler:
            yaz("[HATA] ULUSAL grubu bulunamadı.")
            return False

        hedef = hedef_indeksler[-1]

        yeni_bloklar = []
        ekleme_indeksi = 0

        for i, blok in enumerate(bloklar):
            metin = "\n".join(blok)

            atv = (
                f'tvg-id="{TVG_ID}"' in metin
                or KANAL in metin
            )

            if i <= hedef and not atv:
                ekleme_indeksi += 1

            if not atv:
                yeni_bloklar.append(blok)

        yeni_bloklar.insert(
            ekleme_indeksi,
            atv_satirlari(url)
        )

        gecici = DOSYA + ".tmp"

        with open(gecici, "w", encoding="utf-8") as f:
            f.write("\n".join(baslik).rstrip() + "\n")

            for blok in yeni_bloklar:
                f.write("\n".join(blok).rstrip() + "\n")

        os.replace(gecici, DOSYA)

        yaz("[OK] ATV ULUSAL grubuna eklendi.")
        yaz("[OK] Diğer kanallar korundu.")
        yaz("[OK] M3U dosyası güncellendi.")

        return True

    except Exception as hata:
        yaz(f"[M3U HATASI] {str(hata)[:500]}")

        try:
            if os.path.exists(DOSYA + ".tmp"):
                os.remove(DOSYA + ".tmp")
        except OSError:
            pass

        return False


def main():
    yaz("================================")
    yaz("MIRTI68 ATV YAYIN SİSTEMİ")
    yaz("================================")

    adres = yayin_bul()

    if not adres:
        yaz("[SONUÇ] ATV güncellenmedi.")
        return 1

    yaz("[SEÇİLEN URL] " + guvenli_url(adres))

    if not m3u_guncelle(adres):
        yaz("[SONUÇ] M3U korunuyor.")
        return 1

    yaz("================================")
    yaz("MIRTI68 ATV İŞLEMİ BAŞARILI")
    yaz("================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
        
