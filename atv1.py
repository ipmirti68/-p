
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==================================================
# MIRTI68 - ATV CANLI
# LOGO + GRUP ALTINA EKLE
# TEKRAR EKLEME + LINK YENILEME
# ==================================================

import requests
import re
import os
import html

OUTPUT_FILE = "mirti68.m3u"

GROUP = "🟨◆  ULUSALᴴᴰ ⭕"
AD = "ATVᴴᴰ⭕"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

TVG_ID = "atv.tr"

SITE_ID = "0fe2a405-8afa-4238-b429-e5f96aec3a5c"
LIVE_ID = "00000000-0000-0000-0000-000000000000"

ATV_PAGE = "https://www.atv.com.tr/canli-yayin"

REFERER = "https://www.atv.com.tr/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    ),
    "Referer": REFERER,
    "Origin": "https://www.atv.com.tr"
}

session = requests.Session()
session.headers.update(HEADERS)


# ==================================================
# ATV KIMLIKLERI
# ==================================================

def kimlikleri_al():

    global SITE_ID, LIVE_ID

    try:

        r = session.get(
            ATV_PAGE,
            timeout=25
        )

        r.raise_for_status()

        sayfa = html.unescape(r.text)

        video = re.search(
            r'data-videoid=["\']([^"\']+)',
            sayfa,
            re.I
        )

        website = re.search(
            r'data-websiteid=["\']([^"\']+)',
            sayfa,
            re.I
        )

        if video and website:

            LIVE_ID = video.group(1)
            SITE_ID = website.group(1)

            print("[OK] ATV kimlikleri bulundu")

            return True

        m = re.search(
            r'var\s+tmdPlayer\s*=\s*["\'](.*?)["\']',
            sayfa,
            re.S
        )

        if m:

            player = html.unescape(m.group(1))

            v = re.search(
                r'data-videoid=["\']([^"\']+)',
                player,
                re.I
            )

            w = re.search(
                r'data-websiteid=["\']([^"\']+)',
                player,
                re.I
            )

            if v and w:

                LIVE_ID = v.group(1)
                SITE_ID = w.group(1)

                print("[OK] ATV player kimlikleri bulundu")

                return True

        print("[BILGI] Mevcut kimlikler kullanilacak")

    except Exception as e:

        print("[UYARI] Kimlik alma:", e)

    return True


# ==================================================
# M3U8 BUL
# ==================================================

def find_m3u8(text):

    if not text:
        return ""

    m = re.search(
        r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*',
        str(text),
        re.I
    )

    return m.group(0).rstrip("\\") if m else ""


# ==================================================
# ATV CANLI YAYIN LINKI
# ==================================================

def atv_link_al():

    try:

        api = (
            "https://videojs.tmgrup.com.tr/getvideo/"
            + SITE_ID + "/" + LIVE_ID
        )

        r = session.get(
            api,
            timeout=25
        )

        r.raise_for_status()

        data = r.json()

        video = data.get("video") or {}

        if not isinstance(video, dict):
            video = {}

        ham = (
            video.get("VideoSmilUrl")
            or video.get("VideoUrl")
            or video.get("videoUrl")
            or video.get("Url")
            or video.get("url")
            or ""
        )

        # Alternatif JSON alanlari
        if not ham:

            for key in (
                "VideoSmilUrl",
                "VideoUrl",
                "videoUrl",
                "Url",
                "url"
            ):

                if data.get(key):

                    ham = str(data[key])
                    break

        if not ham:

            ham = find_m3u8(data)

        if not ham:

            print("[HATA] ATV kaynak adresi bulunamadi")
            print("[API]", str(data)[:500])

            return ""

        print("[OK] ATV kaynak adresi alindi")

        # Guvenli yayin tokeni
        token_api = (
            "https://securevideotoken.tmgrup.com.tr/webtv/secure"
        )

        r2 = session.get(
            token_api,
            params={"url": ham},
            headers={"Referer": REFERER},
            timeout=25
        )

        r2.raise_for_status()

        data2 = r2.json()

        link = (
            data2.get("Url")
            or data2.get("url")
            or data2.get("VideoUrl")
            or data2.get("VideoURL")
            or ""
        )

        link = str(link).strip()

        # Token cevabinda dogrudan M3U8 ara
        if not link:

            link = find_m3u8(data2)

        if not link.startswith("http"):

            print("[HATA] Gecersiz token adresi")
            print("[TOKEN]", str(data2)[:500])

            return ""

        if ".m3u8" not in link.lower():

            print("[HATA] Yayin adresi M3U8 degil")
            print("[LINK]", link[:300])

            return ""

        print("[OK] ATV M3U8 adresi alindi")

        return link

    except Exception as e:

        print("[HATA] ATV yayin alma:", str(e))

        return ""


# ==================================================
# M3U BILGILERI
# ==================================================

def grup_al(s):

    m = re.search(
        r'group-title="([^"]*)"',
        s
    )

    return m.group(1) if m else ""


