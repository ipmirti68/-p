#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diziayir.py - MIRTI68
URL içindeki M3U'yu grup-title değerine göre ayırır.
Önce "dizi" klasörünü kurar, sonra içine yazar:
  dizi/dizi.GRUPADI.m3u

Her çalıştırmada:
  - Yeni / değişen grupları yazar (üzerine yazar = günceller)
  - Artık listede olmayan eski dizi.*.m3u dosyalarını siler
  - dizi/_GRUPLAR.txt özetini yeniler

Kullanım:
  python diziayir.py
  python diziayir.py --url "https://.../dizi.m3u"
  python diziayir.py --file dizi.m3u
  python diziayir.py --out dizi --no-temizle   (eski dosyaları silme)
"""

import argparse
import os
import re
import sys
import urllib.request

VARSAYILAN_URL = "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u"
VARSAYILAN_KLASOR = "dizi"
VARSAYILAN_ONEK = "dizi"

YASAKLI = r'\/\\:*?"<>|'

def dosya_adi_temizle(grup):
    ad = grup.strip() or "Grupsuz"
    for ch in YASAKLI:
        ad = ad.replace(ch, "-")
    ad = "".join(c for c in ad if ord(c) >= 32)
    ad = ad.strip().strip(".")
    ad = re.sub(r"\s+", " ", ad)
    ad = re.sub(r"-+", "-", ad)
    if len(ad) > 80:
        ad = ad[:80].rstrip(" -.")
    return ad or "Grupsuz"

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
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")

def ayir(metin, out_dir, prefix, temizle=True):
    # 1) ÖNCE KLASÖRÜ KUR
    os.makedirs(out_dir, exist_ok=True)
    print(f"Klasör hazır: {out_dir}/")

    satirlar = metin.splitlines()
    gruplar = {}
    sira = []
    mevcut_grup = None
    bekleyen_blok = []

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
            mevcut_grup = s[len("#EXTGRP:"):].strip() or "Grupsuz"
            continue
        if s.startswith("#EXTINF"):
            if bekleyen_blok:
                blogu_kaydet(bekleyen_blok, mevcut_grup or "Grupsuz")
            mevcut_grup = grup_bul(s)
            bekleyen_blok = [satir]
            continue
        if s.startswith("#") and bekleyen_blok:
            bekleyen_blok.append(satir)
            continue
        if s.startswith("#"):
            continue
        if bekleyen_blok:
            bekleyen_blok.append(satir)
            blogu_kaydet(bekleyen_blok, mevcut_grup or "Grupsuz")
            bekleyen_blok = []
            mevcut_grup = None
        else:
            blogu_kaydet([satir], "Grupsuz")

    if bekleyen_blok:
        blogu_kaydet(bekleyen_blok, mevcut_grup or "Grupsuz")

    # 2) DOSYALARI YAZ / GÜNCELLE
    yazilan = set()
    ozet = []
    for grup in sira:
        temiz = dosya_adi_temizle(grup)
        dosya_adi = f"{prefix}.{temiz}.m3u"
        dosya = os.path.join(out_dir, dosya_adi)
        sayac = 2
        while dosya_adi in yazilan:
            dosya_adi = f"{prefix}.{temiz}-{sayac}.m3u"
            dosya = os.path.join(out_dir, dosya_adi)
            sayac += 1
        yazilan.add(dosya_adi)
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n" + "\n".join(gruplar[grup]) + "\n")
        adet = sum(1 for x in gruplar[grup] if x.startswith("#EXTINF"))
        ozet.append((grup, adet, dosya_adi))
        print(f"  {adet:4d} adet -> {out_dir}/{dosya_adi}")

    # 3) ESKİ / ARTIK OLMAYAN GRUP DOSYALARINI SİL (günlük güncelleme)
    if temizle:
        for ad in os.listdir(out_dir):
            if ad.startswith(prefix + ".") and ad.endswith(".m3u") and ad not in yazilan:
                try:
                    os.remove(os.path.join(out_dir, ad))
                    print(f"  silindi (artık yok): {out_dir}/{ad}")
                except OSError as e:
                    print(f"  silinemedi {ad}: {e}")

    # 4) ÖZET
    ozet_yolu = os.path.join(out_dir, "_GRUPLAR.txt")
    with open(ozet_yolu, "w", encoding="utf-8") as f:
        f.write(f"Toplam grup: {len(ozet)}\n")
        f.write(f"Toplam dizi/bölüm: {sum(a for _, a, _ in ozet)}\n\n")
        for grup, adet, dosya_adi in ozet:
            f.write(f"{adet:4d} | {grup} | {dosya_adi}\n")
    print(f"\nToplam {len(ozet)} grup, {sum(a for _, a, _ in ozet)} kayıt")
    print(f"Özet: {ozet_yolu}")
    return ozet

def main():
    p = argparse.ArgumentParser(description="M3U'yu dizi/ klasörüne grup grup ayırır, her gün günceller")
    p.add_argument("--url", default=VARSAYILAN_URL, help="Kaynak M3U URL")
    p.add_argument("--file", default=None, help="URL yerine yerel M3U dosyası kullan")
    p.add_argument("--out", default=VARSAYILAN_KLASOR, help="Klasör adı (varsayılan: dizi)")
    p.add_argument("--prefix", default=VARSAYILAN_ONEK, help="Dosya öneki (varsayılan: dizi)")
    p.add_argument("--no-temizle", dest="temizle", action="store_false", help="Artık olmayan eski grup dosyalarını silme")
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

    ayir(metin, args.out, args.prefix, temizle=args.temizle)

if __name__ == "__main__":
    main()
