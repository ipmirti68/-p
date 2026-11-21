
import json
import urllib.request
import re
import os
import sys

# ==================================================
# MIRTI68 - DİZİ + TÜRKİYE KANALLARI AKTARICI
# ==================================================

EK_KOD = "⭕"

HEDEF_M3U = "mirtitv.m3u"

KANAL_JSON = (
    "https://raw.githubusercontent.com/umitm0d/"
    "Liveinlive/refs/heads/main/channels_turkey.json"
)

FILTRELER = {
    "atv.m3u": {
        "aranacak": ["Altı Üstü İstanbul", "Güneşin Doğduğu Yer"],
        "hedef_grup": "🟪◆ ATV DİZİLER 📺⭕",
    },

    "kanalddizi.m3u": {
        "aranacak": ["Haysiyet", "Uzak Şehir",
                     "Güller ve Günahlar", "Daha 17"],
        "hedef_grup": "🟪◆ KANAL D DİZİLER 📺⭕",
    },

    "stardizi.m3u": {
        "aranacak": ["Başkalarının Hayatı",
                     "Tuzlu Kahve", "Sevdiğim Sensin"],
        "hedef_grup": "🟪◆ STAR DİZİLER 📺⭕",
    },
}

SOURCES = [
    (
        "https://raw.githubusercontent.com/KiNGTV2025/Kingof/"
        "refs/heads/main/atv_state.json",
        "atv.m3u"
    ),
    (
        "https://raw.githubusercontent.com/KiNGTV2025/Kingof/"
        "refs/heads/main/kanald_state.json",
        "kanalddizi.m3u"
    ),
    (
        "https://raw.githubusercontent.com/KiNGTV2025/Kingof/"
        "refs/heads/main/startv_state.json",
        "stardizi.m3u"
    ),
]

KANAL_GRUP_ON_EK = "🇹🇷◆"

LOGO_KEYS = (
    "logo", "poster", "image", "img", "thumb",
    "thumbnail", "cover", "poster_url", "logo_url"
)

EP_KEYS = (
    "episodes", "bolumler", "bolum", "bölümler",
    "items", "videos", "list", "episode_list"
)

NAME_KEYS = ("name", "title", "baslik", "ad")

URL_KEYS = (
    "url", "link", "video_url", "stream", "src",
    "m3u8", "mp4"
)

KANAL_KATEGORILERI = [
    "Ulusal",
    "Haber",
    "Spor",
    "Belgesel",
    "Müzik",
    "Çocuk",
]

# ==================================================
# GENEL FONKSİYONLAR
# ==================================================

def temiz(s):
    return re.sub(
        r"\s+",
        " ",
        str(s or "").replace("\n", " ").replace("\r", " ")
    ).strip()


def ilk(d, keys):
    if not isinstance(d, dict):
        return ""

    for k in keys:
        v = d.get(k)
        if v:
            return v

    return ""


def indir_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 MIRTI68"}
    )

    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def bolum_no(name):
    m = re.search(r"(\d+)\s*\.\s*Bölüm", name or "", re.I)

    if m:
        return int(m.group(1))

    m = re.search(r"Bölüm\s*(\d+)", name or "", re.I)

    if m:
        return int(m.group(1))

    if "İlk" in (name or ""):
        return 1

    return 9999


def bolum_listesi_bul(dizi):
    for k in EP_KEYS:
        v = dizi.get(k)

        if isinstance(v, list) and v:
            return v

    for v in dizi.values():
        if isinstance(v, list) and v:
            if isinstance(v[0], (dict, str)):
                return v

    return []


# ==================================================
# DİZİ JSON AKTARIMI
# ==================================================

def cevir(url, out):

    filtre = FILTRELER[out]

    aranacak = filtre["aranacak"]
    hedef_grup = filtre["hedef_grup"]

    print("\nDizi kaynağı:", out)

    try:
        data = indir_json(url)

        if isinstance(data, list):
            data = {
                temiz(ilk(x, NAME_KEYS) or f"dizi-{i}"): x
                for i, x in enumerate(data)
                if isinstance(x, dict)
            }

        if not isinstance(data, dict):
            raise ValueError("JSON nesne veya liste değil")

        lines = []
        say = 0

        for key, dizi in data.items():

            if not isinstance(dizi, dict):
                continue

            dizi_adi = temiz(
                ilk(dizi, NAME_KEYS) or key
            )

            if dizi_adi not in aranacak:
                continue

            logo = temiz(ilk(dizi, LOGO_KEYS))

            eps = bolum_listesi_bul(dizi)

            def siralama(e):

                if isinstance(e, dict) and "order" in e:
                    try:
                        return int(e["order"])
                    except (ValueError, TypeError):
                        pass

                if isinstance(e, dict):
                    return bolum_no(
                        temiz(ilk(e, NAME_KEYS))
                    )

                return 9999

            eps = sorted(eps, key=siralama)

            gorulen = set()

            for ep in eps:

                if isinstance(ep, str):
                    url_ep = temiz(ep)
                    ep_adi = ""

                elif isinstance(ep, dict):
                    url_ep = temiz(ilk(ep, URL_KEYS))
                    ep_adi = temiz(ilk(ep, NAME_KEYS))

                else:
                    continue

                if not url_ep or url_ep in gorulen:
                    continue

                gorulen.add(url_ep)

                ep_adi = temiz(
                    ep_adi.replace("Izle.", "")
                    .replace("izle", "")
                    .replace("/", ". ")
                )

                if not ep_adi:
                    title = dizi_adi

                elif ep_adi.startswith(dizi_adi):
                    title = ep_adi

                else:
                    title = f"{dizi_adi} - {ep_adi}"

                if EK_KOD and not title.endswith(EK_KOD):
                    title = f"{title} {EK_KOD}"

                lines.append(
                    f'#EXTINF:-1 tvg-logo="{logo}" '
                    f'group-title="{hedef_grup}",{title}'
                )

                lines.append(url_ep)

                say += 1

        with open(out, "w", encoding="utf-8") as f:
            f.write(
                '#EXTM3U x-tvg-url=""\n'
                + "\n".join(lines)
                + "\n"
            )

        print(f"{out}: {say} bölüm")

        return lines

    except Exception as e:
        print(f"DİZİ HATASI {out}: {e}")
        return []