def ad_al(s):

    if "," in s:

        return s.rsplit(",", 1)[-1].strip()

    return ""


# ==================================================
# ATV EXTINF SATIRI - LOGO DAHIL
# ==================================================

def kanal_satiri():

    return (
        '#EXTINF:-1 '
        'tvg-id="' + TVG_ID + '" '
        'tvg-name="' + AD + '" '
        'tvg-logo="' + LOGO + '" '
        'group-title="' + GROUP + '",'
        + AD
    )


# ==================================================
# YAYIN SATIRLARI
# ==================================================

def yayin_satirlari(link):

    return [
        kanal_satiri(),

        '#EXTVLCOPT:http-referer=' + REFERER,

        '#EXTVLCOPT:http-user-agent=' + HEADERS["User-Agent"],

        link
    ]


# ==================================================
# ANA ISLEM
# ==================================================

def main():

    if not os.path.exists(OUTPUT_FILE):

        print("[HATA] mirti68.m3u bulunamadi")

        return

    # 1 - Kimlikleri bul
    kimlikleri_al()

    # 2 - ATV yayinini al
    link = atv_link_al()

    if not link:

        print("[KORUMA] Dosyaya dokunulmadi")

        return

    # 3 - M3U dosyasini oku
    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:

        satirlar = f.read().splitlines()

    # 4 - ATV kaydini bul
    hedefler = []

    for idx, s in enumerate(satirlar):

        if not s.startswith("#EXTINF:"):
            continue

        # Ayni gruptaki ATV
        if (
            grup_al(s) == GROUP
            and ad_al(s) == AD
        ):

            hedefler.append(idx)

    # 5 - ATV zaten varsa guncelle
    if hedefler:

        hedef_idx = hedefler[0]

        print("[BULUNDU] ATV mevcut, guncelleniyor")

        yeni = []

        i = 0

        while i < len(satirlar):

            s = satirlar[i]

            if i == hedef_idx:

                yeni.extend(
                    yayin_satirlari(link)
                )

                i += 1

                # Eski yayin ve VLCOPT satirlarini temizle
                while i < len(satirlar):

                    eski = satirlar[i].strip()

                    if eski.startswith("#EXTINF:"):
                        break

                    if (
                        eski.startswith("http://")
                        or eski.startswith("https://")
                        or eski.startswith("#EXTVLCOPT:")
                    ):

                        i += 1
                        continue

                    yeni.append(satirlar[i])

                    i += 1

                continue

            # Ayni gruptaki olasi kopya ATV kayitlarini kaldir
            if i in hedefler[1:]:

                i += 1

                while i < len(satirlar):

                    eski = satirlar[i].strip()

                    if eski.startswith("#EXTINF:"):
                        break

                    i += 1

                continue

            yeni.append(s)

            i += 1

        print("[OK] ATV mevcut yerinde guncellendi")

    else:

        # 6 - Grubun son kanalini bul
        son_grup_bitisi = -1

        for idx, s in enumerate(satirlar):

            if (
                s.startswith("#EXTINF:")
                and grup_al(s) == GROUP
            ):

                bitis = idx + 1

                while (
                    bitis < len(satirlar)
                    and not satirlar[bitis].startswith("#EXTINF:")
                ):

                    bitis += 1

                son_grup_bitisi = bitis

        ek = yayin_satirlari(link)

        if son_grup_bitisi != -1:

            yeni = (
                satirlar[:son_grup_bitisi]
                + ek
                + satirlar[son_grup_bitisi:]
            )

            print("[EKLENDI] ATV grubun altina eklendi")

        else:

            yeni = satirlar + ek

            print("[BILGI] Grup bulunamadi, dosyanin sonuna eklendi")

    # 7 - Kaydetmeden once kontrol
    kontrol = sum(
        1 for s in yeni
        if (
            s.startswith("#EXTINF:")
            and grup_al(s) == GROUP
            and ad_al(s) == AD
        )
    )

    if kontrol != 1:

        print("[HATA] ATV tekrar kontrolunden gecemedi")
        print("[KORUMA] Orijinal dosya korunuyor")

        return

    # 8 - Gecici dosyaya yaz
    gecici = OUTPUT_FILE + ".tmp"

    try:

        with open(
            gecici,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f:

            f.write("\n".join(yeni) + "\n")

        # 9 - Orijinal dosyayi guvenli guncelle
        os.replace(
            gecici,
            OUTPUT_FILE
        )

        print("----------------------------------")
        print("[BASARILI] MIRTI68 ATV GUNCELLENDI")
        print("[LOGO] " + LOGO)
        print("[GRUP] " + GROUP)
        print("[KANAL] " + AD)
        print("[KOPYA] 1 adet")
        print("----------------------------------")

    except Exception as e:

        print("[HATA] Dosya kaydedilemedi:", e)

        if os.path.exists(gecici):
            os.remove(gecici)


if __name__ == "__main__":

    main()
                
