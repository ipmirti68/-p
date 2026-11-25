#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diziayir.py - MIRTI68
URL içindeki M3U'yu group-title değerine göre ayırır.
Önce "dizi" klasörünü kurar, sonra içine yazar:
  dizi/Island.m3u
  dizi/10 Bin Adım.m3u

KURAL: Grup adı SADECE group-title içinde ve DOSYA ADINDA olur.
Dosyanın içindeki görünen ad (virgülden sonrası) ve tvg-name içinde
grup adı ASLA yazılmaz.
  Örn: group-title="Island",Island S1E1 - Altyazı  ->  group-title="Island",S1E1 - Altyazı
  Örn: group-title="10 Bin Adım",10 Bin Adım - Sezon 1 - Bölüm 1 - Altyazı  ->  group-title="10 Bin Adım",S1E1 - Altyazı

Her çalıştırmada eski / artık olmayan grup dosyalarını siler (günlük güncelleme).

Kullanım:
  python diziayir.py
  python diziayir.py --url "https://.../dizi.m3u" --out dizi
  python diziayir.py --file dizi.m3u --out dizi
"""

import argparse
import os
import re
import sys
import urllib.request

VARSAYILAN_URL = "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u"
VARSAYILAN_KLASOR = "dizi"
VARSAYILAN_ONEK = ""  # Boş: dosya adı = GRUPADI.m3u, önünde dizi. yok

YASAKLI = r'\/\\:*?"<>|'

def dosya_adi_temizle(grup):
    ad = (grup or "").strip() or "Grupsuz"
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

def _grup_adini_at(ad, grup):
    """Adın başından, ortasından, sonundan grup adını (birebir + ayraçlarıyla) at."""
    if not grup or not ad:
        return ad.strip()
    # Önce tam hali: "Island - ..." / "Island: ..." / "Island ..."
    ad = re.sub(r"(?i)^\s*" + re.escape(grup) + r"\s*[-–—:,.]?\s*", "", ad.strip())
    # İçte kalan tekrarlar: "... - Island - ..." / "... Island ..."
    ad = re.sub(r"(?i)\s*[-–—:]\s*" + re.escape(grup) + r"\s*[-–—:,.]?\s*", " - ", ad)
    ad = re.sub(r"(?i)\b" + re.escape(grup) + r"\b\s*[-–—:,.]?\s*", "", ad)
    # Tekrar "IslandIsland" gibi bitişik kalırsa da temizle
    ad = re.sub(r"(?i)" + re.escape(grup), "", ad)
    ad = re.sub(r"\s+", " ", ad).strip(" -–—:,. ")
    # Ayraçlar üst üste kaldıysa düzelt: "S1E1 - - Altyazı" -> "S1E1 - Altyazı"
    ad = re.sub(r"\s*[-–—]\s*[-–—]\s*", " - ", ad)
    return ad.strip(" -–—:,. ")

def isim_temizle(grup, ad):
    """Görünen adı grup adından arındır, Sezon/Bölüm -> S1E1 yap.
    DÖNÜŞTE GRUP ADI YOK: 'Island - Sezon 1 - Bölüm 1 - Altyazı' -> 'S1E1 - Altyazı'"""
    if not ad:
        return "Bölüm"
    kalan = _grup_adini_at(ad.strip(), grup)
    # Sezon X - Bölüm Y -> S1E1 (Sezon 1 Bölüm 1 / S1 B1 / 1. Sezon 1. Bölüm)
    m = re.search(r"(?i)(?:sezon|s)\s*0*(\d+)\s*(?:[-–—:. ]+)?(?:b[öo]l[üu]m|b|e|episode)\s*0*(\d+)", kalan)
    if m:
        sezon, bolum = m.group(1), m.group(2)
        once = _grup_adini_at(kalan[:m.start()], grup)
        sonra = _grup_adini_at(kalan[m.end():], grup)
        parcalar = [x for x in [once, sonra] if x]
        sxxexx = f"S{sezon}E{bolum}"
        if parcalar:
            return f"{sxxexx} - {' - '.join(parcalar)}"
        return sxxexx
    # Sezon/Bölüm yoksa sadece grup adı atılmış kalanı döndür
    if kalan:
        return kalan
    return "Bölüm"

def extinf_temizle(satir, grup):
    """#EXTINF satırındaki tvg-name ve virgülden sonraki görünen adı temizler.
    group-title'e DOKUNMAZ, o grup adı olarak kalır."""
    if "," not in satir:
        return satir
    bas, gorunen = satir.rsplit(",", 1)
    yeni = isim_temizle(grup, gorunen)
    bas = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{yeni}"', bas)
    bas = re.sub(r"tvg-name='[^']*'", f"tvg-name='{yeni}'", bas)
    return bas + "," + yeni

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
            bekleyen_blok = [extinf_temizle(satir, mevcut_grup)]
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

    ozet = []
    for grup in sira:
        temiz = dosya_adi_temizle(grup)
        taban = f"{prefix}.{temiz}" if prefix else temiz
        dosya = os.path.join(out_dir, f"{taban}.m3u")
        sayac = 2
        while os.path.exists(dosya) and dosya not in [x[2] for x in ozet]:
            dosya = os.path.join(out_dir, f"{taban}-{sayac}.m3u")
            sayac += 1
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n" + "\n".join(gruplar[grup]) + "\n")
        adet = sum(1 for x in gruplar[grup] if x.startswith("#EXTINF"))
        ozet.append((grup, adet, dosya))
        print(f"  {adet:4d} adet -> {dosya}")

    if temizle:
        yazilan_adlar = {os.path.basename(x[2]) for x in ozet}
        for ad in os.listdir(out_dir):
            if ad.endswith(".m3u") and ad not in yazilan_adlar:
                try:
                    os.remove(os.path.join(out_dir, ad))
                    print(f"  silindi (artık yok): {ad}")
                except OSError as e:
                    print(f"  silinemedi {ad}: {e}")

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
    p = argparse.ArgumentParser(description="M3U'yu gruplara göre dizi/GRUPADI.m3u olarak ayırır, iç isimde grup adı bırakmaz")
    p.add_argument("--url", default=VARSAYILAN_URL, help="Kaynak M3U URL")
    p.add_argument("--file", default=None, help="URL yerine yerel M3U dosyası kullan")
    p.add_argument("--out", default=VARSAYILAN_KLASOR, help="Çıktı klasörü (varsayılan: dizi)")
    p.add_argument("--prefix", default=VARSAYILAN_ONEK, help="Dosya öneki (varsayılan: boş)")
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
