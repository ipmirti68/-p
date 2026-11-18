
import os
import re
import json
import shutil
import time
import html
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ==================================================
# AYARLAR
# ==================================================

BASE_URL = "https://asyawatch.com"
LIST_URL = BASE_URL + "/dizi/ulke/guney-kore"

M3U_FILE = "mirti68.m3u"
BACKUP_FILE = "mirti68_yedek.m3u"

GROUP = "🩷◆ HANIM KORE DİZİLERİ ⭕"

MAX_PAGES = 40
WAIT_SECONDS = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
}


# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def temizle(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(text))).strip()


def meta(soup, *names):
    for name in names:
        tag = soup.find("meta", attrs={"property": name})
        if not tag:
            tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return temizle(tag["content"])
    return ""


def mutlak_url(url, base):
    if not url:
        return ""
    return urljoin(base, url.strip())


def guvenli_m3u(text):
    return temizle(text).replace('"', "'").replace(",", " ")


def dizi_linki(url):
    p = urlparse(url)
    return (
        p.netloc == urlparse(BASE_URL).netloc
        and "/dizi/" in p.path
        and "/dizi/ulke/" not in p.path
    )


# ==================================================
# SAYFA TARAMA
# ==================================================

def listeyi_tara(page):
    diziler = {}
    ziyaret_edilen = set()
    siradaki = [LIST_URL]

    while siradaki and len(ziyaret_edilen) < MAX_PAGES:

        liste_url = siradaki.pop(0)

        if liste_url in ziyaret_edilen:
            continue

        ziyaret_edilen.add(liste_url)

        print("\n[SAYFA]", liste_url)

        try:
            page.goto(
                liste_url,
                wait_until="domcontentloaded",
                timeout=60000
            )
            page.wait_for_timeout(WAIT_SECONDS * 1000)

            soup = BeautifulSoup(page.content(), "html.parser")

        except Exception as e:
            print("[HATA] Sayfa açılamadı:", e)
            continue

        # Dizi bağlantıları
        for a in soup.select("a[href]"):

            href = mutlak_url(a.get("href"), liste_url)

            if not dizi_linki(href):
                continue

            if href in diziler:
                continue

            kart = a

            # Kartın üst elemanlarında başlık ve poster ara
            for _ in range(5):
                if kart.parent:
                    kart = kart.parent

                if kart.find("img"):
                    break

            img = kart.find("img")

            poster = ""

            if img:
                poster = (
                    img.get("data-src")
                    or img.get("data-lazy-src")
                    or img.get("src")
                    or ""
                )

            isim = (
                a.get("title")
                or a.get_text(" ", strip=True)
                or (img.get("alt", "") if img else "")
            )

            isim = temizle(isim)

            if not isim and img:
                isim = temizle(img.get("alt", ""))

            if not isim:
                continue

            diziler[href] = {
                "isim": isim,
                "url": href,
                "poster": mutlak_url(poster, liste_url),
                "aciklama": "",
                "yil": "",
                "tur": ""
            }

            print("[DİZİ]", isim)

        # Sonraki sayfa bağlantıları
        for a in soup.select("a[href]"):

            href = mutlak_url(a.get("href"), liste_url)
            yazi = temizle(a.get_text(" ", strip=True)).lower()
            rel = a.get("rel", [])

            if isinstance(rel, str):
                rel = [rel]

            if (
                "next" in rel
                or yazi in ("sonraki", "next", "›", "»", "→")
            ):
                if href not in ziyaret_edilen:
                    siradaki.append(href)

        # Sayfalama numaraları
        for a in soup.select("a[href]"):
            href = mutlak_url(a.get("href"), liste_url)
            parsed = urlparse(href)

            if (
                parsed.path == urlparse(LIST_URL).path
                and href not in ziyaret_edilen
                and href not in siradaki
            ):
                siradaki.append(href)

    return diziler


# ==================================================
# DİZİ DETAYLARI
# ==================================================

