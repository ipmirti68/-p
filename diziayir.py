#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import argparse
import urllib.request
from collections import defaultdict

KAYNAKLAR = [
    "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u",
]

GENEL_GRUPLAR = {"dizi", "diziler", "series"}

def temizle_isim(s):
    s = s or ""
    s = re.sub(r'[🟪◆⭕]', '', s)
    s = re.sub(r'(?i)^DİZİ\s*-\s*', '', s)
    s = re.sub(r'(?i)^DIZI\s*-\s*', '', s)
    s = re.sub(r'^[A-ZÇĞİÖŞÜ]\s*-\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def ilk_harf(dizi):
    if not dizi:
        return "#"
    return dizi[0].upper()

def basliktan_dizi_adi(ham_baslik):
    b = ham_baslik or ""
    b = re.split(r'\s+[Ss]\d+\s*[Ee]\d+', b, flags=re.I)[0]
    b = re.split(r'\s+\d+\s*x\s*\d+', b, flags=re.I)[0]
    b = re.split(r'\s+Sezon.*', b, flags=re.I)[0]
    b = re.split(r'\s+\d+\.\s*Bölüm.*', b, flags=re.I)[0]
    b = b.split(" - ")[0]
    b = b.split(" | ")[0]
    return temizle_isim(b)

def dizi_adi_bul(extinf_satiri, grup, ham_baslik, tvg_name):
    if tvg_name:
        ad = basliktan_dizi_adi(tvg_name)
        if ad and ad.lower() not in GENEL_GRUPLAR:
            return ad
    ad_grup = temizle_isim(grup)
    if ad_grup and ad_grup.lower() not in GENEL_GRUPLAR and len(ad_grup) > 1:
        return ad_grup
    return basliktan_dizi_adi(ham_baslik)

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
        data = r.read().decode("utf-8", errors="ignore")
    if data.startswith("\ufeff"):
        data = data[1:]
    return data

def calistir(cikti_klasor):
    havuz = defaultdict(dict)

    for kaynak in KAYNAKLAR:
        print(f"Kaynak: {kaynak}")
        icerik = kaynak_oku(kaynak)
        satirlar = icerik.splitlines()
        print(f"Toplam satır: {len(satirlar)}")

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
                ham_baslik = bm.group(1).strip() if bm else ""

                url = ""
                j = i + 1
                while j < len(satirlar) and j < i + 6:
                    aday = satirlar[j].strip()
                    if aday.startswith("#"):
                        j += 1
                        continue
                    if aday.startswith("http") or ".m3u8" in aday or ".mp4" in aday:
                        url = aday
                        break
                    j += 1

                if url:
                    dizi = dizi_adi_bul(satir, grup, ham_baslik, tvg_name)
                    se = se_bul(ham_baslik + " " + tvg_name)
                    if dizi:
                        harf = ilk_harf(dizi)
                        grup_yeni = f"🟪◆ DİZİ - {harf} - {dizi} ⭕"
                        yeni_extinf = f'#EXTINF:-1 tvg-name="{se}" tvg-logo="{logo}" group-title="{grup_yeni}",{se}'
                        havuz[(harf, dizi)][(se, url)] = (yeni_extinf, url)
                    i = j + 1
                    continue
            i += 1

    os.makedirs(cikti_klasor, exist_ok=True)

    # Eski harf dosyalarını temizle, yarım eski dosya kalmasın
    for f in os.listdir(cikti_klasor):
        if f.endswith(".m3u"):
            os.remove(os.path.join(cikti_klasor, f))

    # Harfe göre ayrı dosya yaz
    harfler = sorted(set(h for (h, d) in havuz.keys()))
    for harf in harfler:
        # Dosya adı için güvenli harf: İ -> I dosyası gibi çakışmasın diye orijinal harfi kullan
        dosya = os.path.join(cikti_klasor, f"{harf}.m3u")
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            # Bu harfteki diziler
            diziler = sorted([d for (h, d) in havuz.keys() if h == harf], key=lambda x: x.lower())
            for dizi in diziler:
                for (se, url) in sorted(havuz[(harf, dizi)].keys()):
                    extinf, u = havuz[(harf, dizi)][(se, url)]
                    f.write(extinf + "\n")
                    f.write(u + "\n")
        print(f"{harf}.m3u yazıldı")

    toplam = sum(len(v) for v in havuz.values())
    print(f"Bitti: {len(havuz)} dizi, {toplam} bölüm, {len(harfler)} harf dosyası")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="dizi")
    args = p.parse_args()
    calistir(args.out)
