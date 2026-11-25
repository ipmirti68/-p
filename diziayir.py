#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DİZİAYIR - Son hali
Yapı: dizi/A/A Bloody Lucky Day.m3u
Grup: A Bloody Lucky Day
İçerik: S01E01, S01E02...
URL kontrolü KAPALI
"""
import re
import os
import argparse
import urllib.request
from collections import defaultdict

KAYNAKLAR = [
    "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u",
]

TUM_HARFLER = list("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ") + list("0123456789") + ["#"]
GENEL_GRUPLAR = {"dizi", "diziler", "series"}

def dosya_adi_temizle(s):
    # Dosya adında olmaması gereken karakterleri temizle
    s = re.sub(r'[\\/:*?"<>|]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def temizle_isim(s):
    s = s or ""
    s = re.sub(r'[🟪◆⭕]', '', s)
    s = re.sub(r'(?i)^DİZİ\s*-\s*', '', s)
    s = re.sub(r'(?i)^DIZI\s*-\s*', '', s)
    # Eski "A - Bloody Lucky Day" veya "A Bloody Lucky Day" gelirse harfi at
    s = re.sub(r'^[A-ZÇĞİÖŞÜ0-9#]\s*-\s*', '', s)
    s = re.sub(r'^[A-ZÇĞİÖŞÜ0-9#]\s+', '', s, count=1) if len(s.split()) > 1 else s
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def harf_bul(dizi):
    if not dizi:
        return "#"
    h = dizi.strip()[0].upper()
    if h in TUM_HARFLER:
        return h
    if h.isdigit():
        return h
    return "#"

def basliktan_dizi_adi(ham):
    b = ham or ""
    b = re.split(r'\s+[Ss]\d+\s*[Ee]\d+', b, flags=re.I)[0]
    b = re.split(r'\s+\d+\s*x\s*\d+', b, flags=re.I)[0]
    b = re.split(r'\s+Sezon.*', b, flags=re.I)[0]
    b = re.split(r'\s+\d+\.\s*Bölüm.*', b, flags=re.I)[0]
    b = b.split(" - ")[0].split(" | ")[0]
    return temizle_isim(b)

def dizi_adi_bul(grup, ham, tvg_name):
    if tvg_name:
        ad = basliktan_dizi_adi(tvg_name)
        if ad and ad.lower() not in GENEL_GRUPLAR:
            return ad
    ad_grup = temizle_isim(grup)
    if ad_grup and ad_grup.lower() not in GENEL_GRUPLAR and len(ad_grup) > 1:
        return ad_grup
    return basliktan_dizi_adi(ham)

def se_bul(baslik):
    m = re.search(r'[Ss](\d+)\s*[Ee](\d+)', baslik)
    if m:
        return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    m = re.search(r'(\d+)\s*x\s*(\d+)', baslik, flags=re.I)
    if m:
        return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    m = re.search(r'Sezon\s*(\d+).*?Bölüm\s*(\d+)', baslik, flags=re.I)
    if m:
        return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    m = re.search(r'(\d+)\.\s*Bölüm', baslik, flags=re.I)
    if m:
        return f"S01E{int(m.group(1)):02d}"
    return "S01E01"

def kaynak_oku(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read().decode("utf-8", errors="ignore")
    if data.startswith("\ufeff"):
        data = data[1:]
    return data

def m3u_parse_et(satirlar, havuz):
    i = 0
    while i < len(satirlar):
        satir = satirlar[i].strip()
        if satir.startswith("#EXTINF"):
            gm = re.search(r'group-title="([^"]*)"', satir)
            grup = gm.group(1) if gm else ""
            lm = re.search(r'tvg-logo="([^"]*)"', satir)
            logo = lm.group(1) if lm else ""
            nm = re.search(r'tvg-name="([^"]*)"', satir)
            tvg_name = nm.group(1) if nm else ""
            bm = re.search(r',(.+)$', satir)
            ham = bm.group(1).strip() if bm else ""

            url = ""
            j = i + 1
            while j < len(satirlar) and j < i + 6:
                aday = satirlar[j].strip()
                if aday.startswith("#"):
                    j += 1
                    continue
                if aday.startswith("http"):
                    url = aday
                    break
                j += 1

            if url:
                dizi = dizi_adi_bul(grup, ham, tvg_name)
                se = se_bul(ham + " " + tvg_name)
                if dizi:
                    harf = harf_bul(dizi)
                    # Grup adı = Dosya adı: A Bloody Lucky Day
                    grup_yeni = f"{harf} {dizi}"
                    yeni = f'#EXTINF:-1 tvg-name="{se}" tvg-logo="{logo}" group-title="{grup_yeni}",{se}'
                    for (eski_se, eski_u) in list(havuz[(harf, dizi)].keys()):
                        if eski_se == se:
                            del havuz[(harf, dizi)][(eski_se, eski_u)]
                            break
                    havuz[(harf, dizi)][(se, url)] = (yeni, url)
                i = j + 1
                continue
        i += 1

def calistir(cikti_klasor):
    havuz = defaultdict(dict)
    os.makedirs(cikti_klasor, exist_ok=True)

    # 1. ESKİYİ OKU - hem eski düz dizi/A.m3u hem de yeni dizi/A/A ...m3u yapısını oku
    print("Eski dosyalar okunuyor...")
    for kok, klasorler, dosyalar in os.walk(cikti_klasor):
        for f in dosyalar:
            if f.endswith(".m3u"):
                yol = os.path.join(kok, f)
                try:
                    with open(yol, encoding="utf-8", errors="ignore") as fh:
                        m3u_parse_et(fh.read().splitlines(), havuz)
                except Exception as e:
                    print(f"Eski okunamadı {yol}: {e}")

    # 2. KAYNAKTAN EKLE
    for kaynak in KAYNAKLAR:
        print(f"Kaynak: {kaynak}")
        icerik = kaynak_oku(kaynak)
        print(f"Kaynak satır: {len(icerik.splitlines())}")
        m3u_parse_et(icerik.splitlines(), havuz)

    # 3. ESKİ DÜZ DOSYALARI TEMİZLE - artık klasörlü yapıya geçiyoruz
    for f in os.listdir(cikti_klasor):
        yol = os.path.join(cikti_klasor, f)
        if os.path.isfile(yol) and f.endswith(".m3u"):
            os.remove(yol)

    # 4. YAZ: dizi/A/A Bloody Lucky Day.m3u
    for harf in TUM_HARFLER:
        klasor = os.path.join(cikti_klasor, harf)
        os.makedirs(klasor, exist_ok=True)
        diziler = sorted([d for (h, d) in havuz.keys() if h == harf], key=lambda x: x.lower())
        for dizi in diziler:
            grup_adi = f"{harf} {dizi}"
            dosya_adi = dosya_adi_temizle(grup_adi) + ".m3u"
            dosya = os.path.join(klasor, dosya_adi)
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for (se, url) in sorted(havuz[(harf, dizi)].keys()):
                    extinf, u = havuz[(harf, dizi)][(se, url)]
                    f.write(extinf + "\n")
                    f.write(u + "\n")
        print(f"{harf}/ -> {len(diziler)} dizi")

    toplam = sum(len(v) for v in havuz.values())
    print(f"Bitti: {len(havuz)} dizi, {toplam} bölüm")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="dizi")
    args = p.parse_args()
    calistir(args.out)
