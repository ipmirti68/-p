#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MIRTI68 - 【entity-ATV¦canonical_name=ATV】 Canli - atv1.py
# 【entity-ATV Avrupa¦canonical_name=ATV】'yi REDDEDER, sadece 【entity-ATV¦canonical_name=ATV】 Turkiye kabul eder
# Kullanim 1: python atv1.py "https://trkvz.daioncdn.net/atv/atv.m3u8?..."
# Kullanim 2: GitHub Secrets -> ATV_URL olarak bookmarklet adresini koy

import os
import sys
import re
import requests
import urllib3
from urllib.parse import urlsplit, parse_qs, urlencode, urlunsplit

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SAYFA_URL = "https://www.atv.com.tr/canli-yayin"
ORIGIN = "https://www.atv.com.tr"
REFERER = SAYFA_URL
DOSYA = "mirti68.m3u"
KANAL = "ATVᴴᴰ⭕"
TVG_ID = "atv.tr"
LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"
GRUP = "🟨◆  ULUSALᴴᴰ ⭕"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# GitHub Secrets'ten gelir, yoksa bos
MANUEL_URL = os.environ.get("ATV_URL", "").strip()

def avrupa_mi(url):
    u = url.lower()
    return "atvavrupa" in u or "220182" in u or "atv_avrupa" in u

def url_temizle_1080p_yap(url):
    url = url.strip().strip('"').strip("'")
    if avrupa_mi(url):
        print("[REDDEDILDI] Bu 【entity-ATV Avrupa¦canonical_name=ATV】, 【entity-ATV Turkiye¦canonical_name=ATV】 degil:")
        print(url[:200])
        print("[SEBEP] GitHub sunucusu yurt disinda, site Avrupa veriyor.")
        return None
    if "daioncdn.net" not in url or ".m3u8" not in url:
        print("[HATA] ATV / Daion adresi degil:", url[:120])
        return None
    p = urlsplit(url)
    q = parse_qs(p.query)
    gerekli = {}
    for k in ["ce", "app", "st", "e", "sid", "ppid"]:
        if k in q and q[k]:
            gerekli[k] = q[k][0]
    yeni_path = re.sub(r"/atv[^/]*\.m3u8", "/atv/atv_1080p.m3u8", p.path, flags=re.I)
    if yeni_path == p.path:
        yeni_path = "/atv/atv_1080p.m3u8"
    yeni = urlunsplit((p.scheme, p.netloc, yeni_path, urlencode(gerekli), ""))
    print("[DONUSTURULDU] 1080P:", yeni[:250])
    return yeni

def yayin_test(url):
    print("[TEST] Yayin kontrol ediliyor...")
    headers = {"User-Agent": USER_AGENT, "Referer": REFERER, "Origin": ORIGIN, "Accept": "*/*"}
    try:
        r = requests.get(url, headers=headers, timeout=25, verify=False)
        print("[HTTP]", r.status_code)
        if r.status_code != 200:
            return False
        if "#EXTM3U" not in r.text[:2000].lstrip():
            print("[HATA] Gecerli HLS degil")
            return False
        print("[OK] Gecerli M3U8")
        return True
    except Exception as e:
        print("[UYARI] Test basarisiz:", e)
        return False

def atv_m3u_kaydi(url):
    return [
        f'#EXTINF:-1 tvg-id="{TVG_ID}" tvg-name="{KANAL}" tvg-logo="{LOGO}" group-title="{GRUP}",{KANAL}',
        "#EXTVLCOPT:http-referrer=" + REFERER,
        "#EXTVLCOPT:http-origin=" + ORIGIN,
        "#EXTVLCOPT:http-user-agent=" + USER_AGENT,
        url
    ]

def m3u_guncelle(url):
    if not os.path.exists(DOSYA):
        print("[HATA] M3U bulunamadi:", DOSYA)
        return False
    with open(DOSYA, "r", encoding="utf-8-sig") as f:
        satirlar = f.read().splitlines()
    baslik, bloklar, mevcut = [], [], []
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

    temiz, silinen = [], 0
    for blok in bloklar:
        metin = "\n".join(blok).lower()
        # Eski 【entity-ATV¦canonical_name=ATV】 + eski 【entity-ATV Avrupa¦canonical_name=ATV】 kayitlarini da sil, karismasin
        if 'tvg-id="atv.tr"' in metin or "atvᴴᴰ⭕".lower() in metin or "atvavrupa" in metin:
            silinen += 1
            continue
        temiz.append(blok)
    print(" Eski ATV / Avrupa kaydi silindi:", silinen)

    hedef = [i for i, blok in enumerate(temiz) if "group-title=" in blok[0] and "ULUSAL" in blok[0].upper()]
    yeni_blok = atv_m3u_kaydi(url)
    if hedef:
        temiz.insert(hedef[-1] + 1, yeni_blok)
        print(" ATV ULUSAL grubunun sonuna eklendi.")
    else:
        temiz.append(yeni_blok)
        print("[UYARI] ULUSAL bulunamadi, sona eklendi.")
    cikti = list(baslik)
    for blok in temiz:
        cikti.extend(blok)
    with open(DOSYA + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(cikti) + "\n")
    os.replace(DOSYA + ".tmp", DOSYA)
    print("[OK] M3U guncellendi.")
    return True

def main():
    gelen = ""
    if len(sys.argv) > 1:
        gelen = sys.argv[1]
    elif MANUEL_URL:
        gelen = MANUEL_URL
        print("[BILGI] ATV_URL Secret kullaniliyor")
    else:
        gelen = input("Bookmarklet ile buldugun ATV Turkiye adresini yapistir: ").strip()

    if not gelen:
        print("[HATA] Adres verilmedi.")
        return 1
    if avrupa_mi(gelen):
        print("[DURDURULDU] Verdign adres ATV Avrupa. ATV Turkiye adresi lazim.")
        print("[SONUC] Eski M3U korundu, yanlis kanal yazilmadi.")
        return 1

    url1080 = url_temizle_1080p_yap(gelen)
    if not url1080:
        return 1

    if yayin_test(url1080):
        final_url = url1080
    elif yayin_test(gelen.strip()):
        final_url = gelen.strip()
        print("[UYARI] 1080p calismadi, ana adres kullaniliyor")
    else:
        print("[BASARISIZ] Token suresi dolmus olabilir. Sayfayi yenileyip bookmarklet ile yeni adres al.")
        print("[SONUC] Eski M3U korundu.")
        return 1

    if not m3u_guncelle(final_url):
        return 1
    print("[TAMAMLANDI] 【entity-ATV Turkiye¦canonical_name=ATV】 guncellendi")
    return 0

if __name__ == "__main__":
    sys.exit(main())