def detaylari_al(page, dizi):

    try:
        page.goto(
            dizi["url"],
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(1000)

        soup = BeautifulSoup(page.content(), "html.parser")

        # Başlık
        dizi["isim"] = (
            meta(soup, "og:title")
            or (soup.title.get_text() if soup.title else "")
            or dizi["isim"]
        )

        # Açıklama
        dizi["aciklama"] = (
            meta(
                soup,
                "og:description",
                "description",
                "twitter:description"
            )
        )

        # Poster
        poster = meta(
            soup,
            "og:image",
            "twitter:image"
        )

        if poster:
            dizi["poster"] = mutlak_url(
                poster,
                dizi["url"]
            )

        # JSON-LD bilgileri
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())

                if isinstance(data, list):
                    items = data
                else:
                    items = [data]

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    dizi["yil"] = (
                        str(item.get("datePublished", ""))[:4]
                        or dizi["yil"]
                    )

                    genre = item.get("genre", "")

                    if isinstance(genre, list):
                        genre = ", ".join(genre)

                    dizi["tur"] = temizle(genre) or dizi["tur"]

            except Exception:
                pass

        # Açıklama boşsa sayfadaki metinden yararlan
        if not dizi["aciklama"]:
            for selector in [
                ".description",
                ".content-description",
                ".detail-content",
                ".summary",
                ".story"
            ]:
                el = soup.select_one(selector)

                if el:
                    dizi["aciklama"] = temizle(
                        el.get_text(" ", strip=True)
                    )
                    break

        dizi["isim"] = temizle(dizi["isim"])

        print(
            "[BİLGİ]",
            dizi["isim"],
            "| Poster:",
            bool(dizi["poster"]),
            "| Açıklama:",
            bool(dizi["aciklama"])
        )

    except Exception as e:
        print("[DETAY HATASI]", dizi["isim"], e)

    return dizi


# ==================================================
# M3U GRUBUNU OLUŞTUR
# ==================================================

def m3u_olustur(diziler):

    cikti = []

    for d in diziler:

        isim = guvenli_m3u(d["isim"])
        poster = d["poster"]

        aciklama = guvenli_m3u(d["aciklama"])

        ek_bilgi = []

        if d["yil"]:
            ek_bilgi.append("Yıl: " + d["yil"])

        if d["tur"]:
            ek_bilgi.append("Tür: " + d["tur"])

        if ek_bilgi:
            aciklama = " | ".join(ek_bilgi) + " | " + aciklama

        aciklama = guvenli_m3u(aciklama)

        cikti.append(
            f'#EXTINF:-1 tvg-name="{isim}" '
            f'tvg-logo="{poster}" '
            f'tvg-country="KR" '
            f'tvg-description="{aciklama}" '
            f'group-title="{GROUP}",{isim}'
        )

        # Bu adres dizi bilgi sayfasıdır.
        # Korunan video akışları çıkarılmaz.
        cikti.append(d["url"])

    return cikti


# ==================================================
# MEVCUT M3U'YU KORU
# ==================================================

def listeye_ekle(yeni_satirlar):

    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
        return

    with open(
        M3U_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:
        eski = f.readlines()

    # Önce yedek al
    shutil.copy2(M3U_FILE, BACKUP_FILE)

    # Yalnızca bu gruba ait eski kayıtları çıkar
    temiz_eski = []
    atla = False

    for line in eski:

        satir = line.strip()

        if satir.startswith("#EXTINF:"):

            if f'group-title="{GROUP}"' in satir:
                atla = True
                continue

            atla = False

        elif atla:
            if not satir or satir.startswith("#"):
                continue

            atla = False
            continue

        temiz_eski.append(line)

    # Eski listeyi aynen koruyup yeni grubu sona ekle
    with open(
        M3U_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.writelines(temiz_eski)

        if temiz_eski and not temiz_eski[-1].endswith("\n"):
            f.write("\n")

        f.write("\n")
        f.write("\n".join(yeni_satirlar))
        f.write("\n")

    print("\n[YEDEK]", BACKUP_FILE)
    print("[OK] M3U güncellendi.")


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 50)
    print("HANIM KORE DİZİLERİ TARAMA")
    print("=" * 50)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1366, "height": 900}
        )

        page = context.new_page()

        diziler = listeyi_tara(page)

        print("\n[TOPLAM]", len(diziler), "dizi bulundu.")

        tamamlanan = []

        for i, dizi in enumerate(diziler.values(), 1):

            print(
                f"\n[DETAY {i}/{len(diziler)}]",
                dizi["isim"]
            )

            detay = detaylari_al(page, dizi)
            tamamlanan.append(detay)

            time.sleep(0.5)

        browser.close()

    if not tamamlanan:
        print("[UYARI] Dizi bulunamadı. Mevcut liste korunuyor.")
        return

    yeni_satirlar = m3u_olustur(tamamlanan)

    listeye_ekle(yeni_satirlar)

    print("\n" + "=" * 50)
    print("TARAMA TAMAMLANDI")
    print("Dizi sayısı:", len(tamamlanan))
    print("Grup:", GROUP)
    print("Dosya:", M3U_FILE)
    print("=" * 50)


if __name__ == "__main__":
    main()