# ==================================================
# TÜRKİYE CANLI KANALLARI
# ==================================================

def turkiye_kanallarini_aktar():

    print("\nTürkiye kanal JSON indiriliyor...")

    try:
        data = indir_json(KANAL_JSON)

        if isinstance(data, dict):
            kanallar = data.get("channels", [])
        elif isinstance(data, list):
            kanallar = data
        else:
            raise ValueError("Beklenmeyen JSON yapısı")

        if not isinstance(kanallar, list):
            raise ValueError("channels alanı liste değil")

        lines = []
        say = 0
        gorulen = set()

        for kanal in kanallar:

            if not isinstance(kanal, dict):
                continue

            ulke = temiz(
                kanal.get("country", "")
            ).lower()

            if ulke not in ("turkey", "tr", "türkiye"):
                continue

            isim = temiz(kanal.get("name"))
            url = temiz(kanal.get("url"))
            logo = temiz(kanal.get("logo"))
            epg = temiz(kanal.get("epg_id"))

            kategori = temiz(
                kanal.get("category")
                or kanal.get("group")
                or "Diğer"
            )

            if not isim or not url:
                continue

            if url in gorulen:
                continue

            gorulen.add(url)

            grup = f"{KANAL_GRUP_ON_EK} {kategori.upper()} ⭕"

            extinf = (
                f'#EXTINF:-1 '
                f'tvg-id="{epg}" '
                f'tvg-name="{isim}" '
                f'tvg-logo="{logo}" '
                f'group-title="{grup}",{isim}'
            )

            lines.append(extinf)
            lines.append(url)

            say += 1

        print(f"Türkiye kanalları: {say}")

        return lines

    except Exception as e:
        print("TÜRKİYE KANAL HATASI:", e)
        return []


# ==================================================
# ANA M3U GÜNCELLEME
# ==================================================

def mirti68e_ekle(tum_satirlar):

    if not os.path.exists(HEDEF_M3U):
        print(f"HATA: {HEDEF_M3U} bulunamadı.")
        return

    hedef_gruplar = {
        v["hedef_grup"]
        for v in FILTRELER.values()
    }

    # Türkiye kanallarının grupları
    hedef_gruplar.update(
        f"{KANAL_GRUP_ON_EK} {k.upper()} ⭕"
        for k in KANAL_KATEGORILERI
    )

    # Diğer kategorilerdeki eski Türkiye kayıtları
    # aynı kaynak tarafından yenilenebilmesi için tanınır.
    try:
        with open(HEDEF_M3U, encoding="utf-8",
                  errors="ignore") as f:
            ham = f.read().splitlines()
    except Exception as e:
        print("Ana liste okunamadı:", e)
        return

    header = (
        ham[0]
        if ham and ham[0].startswith("#EXTM3U")
        else "#EXTM3U"
    )

    geri = (
        ham[1:]
        if ham and ham[0].startswith("#EXTM3U")
        else ham
    )

    bloklar = []
    cur = []

    for satir in geri:

        if satir.startswith("#EXTINF"):

            if cur:
                bloklar.append(cur)

            cur = [satir]

        elif cur:
            cur.append(satir)

        elif satir.strip():
            bloklar.append([satir])

    if cur:
        bloklar.append(cur)

    tutulan = []
    atilan = 0

    for blok in bloklar:

        ilk_satir = blok[0] if blok else ""

        silinecek = False

        if ilk_satir.startswith("#EXTINF"):

            for grup in hedef_gruplar:

                if f'group-title="{grup}"' in ilk_satir:
                    silinecek = True
                    break

        if silinecek:
            atilan += 1
            continue

        tutulan.append(blok)

    yeni = [header]

    for blok in tutulan:
        yeni.extend(blok)

    yeni.extend(tum_satirlar)

    gecici = HEDEF_M3U + ".tmp"

    try:
        with open(gecici, "w", encoding="utf-8") as f:
            f.write("\n".join(yeni) + "\n")

        os.replace(gecici, HEDEF_M3U)

        print("\n================================")
        print("MIRTI68 GÜNCELLEME TAMAMLANDI")
        print("================================")
        print("Eski kayıt silindi:", atilan)
        print("Yeni bölüm/kanal:", len(tum_satirlar) // 2)
        print("Ana liste:", HEDEF_M3U)
        print("Diğer gruplar korundu.")

    except Exception as e:
        print("M3U YAZMA HATASI:", e)

        if os.path.exists(gecici):
            os.remove(gecici)


# ==================================================
# PROGRAM BAŞLANGICI
# ==================================================

def main():

    print("================================")
    print("MIRTI68 OTOMATİK AKTARICI")
    print("================================")

    tum = []

    # ATV + KANAL D + STAR
    for url, dosya in SOURCES:
        tum.extend(cevir(url, dosya))

    # TÜRKİYE CANLI KANALLARI
    turkiye = turkiye_kanallarini_aktar()
    tum.extend(turkiye)

    # ANA M3U DOSYASINA EKLE
    if tum:
        mirti68e_ekle(tum)
    else:
        print("Yeni kayıt bulunamadı. Ana liste korunuyor.")


if __name__ == "__main__":
    main()
