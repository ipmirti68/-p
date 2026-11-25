#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DİZİAYIR - capcanli kaynağı, ilk harfe göre gruplu, sabit isimli
- Kaynak: kimbumuratyavuz/capcanli dizi.m3u
- Grup: 🟪◆ DİZİ - I - Island ⭕  (Harf + Dizi Adı)
- Başlık: Sadece S01E01
- Dizi adı başlıkta tekrarlanmaz, sadece grupta
- Logo kaynaktan aynen gelir
- requests gerektirmez
"""
import re
import os
import argparse
import urllib.request
from collections import defaultdict

KAYNAKLAR = [
    "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u",
]

def temizle_isim(s):
    s = s or ""
    s = re.sub(r'[🟪◆⭕]', '', s)
    s = re.sub(r'(?i)^DİZİ\s*-\s*', '', s)
    s = re.sub(r'(?i)^DIZI\s*-\s*', '', s)
    # Kaynakta "DİZİ - I - Island" gibi gelirse harfi at, biz yeniden ekleyeceğiz
    s = re.sub(r'^[A-ZÇĞİÖŞÜ]\s*-\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def ilk_harf(dizi):
    if not dizi:
        return "#"
    h = dizi[0].upper()
    # Türkçe karakterleri düzelt
    if h == "İ":
        return "İ"
    return h

def dizi_adi_bul(extinf_satiri, grup):
    ad = temizle_isim(grup)
    if not ad:
        m = re.search(r',(.+)', extinf_satiri)
        if m:
            baslik = m.group(1).strip()
            ad = re.split(r'\s+S\d+E\d+', baslik, flags=re.I)[0]
            ad = re.split(r'\s+-\s+', ad)[0]
            ad = temizle_isim(ad)
    return ad

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
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="ignore")

def calistir(cikti_klasor):
    # (harf, dizi) -> { (se, url): (extinf, url) }
    havuz = defaultdict(dict)

    for kaynak in KAYNAKLAR:
        print(f"Kaynak: {kaynak}")
        try:
            icerik = kaynak_oku(kaynak)
            satirlar = icerik.splitlines()
        except Exception as e:
            print(f"Kaynak okunamadı: {e}")
            continue

        i = 0
        while i < len(satirlar):
            satir = satirlar[i].strip()
            if satir.startswith("#EXTINF"):
                gm = re.search(r'group-title="([^"]*)"', satir)
                grup = gm.group(1) if gm else ""
                lm = re.search(r'tvg-logo="([^"]*)"', satir)
                logo = lm.group(1) if lm else ""
                bm = re.search(r',(.+)$', satir)
                ham_baslik = bm.group(1).strip() if bm else ""

                if i + 1 < len(satirlar) and satirlar[i+1].strip().startswith("http"):
                    url = satirlar[i+1].strip()
                    dizi = dizi_adi_bul(satir, grup)
                    se = se_bul(ham_baslik)

                    if dizi:
                        harf = ilk_harf(dizi)
                        # GRUP: Harf + Dizi adı
                        grup_yeni = f"🟪◆ DİZİ - {harf} - {dizi} ⭕"
                        # BAŞLIK: Sadece S01E01, dizi adı YOK, logo var
                        yeni_extinf = f'#EXTINF:-1 tvg-name="{se}" tvg-logo="{logo}" group-title="{grup_yeni}",{se}'
                        havuz[(harf, dizi)][(se, url)] = (yeni_extinf, url)
                    i += 2
                    continue
            i += 1

    os.makedirs(cikti_klasor, exist_ok=True)
    cikti = os.path.join(cikti_klasor, "dizi.m3u")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        # Önce harfe, sonra dizi adına, sonra bölüme göre sırala
        for (harf, dizi) in sorted(havuz.keys(), key=lambda x: (x[0], x[1].lower())):
            for (se, url) in sorted(havuz[(harf, dizi)].keys()):
                extinf, u = havuz[(harf, dizi)][(se, url)]
                f.write(extinf + "\n")
                f.write(u + "\n")

    toplam = sum(len(v) for v in havuz.values())
    print(f"Bitti: {len(havuz)} dizi, {toplam} bölüm -> {cikti}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="dizi")
    args = p.parse_args()
    calistir(args.out)
