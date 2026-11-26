
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MIRTI68 - ATV CANLI
# GRUP ALTINA EKLE - TEKRAR EKLEME - LINK YENILEME

import requests
import re
import os
import time
import html

OUTPUT_FILE = "mirti68.m3u"

GROUP = "🟨◆  ULUSALᴴᴰ ⭕"
AD = "ATVᴴᴰ⭕"

SITE_ID = "0fe2a405-8afa-4238-b429-e5f96aec3a5c"
LIVE_ID = "00000000-0000-0000-0000-000000000000"

ATV_PAGE = "https://www.atv.com.tr/canli-yayin"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.atv.com.tr/",
    "Origin": "https://www.atv.com.tr"
}

REFERER = "https://www.atv.com.tr/"

session = requests.Session()
session.headers.update(HEADERS)


def kimlikleri_al():

    global SITE_ID, LIVE_ID

    try:
        r = session.get(
            ATV_PAGE,
            timeout=25
        )

        r.raise_for_status()

        sayfa = html.unescape(r.text)

        # HTML data-videoid / data-websiteid
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

            print("[OK] ATV kimlikleri sayfadan alindi")
            return True

        # Script icindeki tmdPlayer
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

                print("[OK] ATV kimlikleri player icinden alindi")
                return True

        print("[BILGI] Sayfadan kimlik alinamadi, mevcut kimlikler kullanilacak")

    except Exception as e:
        print("[UYARI] Sayfa kimlik hatasi:", e)

    return True


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

        # YENI API JSON YAPISI
        video = data.get("video", {})

        ham = (
            video.get("VideoSmilUrl")
            or video.get("VideoUrl")
            or video.get("videoUrl")
            or video.get("Url")
            or video.get("url")
            or ""
        )

        if not ham:
            print("[HATA] API VideoSmilUrl vermedi")
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

        if data2.get("Success") is not True:
            print("[HATA] Guvenli yayin tokeni onaylanmadi")
            print("[TOKEN]", str(data2)[:500])
            return ""

        link = (
            data2.get("Url")
            or data2.get("url")
            or ""
        ).strip()

        if not link.startswith("http"):
            print("[HATA] Gecersiz yayin adresi")
            return ""

        if ".m3u8" not in link.lower():
            print("[HATA] Token sonucu M3U8 degil")
            print("[LINK]", link[:300])
            return ""

        print("[OK] ATV M3U8 yayin adresi alindi")

        return link

    except Exception as e:

        print("[HATA] ATV yayin alma:", str(e))
        return ""


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


def kanal_satiri():

    return (
        '#EXTINF:-1 tvg-name="' + AD +
        '" tvg-logo="" group-title="' + GROUP +
        '",' + AD
    )


def yayin_satirlari(link):

    return [
        kanal_satiri(),
        '#EXTVLCOPT:http-referer=' + REFERER,
        '#EXTVLCOPT:http-user-agent=' + HEADERS["User-Agent"],
        link
    ]


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

    # 4 - Mevcut ATV kaydini bul
    hedef_idx = -1

    for idx, s in enumerate(satirlar):

        if (
            s.startswith("#EXTINF:")
            and grup_al(s) == GROUP
            and ad_al(s) == AD
        ):

            hedef_idx = idx
            break

    yeni = []

    # 5 - Varsa eski yerinde guncelle
    if hedef_idx != -1:

        print("[BULUNDU] ATV mevcut konumunda yenileniyor")

        i = 0

        while i < len(satirlar):

            s = satirlar[i]

            if i == hedef_idx:

                yeni.append(kanal_satiri())

                yeni.extend([
                    '#EXTVLCOPT:http-referer=' + REFERER,
                    '#EXTVLCOPT:http-user-agent=' + HEADERS["User-Agent"],
                    link
                ])

                i += 1

                while i < len(satirlar):

                    eski = satirlar[i].strip()

                    if (
                        eski.startswith("#EXTINF:")
                    ):
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

            yeni.append(s)
            i += 1

        print("[OK] ATV eski yerinde guncellendi")

    else:

        # 6 - Grup sonunu bul
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

            print("[BILGI] Grup yok, ATV dosyanin sonuna eklendi")

    # 7 - Guvenli kaydetme
    gecici = OUTPUT_FILE + ".tmp"

    try:

        with open(
            gecici,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f:

            f.write("\n".join(yeni) + "\n")

        os.replace(
            gecici,
            OUTPUT_FILE
        )

        print("[BASARILI] MIRTI68 ATV GUNCELLENDI")

    except Exception as e:

        print("[HATA] Dosya kaydedilemedi:", e)

        if os.path.exists(gecici):
            os.remove(gecici)


if __name__ == "__main__":
    main()
    
