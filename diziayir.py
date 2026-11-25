#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DİZİAYIR - Tek dosya, sabit isimli
- Her dizi için ayrı dosya açmaz, hepsini dizi/dizi.m3u içine yazar
- Başlıkta dizi ismini tekrarlamaz, sadece S01E01 yazar
- Grup adında dizi ismi olur
- Kaynak başlığı değişse bile isim değişmez
"""
import re
import os
import requests
from collections import defaultdict

# BURAYA KAYNAK LİSTENİ YAZ
KAYNAKLAR = [
    "https://raw.githubusercontent.com/k33n26/iptv/refs/heads/master/Bizimkiler.m3u",
]

CIKTI = "dizi/dizi.m3u"

def temizle_isim(s):
    s = s or ""
    s = re.sub(r'[🟪◆⭕]', '', s)
    s = s.replace("DİZİ -", "").replace("DIZI -", "").replace("Dizi -", "")
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def dizi_adi_bul(extinf_satiri, grup):
    # Önce grup adından al, en stabil olanı bu
    ad = temizle_isim(grup)
    # Grupta "Island" gibi tek isim varsa onu kullan
    # Grup boşsa başlıktan al
    if not ad:
        # Başlıktaki S01E01 öncesini al
        m = re.search(r',(.+)', extinf_satiri)
        if m:
            baslik = m.group(1).strip()
            ad = re.split(r'\s+S\d+E\d+', baslik, flags=re.I)[0]
            ad = re.split(r'\s+-\s+', ad)[0]
            ad = temizle_isim(ad)
    return ad

def se_bul(baslik):
    # S1E1, S01E01, 1x01, Sezon 1 Bölüm 1 gibi her şeyi S01E01 yapar
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

def calistir():
    # dizi_adi -> { (se, url): satirlar }
    havuz = defaultdict(dict)

    for kaynak in KAYNAKLAR:
        print(f"Kaynak: {kaynak}")
        try:
            r = requests.get(kaynak, timeout=60)
            r.raise_for_status()
            satirlar = r.text.splitlines()
        except Exception as e:
            print(f"Kaynak okunamadı: {e}")
            continue

        i = 0
        while i < len(satirlar):
            satir = satirlar[i].strip()
            if satir.startswith("#EXTINF"):
                # grup-title al
                gm = re.search(r'group-title="([^"]*)"', satir)
                grup = gm.group(1) if gm else ""
                # logo al
                lm = re.search(r'tvg-logo="([^"]*)"', satir)
                logo = lm.group(1) if lm else ""
                # başlık al (virgülden sonrası)
                bm = re.search(r',(.+)$', satir)
                ham_baslik = bm.group(1).strip() if bm else ""

                # Bir sonraki satır URL olmalı
                if i + 1 < len(satirlar) and satirlar[i+1].strip().startswith("http"):
                    url = satirlar[i+1].strip()
                    dizi = dizi_adi_bul(satir, grup)
                    se = se_bul(ham_baslik)

                    if dizi:
                        # SABİT BAŞLIK: İsim tekrarı yok, sadece S01E01
                        # Grup: 🟪◆ DİZİ - Island ⭕
                        grup_yeni = f"🟪◆ DİZİ - {dizi} ⭕"
                        # tvg-name de sabit: Island S01E01
                        yeni_extinf = f'#EXTINF:-1 tvg-name="{dizi} {se}" tvg-logo="{logo}" group-title="{grup_yeni}",{se}'
                        # Aynı dizi + aynı bölüm + aynı URL tekrar ederse ekleme
                        havuz[dizi][(se, url)] = (yeni_extinf, url)
                    i += 2
                    continue
            i += 1

    os.makedirs("dizi", exist_ok=True)
    with open(CIKTI, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        # Dizi adına göre sırala, böylece her seferinde aynı sıra olur
        for dizi in sorted(havuz.keys(), key=lambda x: x.lower()):
            # Bölüme göre sırala
            for (se, url) in sorted(havuz[dizi].keys()):
                extinf, u = havuz[dizi][(se, url)]
                f.write(extinf + "\n")
                f.write(u + "\n")

    toplam = sum(len(v) for v in havuz.values())
    print(f"Bitti: {len(havuz)} dizi, {toplam} bölüm -> {CIKTI}")

if __name__ == "__main__":
    calistir()
