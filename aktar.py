# ==================================================
# MIRTI68 - TEK AKTARICI (Grup içi SİLMEZ, BİRLEŞTİRİR)
# Kural:
# - Hedefte aynı isimde grup varsa -> İÇİNE BİRLEŞTİR
#   Aynı isimli kayıt varsa güncelle, yoksa ekle, diğerlerine DOKUNMA
# - Yoksa aynı şekil/renk başlangıcı olan grubun ALTINA yaz
# - Bilgilendirme YOK
# ==================================================
import re, os, codecs, shutil, urllib.request

HEDEF_DOSYA = "mirti68.m3u"

AKTARIMLAR = [
      {
        "kaynak_url": "https://raw.githubusercontent.com/smtv62/atomspor/refs/heads/main/atom.m3u",
        "kaynak_grup": "Atom-Panel",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Atom",
    },
]

def grup_bul(rec):
    for l in rec:
        if l.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', l)
            return m.group(1) if m else ""
    return ""

def kanal_adi(rec):
    for l in rec:
        if l.startswith("#EXTINF:"):
            return l.split(",", 1)[-1].strip()
    return ""

def extinf_bul(rec):
    for l in rec:
        if l.startswith("#EXTINF:"):
            return l
    return ""

def temiz_isim(ad):
    """HAYSİYET - 1. Bölüm - 2026-11-17 -> HAYSİYET gibi karşılaştırma için sadeleştir"""
    ad = ad.lower().strip()
    # bölüm / tarih kısmını at
    ad = re.split(r'\s*-\s*\d+\.?\s*bölüm', ad)[0]
    ad = re.split(r'\s*-\s*\d{4}-\d{2}-\d{2}', ad)[0]
    return ad.strip()

def grup_baslangici(grup_adi):
    m = re.match(r'^\s*(\S+\s*◆)', grup_adi.strip())
    if m:
        return m.group(1).strip()
    return grup_adi.strip().split()[0] if grup_adi.strip() else ""

