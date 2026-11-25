#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diziayir.py - MIRTI68
URL içindeki M3U'yu grup-title değerine göre ayırır.
Her grup -> dizi/dizi.GRUPADI.m3u (önce dizi klasörünü kurar, her gün günceller)

Kullanım:
  python diziayir.py
  python diziayir.py --url "https://.../dizi.m3u" --out cikti
  python diziayir.py --url "https://.../dizi.m3u" --out cikti --prefix dizi
"""

import argparse
import os
import re
import sys
import unicodedata
import urllib.request

VARSAYILAN_URL = "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u"

# Türkçe karakterleri dosya adında bozulmasın diye koru, sadece yasaklıları temizle
YASAKLI = r'\/\\:*?"<>|'

def dosya_adi_temizle(grup):
    ad = grup.strip()
    if not ad:
        ad = "Grupsuz"
    # Yasaklı karakterleri - yap
    for ch in YASAKLI:
        ad = ad.replace(ch, "-")
    # Kontrol karakterleri + satır sonları
    ad = "".join(c for c in ad if ord(c) >= 32)
    ad = ad.strip().strip(".")
    # Çoklu boşluk / tire temizliği
    ad = re.sub(r"\s+", " ", ad)
    ad = re.sub(r"-+", "-", ad)
    # Çok uzun grup adlarını kısalt (Windows sınırı için)
    if len(ad) > 80:
        ad = ad[:80].rstrip(" -.")
    if not ad:
        ad = "Grupsuz"
    return ad

def grup_bul(extinf_satiri):
    m = re.search(r'group-title="([^"]*)"', extinf_satiri)
    if m:
        return m.group(1).strip() or "Grupsuz"
    m = re.search(r"group-title='([^']*)'", extinf_satiri)
    if m:
        return m.group(1).strip() or "Grupsuz"
    return "Grupsuz"

def m3u_indir(url):
    print(f"İndiriliyor: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    # utf-8-sig BOM'u da yutar
    try:
        metin = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        metin = data.decode("utf-8", errors="ignore")
    return metin

def ayir(metin, out_dir, prefix, temizle=True):
    os.makedirs(out_dir, exist_ok=True)
    satirlar = metin.splitlines()

    gruplar = {}  # grup_adi -> [satir, satir...]
    sira = []     # ilk görünüş sırası
    mevcut_grup = None
    bekleyen_blok = []  # EXTINF + ara satırlar, URL gelene kadar tut

    def blogu_kaydet(blok, grup):
        if not blok:
            return
        if grup not in gruplar:
            gruplar[grup] = []
            sira.append(grup)
        gruplar[grup].extend(blok)

    for satir in satirlar:
        s = satir.strip()
        if not s:
            continue
        if s.startswith("#EXTM3U"):
            continue
        if s.startswith("#EXTGRP:"):
            # EXTGRP varsa grup olarak kullan, bir sonraki EXTINF bunu ezebilir
            g = s[len("#EXTGRP:"):].strip() or "Grupsuz"
            mevcut_grup = g
            continue
        if s.startswith("#EXTINF"):
            # Önceki blok yarım kaldıysa (URL'siz) yine de kaydet, kaybolmasın
            if bekleyen_blok:
                blogu_kaydet(bekleyen_blok, mevcut_grup or "Grupsuz")
            mevcut_grup = grup_bul(s)
            bekleyen_blok = [satir]
            continue
        if s.startswith("#") and bekleyen_blok:
            # #EXTVLCOPT gibi EXTINF ile URL arası satırlar bloğa dahil
            bekleyen_blok.append(satir)
            continue
        if s.startswith("#"):
            # Bağımsız yorum satırı, atla
            continue
        # URL satırı -> blok tamamlandı
        if bekleyen_blok:
            bekleyen_blok.append(satir)
            blogu_kaydet(bekleyen_blok, mevcut_grup or "Grupsuz")
            bekleyen_blok = []
            mevcut_grup = None
        else:
            # EXTINF'siz tek başına URL
            blogu_kaydet([satir], "Grupsuz")

    if bekleyen_blok:
        blogu_kaydet(bekleyen_blok, mevcut_grup or "Grupsuz")

    # Dosyaları yaz
    ozet = []
    for grup in sira:
        temiz = dosya_adi_temizle(grup)
        dosya = os.path.join(out_dir, f"{prefix}.{temiz}.m3u")
        # Aynı temiz ad iki farklı gruptan gelirse ezmesin
        sayac = 2
        while os.path.exists(dosya) and dosya not in [x[2] for x in ozet]:
            dosya = os.path.join(out_dir, f"{prefix}.{temiz}-{sayac}.m3u")
            sayac += 1
        icerik = ["#EXTM3U"] + gruplar[grup]
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("\n".join(icerik) + "\n")
        adet = sum(1 for x in gruplar[grup] if x.startswith("#EXTINF"))
        ozet.append((grup, adet, dosya))
        print(f"  {adet:4d} adet -> {dosya}")

    # Artık listede olmayan eski grup dosyalarını sil (günlük güncelleme)
    if temizle:
        yazilan_adlar = {os.path.basename(x[2]) for x in ozet}
        for ad in os.listdir(out_dir):
            if ad.startswith(prefix + ".") and ad.endswith(".m3u") and ad not in yazilan_adlar:
                try:
                    os.remove(os.path.join(out_dir, ad))
                    print(f"  silindi (artık yok): {ad}")
                except OSError as e:
                    print(f"  silinemedi {ad}: {e}")

    # Özet listesi
    ozet_yolu = os.path.join(out_dir, "_GRUPLAR.txt")
    with open(ozet_yolu, "w", encoding="utf-8") as f:
        f.write(f"Toplam grup: {len(ozet)}\n")
        f.write(f"Toplam dizi/bölüm: {sum(a for _, a, _ in ozet)}\n\n")
        for grup, adet, dosya in ozet:
            f.write(f"{adet:4d} | {grup} | {os.path.basename(dosya)}\n")
    print(f"\nToplam {len(ozet)} grup, {sum(a for _, a, _ in ozet)} kayıt")
    print(f"Özet: {ozet_yolu}")
    return ozet

def main():
    p = argparse.ArgumentParser(description="M3U'yu gruplara göre dizi.GRUPADI.m3u olarak ayırır")
    p.add_argument("--url", default=VARSAYILAN_URL, help="Kaynak M3U URL")
    p.add_argument("--file", default=None, help="URL yerine yerel M3U dosyası kullan")
    p.add_argument("--out", default="dizi", help="Çıktı klasörü (varsayılan: dizi)")
    p.add_argument("--prefix", default="dizi", help="Dosya öneki (varsayılan: dizi)")
    args = p.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8-sig", errors="ignore") as f:
            metin = f.read()
    else:
        try:
            metin = m3u_indir(args.url)
        except Exception as e:
            print(f"HATA: URL indirilemedi: {e}", file=sys.stderr)
            sys.exit(1)

    ayir(metin, args.out, args.prefix, temizle=True)

if __name__ == "__main__":
    main()
