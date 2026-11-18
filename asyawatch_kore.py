
import os
import re
import time
import html
import shutil
import requests

from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =====================================================
# HANIM KORE DIZILERI - TVMAZE API
# =====================================================

API = "https://api.tvmaze.com"

M3U_FILE = "mirti.m3u"
BACKUP_FILE = "mirti_yedek.m3u"

GROUP = "🩷◆ HANIM KORE DİZİLERİ ⭕"

# TVmaze ücretsiz API sınırlarına uygun hız
BEKLEME = 0.55

# Güvenlik sınırı. 1000 sayfaya ulaşılması beklenmez.
MAX_PAGES = 1000


HEADERS = {
    "User-Agent": "HanimKoreCatalog/1.0"
}


session = requests.Session()
session.headers.update(HEADERS)

retry = Retry(
    total=4,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry)
)


# =====================================================
# YARDIMCI FONKSIYONLAR
# =====================================================

def temizle(metin):

    if not metin:
        return ""

    metin = html.unescape(str(metin))
    metin = re.sub(r"<[^>]+>", " ", metin)
    metin = re.sub(r"\s+", " ", metin)

    return metin.strip()


def m3u_guvenli(metin):

    metin = temizle(metin)

    return (
        metin
        .replace('"', "'")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def kore_dizisi(show):

    dil = (show.get("language") or "").lower()

    turler = show.get("genres") or []

    network = show.get("network") or {}
    webchannel = show.get("webChannel") or {}

    network_country = network.get("country") or {}
    web_country = webchannel.get("country") or {}

    ulke = (
        network_country.get("code")
        or web_country.get("code")
        or ""
    ).upper()

    # Korece ve drama türü şartı
    if "Drama" not in turler:
        return False

    # Dil bilgisi Korece veya yayın ülkesi Güney Kore
    return (
        dil == "korean"
        or ulke == "KR"
    )


def poster_al(show):

    image = show.get("image") or {}

    return (
        image.get("original")
        or image.get("medium")
        or ""
    )


def yil_al(show):

    premiered = show.get("premiered") or ""

    if len(premiered) >= 4:
        return premiered[:4]

    return ""


# =====================================================
# TVMAZE VERILERINI TARA
# =====================================================

def dizileri_cek():

    diziler = {}

    print("=" * 55)
    print("HANIM KORE DİZİLERİ - TVMAZE")
    print("=" * 55)

    sayfa = 0

    while sayfa < MAX_PAGES:

        url = f"{API}/shows?page={sayfa}"

        print(f"\n[SAYFA] {sayfa}")

        try:

            response = session.get(
                url,
                timeout=60
            )

            if response.status_code == 404:
                print("[BİLGİ] API son sayfasına ulaşıldı.")
                break

            response.raise_for_status()

            veriler = response.json()

            if not isinstance(veriler, list) or not veriler:
                print("[BİLGİ] Yeni kayıt bulunamadı.")
                break

            for show in veriler:

                if not isinstance(show, dict):
                    continue

                if not kore_dizisi(show):
                    continue

                show_id = show.get("id")

                if not show_id:
                    continue

                isim = temizle(show.get("name"))

                if not isim:
                    continue

                ozet = temizle(show.get("summary"))

                genres = show.get("genres") or []

                diziler[str(show_id)] = {
                    "id": show_id,
                    "isim": isim,
                    "poster": poster_al(show),
                    "aciklama": ozet,
                    "yil": yil_al(show),
                    "tur": ", ".join(genres),
                    "durum": show.get("status") or "",
                    "url": show.get("url") or ""
                }

                print("[KORE DİZİ]", isim)

            print(
                "[TOPLAM KORE DİZİSİ]",
                len(diziler)
            )

            sayfa += 1

            time.sleep(BEKLEME)

        except requests.RequestException as e:

            print("[API HATASI]", str(e))
            print("[UYARI] Tarama tamamlanamadı.")
            return None

        except Exception as e:

            print("[VERİ HATASI]", str(e))
            return None

    if sayfa >= MAX_PAGES:
        print("[UYARI] Güvenlik sayfa sınırına ulaşıldı.")
        return None

    return list(diziler.values())


# =====================================================
# M3U KAYITLARINI HAZIRLA
# =====================================================

def m3u_olustur(diziler):

    satirlar = []

    # Yeni ve eski diziler birlikte sıralanır
    diziler.sort(
        key=lambda x: (
            x["yil"],
            x["isim"].lower()
        ),
        reverse=True
    )

    for d in diziler:

        isim = m3u_guvenli(d["isim"])

        poster = m3u_guvenli(d["poster"])

        aciklama = m3u_guvenli(d["aciklama"])

        yil = d["yil"] or "Bilinmiyor"

        tur = m3u_guvenli(d["tur"])

        durum = m3u_guvenli(d["durum"])

        aciklama_parcalari = [
            "Ülke: Güney Kore",
            "Yıl: " + yil
        ]

        if tur:
            aciklama_parcalari.append("Tür: " + tur)

        if durum:
            aciklama_parcalari.append("Durum: " + durum)

        if aciklama:
            aciklama_parcalari.append(aciklama)

        aciklama_parcalari.append(
            "Bilgi kaynağı: TVmaze"
        )

        tam_aciklama = m3u_guvenli(
            " | ".join(aciklama_parcalari)
        )

        dizi_url = d["url"]

        if not dizi_url:
            continue

        satirlar.append(
            f'#EXTINF:-1 '
            f'tvg-name="{isim}" '
            f'tvg-logo="{poster}" '
            f'tvg-country="KR" '
            f'tvg-description="{tam_aciklama}" '
            f'group-title="{GROUP}",{isim}'
        )

        # Bu bağlantı dizi bilgi sayfasıdır, canlı yayın değildir.
        satirlar.append(dizi_url)

    return satirlar


# =====================================================
# ESKI KORE GRUBUNU GUVENLI TEMIZLE
# =====================================================

def eski_grubu_temizle(satirlar):

    sonuc = []

    kore_kaydi = False

    for line in satirlar:

        satir = line.strip()

        if satir.startswith("#EXTINF:"):

            kore_kaydi = (
                f'group-title="{GROUP}"' in satir
            )

            if kore_kaydi:
                continue

        if kore_kaydi:
            continue

        sonuc.append(line)

    return sonuc


# =====================================================
# MEVCUT M3U'YA EKLE
# =====================================================

def listeyi_guncelle(yeni_satirlar):

    if not os.path.isfile(M3U_FILE):

        print("[HATA] mirti68.m3u bulunamadı!")
        return False

    if not yeni_satirlar:

        print("[UYARI] Yeni kayıtlar boş. Eski liste korunuyor.")
        return False

    with open(
        M3U_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:

        eski_satirlar = f.readlines()

    # Yedek
    shutil.copy2(
        M3U_FILE,
        BACKUP_FILE
    )

    # Sadece kendi grubumuzu kaldır
    temiz_liste = eski_grubu_temizle(
        eski_satirlar
    )

    with open(
        M3U_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.writelines(temiz_liste)

        if temiz_liste and not temiz_liste[-1].endswith("\n"):
            f.write("\n")

        f.write("\n")

        f.write(
            "\n".join(yeni_satirlar)
        )

        f.write("\n")

    print("\n[YEDEK]", BACKUP_FILE)
    print("[OK] Kore dizileri grubu yenilendi.")

    return True


# =====================================================
# ANA PROGRAM
# =====================================================

def main():

    if not os.path.exists(M3U_FILE):

        print("[HATA] M3U dosyası bulunamadı.")
        return

    diziler = dizileri_cek()

    # API hatasında mevcut listeye dokunma
    if diziler is None:

        print("[HATA] Tarama başarısız. M3U korunuyor.")
        return

    if len(diziler) == 0:

        print("[UYARI] Kore dizisi bulunamadı.")
        print("[UYARI] Mevcut liste korunuyor.")
        return

    yeni_satirlar = m3u_olustur(diziler)

    if listeyi_guncelle(yeni_satirlar):

        print("\n" + "=" * 55)
        print("HANIM KORE DİZİLERİ GÜNCELLENDİ")
        print("DİZİ SAYISI:", len(diziler))
        print("GRUP:", GROUP)
        print("DOSYA:", M3U_FILE)
        print("YEDEK:", BACKUP_FILE)
        print("=" * 55)


if __name__ == "__main__":
    main()
