
import os
import re
import json
import shutil
import time
import html

from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ==================================================
# HANIM KORE DIZILERI
# ==================================================

BASE_URL = "https://asyawatch.com"
LIST_URL = BASE_URL + "/dizi/ulke/guney-kore"

M3U_FILE = "mirti68.m3u"
BACKUP_FILE = "mirti68_yedek.m3u"

GROUP = "🩷◆ HANIM KORE DİZİLERİ ⭕"

MAX_PAGES = 40
WAIT_SECONDS = 5

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)


# ==================================================
# YARDIMCI FONKSIYONLAR
# ==================================================

def temizle(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        html.unescape(str(text))
    ).strip()


def mutlak_url(url, base):
    if not url:
        return ""

    return urljoin(base, url.strip())


def guvenli(text):
    return (
        temizle(text)
        .replace('"', "'")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def dizi_linki(url):
    p = urlparse(url)

    return (
        p.netloc == urlparse(BASE_URL).netloc
        and "/dizi/" in p.path
        and "/dizi/ulke/" not in p.path
    )


def poster_bul(img, base):

    if not img:
        return ""

    for attr in [
        "data-src",
        "data-lazy-src",
        "data-original",
        "data-image",
        "src"
    ]:

        value = img.get(attr)

        if value and not value.startswith("data:image"):
            return mutlak_url(value, base)

    return ""


# ==================================================
# SAYFA TARAMA
# ==================================================

def listeyi_tara(page):

    diziler = {}
    ziyaret_edilen = set()
    siradaki = [LIST_URL]

    print("\n[BAŞLANGIÇ] ASYAWATCH KORE TARAMASI")

    while siradaki and len(ziyaret_edilen) < MAX_PAGES:

        liste_url = siradaki.pop(0)

        if liste_url in ziyaret_edilen:
            continue

        ziyaret_edilen.add(liste_url)

        print("\n[SAYFA]", liste_url)

        try:

            response = page.goto(
                liste_url,
                wait_until="domcontentloaded",
                timeout=90000
            )

            status = response.status if response else 0

            print("[HTTP DURUMU]", status)

            if status in (403, 429):
                print("[ENGEL] Site erişimi reddetti.")
                continue

            page.wait_for_timeout(WAIT_SECONDS * 1000)

            # JavaScript yüklenmesini bekle
            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=12000
                )
            except Exception:
                pass

            # Sayfayı aşağı kaydır
            for _ in range(4):

                page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )

                page.wait_for_timeout(1000)

            soup = BeautifulSoup(
                page.content(),
                "html.parser"
            )

            print("[HTML UZUNLUK]", len(str(soup)))

            if soup.title:
                print(
                    "[SAYFA BAŞLIĞI]",
                    temizle(soup.title.get_text())
                )

            # Dizi kartları
            for a in soup.select("a[href]"):

                href = mutlak_url(
                    a.get("href"),
                    liste_url
                )

                if not dizi_linki(href):
                    continue

                if href in diziler:
                    continue

                kart = a

                for _ in range(6):

                    if kart.parent:
                        kart = kart.parent

                    if kart.find("img"):
                        break

                img = kart.find("img")

                isim = (
                    a.get("title")
                    or a.get_text(" ", strip=True)
                )

                if not isim and img:
                    isim = img.get("alt", "")

                if not isim:
                    continue

                poster = poster_bul(img, liste_url)

                diziler[href] = {
                    "isim": temizle(isim),
                    "url": href,
                    "poster": poster,
                    "aciklama": "",
                    "yil": "",
                    "tur": ""
                }

                print("[DİZİ BULUNDU]", temizle(isim))

            # Sayfalama
            for a in soup.select("a[href]"):

                href = mutlak_url(
                    a.get("href"),
                    liste_url
                )

                yazi = temizle(
                    a.get_text(" ", strip=True)
                ).lower()

                rel = a.get("rel", [])

                if isinstance(rel, str):
                    rel = [rel]

                if (
                    "next" in rel
                    or yazi in [
                        "sonraki",
                        "next",
                        "›",
                        "»",
                        "→"
                    ]
                ):

                    if (
                        href not in ziyaret_edilen
                        and href not in siradaki
                    ):
                        siradaki.append(href)

            # Sayfa numaraları
            for a in soup.select("a[href]"):

                href = mutlak_url(
                    a.get("href"),
                    liste_url
                )

                parsed = urlparse(href)

                if (
                    parsed.path == urlparse(LIST_URL).path
                    and href != liste_url
                    and href not in ziyaret_edilen
                    and href not in siradaki
                ):
                    siradaki.append(href)

            print("[BU SAYFADA TOPLAM]", len(diziler))

        except Exception as e:

            print("[SAYFA HATASI]", repr(e))

    # Hiçbir şey bulunamazsa teşhis bilgisi
    if not diziler:

        print("\n[DEBUG] Dizi bulunamadı.")

        try:

            page.goto(
                LIST_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(5000)

            soup = BeautifulSoup(
                page.content(),
                "html.parser"
            )

            print("[DEBUG] Sayfa metni:")
            print(
                soup.get_text(" ", strip=True)[:3000]
            )

            print("[DEBUG] İlk bağlantılar:")

            for a in soup.select("a[href]")[:30]:

                print(
                    a.get("href"),
                    temizle(a.get_text(" ", strip=True))[:100]
                )

        except Exception as e:
            print("[DEBUG HATASI]", e)

    return diziler


# ==================================================
# DIZI DETAYLARI
# ==================================================

def meta_bul(soup, *names):

    for name in names:

        tag = soup.find(
            "meta",
            attrs={"property": name}
        )

        if not tag:

            tag = soup.find(
                "meta",
                attrs={"name": name}
            )

        if tag and tag.get("content"):
            return temizle(tag["content"])

    return ""


def detaylari_al(page, dizi):

    try:

        print("[DETAY]", dizi["isim"])

        response = page.goto(
            dizi["url"],
            wait_until="domcontentloaded",
            timeout=60000
        )

        if response and response.status in (403, 429):
            print("[DETAY ENGELİ]", dizi["isim"])
            return dizi

        page.wait_for_timeout(1500)

        soup = BeautifulSoup(
            page.content(),
            "html.parser"
        )

        baslik = meta_bul(
            soup,
            "og:title",
            "twitter:title"
        )

        if baslik:
            dizi["isim"] = baslik

        aciklama = meta_bul(
            soup,
            "og:description",
            "description",
            "twitter:description"
        )

        if aciklama:
            dizi["aciklama"] = aciklama

        poster = meta_bul(
            soup,
            "og:image",
            "twitter:image"
        )

        if poster:
            dizi["poster"] = mutlak_url(
                poster,
                dizi["url"]
            )

        # JSON-LD
        for script in soup.select(
            'script[type="application/ld+json"]'
        ):

            try:

                data = json.loads(
                    script.string or script.get_text()
                )

                items = data if isinstance(data, list) else [data]

                for item in items:

                    if not isinstance(item, dict):
                        continue

                    tarih = item.get("datePublished", "")

                    if tarih:
                        dizi["yil"] = str(tarih)[:4]

                    tur = item.get("genre", "")

                    if isinstance(tur, list):
                        tur = ", ".join(tur)

                    if tur:
                        dizi["tur"] = temizle(tur)

            except Exception:
                pass

        # Alternatif açıklama alanları
        if not dizi["aciklama"]:

            for selector in [
                ".description",
                ".content-description",
                ".detail-content",
                ".summary",
                ".story",
                ".entry-content"
            ]:

                el = soup.select_one(selector)

                if el:

                    dizi["aciklama"] = temizle(
                        el.get_text(" ", strip=True)
                    )

                    break

        print(
            "[TAMAM]",
            dizi["isim"],
            "| POSTER:",
            bool(dizi["poster"]),
            "| AÇIKLAMA:",
            bool(dizi["aciklama"])
        )

    except Exception as e:

        print("[DETAY HATASI]", repr(e))

    return dizi


# ==================================================
# M3U OLUŞTUR
# ==================================================

def m3u_olustur(diziler):

    satirlar = []

    for d in diziler:

        isim = guvenli(d["isim"])

        poster = guvenli(d["poster"])

        aciklama = guvenli(d["aciklama"])

        bilgiler = []

        if d["yil"]:
            bilgiler.append("Yıl: " + d["yil"])

        if d["tur"]:
            bilgiler.append("Tür: " + d["tur"])

        if bilgiler:

            aciklama = (
                " | ".join(bilgiler)
                + " | "
                + aciklama
            )

        aciklama = guvenli(aciklama)

        satirlar.append(
            f'#EXTINF:-1 tvg-name="{isim}" '
            f'tvg-logo="{poster}" '
            f'tvg-country="KR" '
            f'tvg-description="{aciklama}" '
            f'group-title="{GROUP}",{isim}'
        )

        # Dizi bilgi sayfası.
        # Gerçek video adresi bulunmadığında sahte akış eklenmez.
        satirlar.append(d["url"])

    return satirlar


# ==================================================
# MEVCUT M3U KORUMA
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

    # Önce yedek
    shutil.copy2(
        M3U_FILE,
        BACKUP_FILE
    )

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

    # Mevcut dosya korunur, yeni grup eklenir
    with open(
        M3U_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.writelines(temiz_eski)

        if temiz_eski and not temiz_eski[-1].endswith("\n"):
            f.write("\n")

        f.write("\n")

        f.write(
            "\n".join(yeni_satirlar)
        )

        f.write("\n")

    print("[YEDEK]", BACKUP_FILE)
    print("[OK] M3U GÜNCELLENDİ")


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 55)
    print("HANIM KORE DİZİLERİ")
    print("=" * 55)

    if not os.path.exists(M3U_FILE):

        print("[HATA] M3U dosyası bulunamadı.")
        return

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={
                "width": 1366,
                "height": 900
            },
            locale="tr-TR"
        )

        page = context.new_page()

        diziler = listeyi_tara(page)

        print("\n[BULUNAN DİZİ]", len(diziler))

        if not diziler:

            print(
                "[UYARI] Dizi bulunamadı. "
                "Mevcut M3U DEĞİŞTİRİLMEDİ."
            )

            browser.close()
            return

        tamamlanan = []

        for i, dizi in enumerate(
            diziler.values(),
            start=1
        ):

            print(
                f"\n[DETAY {i}/{len(diziler)}]"
            )

            detay = detaylari_al(
                page,
                dizi
            )

            tamamlanan.append(detay)

            time.sleep(0.5)

        browser.close()

    yeni_satirlar = m3u_olustur(
        tamamlanan
    )

    if yeni_satirlar:

        listeye_ekle(
            yeni_satirlar
        )

    print("\n" + "=" * 55)
    print("TARAMA TAMAMLANDI")
    print("DİZİ:", len(tamamlanan))
    print("GRUP:", GROUP)
    print("DOSYA:", M3U_FILE)
    print("=" * 55)


if __name__ == "__main__":
    main()