def oku_m3u(path_or_url):
    if path_or_url.startswith("http"):
        req = urllib.request.Request(path_or_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            metin = r.read().decode("utf-8-sig", errors="ignore")
    else:
        if not os.path.exists(path_or_url):
            print(f"  [!] Kaynak bulunamadı: {path_or_url}")
            return [], [], "\n", "utf-8"
        metin = open(path_or_url, "rb").read().decode("utf-8-sig", errors="ignore")
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()
    ilk = next((i for i, s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik = satirlar[:ilk]
    govde = satirlar[ilk:]
    records, cur = [], []
    for line in govde:
        if line.startswith("#EXTINF:") and cur:
            records.append(cur); cur = []
        cur.append(line)
    if cur: records.append(cur)
    return baslik, records, newline, "utf-8"

def hedefe_uyarla(rec, cfg):
    extinf = extinf_bul(rec)
    url = rec[-1] if rec else ""
    ad = kanal_adi(rec)

    # 1. Hedef grup
    if 'group-title="' in extinf:
        extinf = re.sub(r'group-title="[^"]*"', f'group-title="{cfg["hedef_grup"]}"', extinf)
    else:
        extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{cfg["hedef_grup"]}"')

    # 2. Hedef logo
    if cfg.get("hedef_logo"):
        if 'tvg-logo="' in extinf:
            extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{cfg["hedef_logo"]}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{cfg["hedef_logo"]}"')

    # 3. ek_kod - İKİ TİPİ DE DESTEKLER
    ek = (cfg.get("ek_kod") or "").strip()
    if ek:
        if "=" in ek:
            # Tip 1: EXTINF özelliği -> #EXTINF:-1 tvg-id="..." gibi
            # Zaten varsa tekrar ekleme
            anahtar = ek.split("=")[0].strip()
            if anahtar not in extinf:
                extinf = extinf.replace("#EXTINF:-1", f"#EXTINF:-1 {ek}")
        else:
            # Tip 2: İSİM SONUNA ekle -> "HAYSİYET" -> "HAYSİYET ⭕ Atom"
            # Zaten sonda varsa tekrar ekleme
            if not ad.endswith(ek) and ek not in ad:
                yeni_ad = f"{ad} {ek}"
                # tvg-name="..." içini de değiştir
                extinf = re.sub(
                    r'tvg-name="[^"]*"',
                    f'tvg-name="{yeni_ad}"',
                    extinf,
                    count=1
                )
                # virgülden sonraki görünen adı da değiştir
                # #EXTINF:-1 ...,GÖRÜNEN AD
                extinf = re.sub(
                    r',([^,]*)$',
                    f',{yeni_ad}',
                    extinf,
                    count=1
                )
    return [extinf, url]

def main():
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok!")
        return

    baslik, hedef_records, newline, enc = oku_m3u(HEDEF_DOSYA)

    for cfg in AKTARIMLAR:
        print(f"\n[*] {cfg['kaynak_url']} | aranacak='{cfg['aranacak']}' -> hedef='{cfg['hedef_grup']}'")
        _, kaynak_records, _, _ = oku_m3u(cfg["kaynak_url"])
        aranacak = cfg.get("aranacak", "").strip().lower()
        kaynak_grup = cfg.get("kaynak_grup", "").strip()

        secilen = []
        for r in kaynak_records:
            if kaynak_grup and grup_bul(r) != kaynak_grup:
                continue
            if aranacak:
                ad = kanal_adi(r).lower()
                url = " ".join(r).lower()
                if aranacak not in ad and aranacak not in url:
                    continue
            if "bilgilendirme" in kanal_adi(r).lower():
                continue
            secilen.append(hedefe_uyarla(r, cfg))

        if not secilen:
            print(f"  [!] Kayıt yok, bu grup atlandı, hedefe DOKUNULMADI")
            continue

        print(f"  [+] {len(secilen)} kayıt seçildi")
        hedef_grup = cfg["hedef_grup"]

        # 1. Hedefte AYNI İSİMDE grup var mı? -> BİRLEŞTİR, SİLME
        ayni_indexler = [i for i, r in enumerate(hedef_records) if grup_bul(r) == hedef_grup]
        if ayni_indexler:
            # Gelen kayıtların isimleri
            gelen_isimler = {temiz_isim(kanal_adi(r)): r for r in secilen}
            yeni_grup_kayitlari = []
            # Eski grup kayıtlarını gez
            for idx in ayni_indexler:
                eski = hedef_records[idx]
                eski_isim = temiz_isim(kanal_adi(eski))
                if eski_isim in gelen_isimler:
                    # Aynı isim varsa YENİSİ ile değiştir (link güncellendi)
                    yeni_grup_kayitlari.append(gelen_isimler.pop(eski_isim))
                    print(f"    [GÜNCELLENDİ] {kanal_adi(eski)}")
                else:
                    # Aynı isim yoksa ESKİSİ KALSIN - SİLME
                    yeni_grup_kayitlari.append(eski)
                    print(f"    [KORUNDU] {kanal_adi(eski)}")
            # Tamamen yeni isimler varsa sona ekle
            for isim, rec in gelen_isimler.items():
                yeni_grup_kayitlari.append(rec)
                print(f"    [EKLENDİ] {kanal_adi(rec)}")

            # Grubu eski yerinde yeniden kur
            ilk = min(ayni_indexler)
            digerleri = [r for r in hedef_records if grup_bul(r) != hedef_grup]
            onceki = sum(1 for r in hedef_records[:ilk] if grup_bul(r) != hedef_grup)
            hedef_records = digerleri[:onceki] + yeni_grup_kayitlari + digerleri[onceki:]
            print(f"  [YAZILDI] Aynı grup bulundu, birleştirildi: {hedef_grup}")
            continue

        # 2. Aynı isim yoksa, aynı şekil/renk başlangıcı olan grubun ALTINA ekle
        hedef_baslangic = grup_baslangici(hedef_grup)
        benzer = [i for i, r in enumerate(hedef_records) if grup_baslangici(grup_bul(r)) == hedef_baslangic and grup_bul(r)]
        if benzer:
            son_benzer = max(benzer)
            hedef_records = hedef_records[:son_benzer+1] + secilen + hedef_records[son_benzer+1:]
            print(f"  [YAZILDI] Aynı isim yok, '{hedef_baslangic}' grubunun altına eklendi")
            continue

        # 3. Hiç benzer yoksa en sona ekle
        hedef_records = hedef_records + secilen
        print(f"  [YAZILDI] Benzer yok, en sona eklendi")

    shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA + ".bak")
    sonuc = list(baslik)
    for r in hedef_records:
        sonuc.extend(r)
    with open(HEDEF_DOSYA, "w", encoding=enc, newline="") as f:
        f.write(newline.join(sonuc) + newline)
    print(f"\n[TAMAM] {HEDEF_DOSYA} güncellendi | Grup içi silinmedi, birleştirildi | EPG korundu")

if __name__ == "__main__":
    main()
