# ==================================================
# MIRTI68 - TEK AKTARICI (Bilgilendirme YOK)
# Kural:
# - Hedefte aynı isimde grup varsa -> ONUN İÇİNE yaz
# - Yoksa aynı şekil/renk başlangıcı olan grubun ALTINA yaz
#   Örn: 🟪◆ ... -> 🟪◆ grubunun altına
#        🟨◆ ... -> 🟨◆ grubunun altına
# ==================================================
import re, os, codecs, shutil, urllib.request

HEDEF_DOSYA = "mirti68.m3u"

# ==================================================
# BURAYI DOLDUR
# kaynak_url:  nereden alınacak? .m3u linki veya yerel dosya
# kaynak_grup: kaynakta hangi grupta arayayım? "" = tümünde ara
# aranacak:    kanal / dizi adı filtresi. "" = hepsini al
# hedef_grup:  ana listede hangi gruba yazılacak?
# hedef_logo:  yazılırken logo değişsin mi? "" = kaynak logosu kalsın
# ek_kod:      EXTINF'e eklenecek ekstra kod. "" = ekleme
# ==================================================
AKTARIMLAR = [
    {
        "kaynak_url": "【entity-atv¦canonical_name=ATV】.m3u",
        "kaynak_grup": "🟪◆  【entity-ATV¦canonical_name=ATV】 DİZİ 📺⭕",
        "aranacak": "",
        "hedef_grup": "🟪◆  【entity-ATV¦canonical_name=ATV】 DİZİ 📺⭕",
        "hedef_logo": "",
        "ek_kod": "",
    },
    {
        "kaynak_url": "【entity-atv¦canonical_name=ATV】.m3u",
        "kaynak_grup": "🟪◆  【entity-ATV¦canonical_name=ATV】 DİZİ 📺⭕",
        "aranacak": "haysiyet",
        "hedef_grup": "🟪◆ HAYSİYET 📺⭕",
        "hedef_logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/haysiyet.png",
        "ek_kod": "",
    },
    {
        "kaynak_url": "https://ornek.com/liste.m3u",
        "kaynak_grup": "",
        "aranacak": "beinsport",
        "hedef_grup": "🟦◆ BEIN SPORT ⭕",
        "hedef_logo": "",
        "ek_kod": "",
    },
]

# ==================================================
# ALTA DOKUNMA
# ==================================================

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

def grup_baslangici(grup_adi):
    """Aynı şekil/renk başlangıcını bul: örn '🟪◆' , '🟨◆' , '🟦◆'"""
    # İlk 2 karakter genelde emoji + ◆ oluyor, boşluğa kadar al
    m = re.match(r'^\s*(\S+\s*◆)', grup_adi.strip())
    if m:
        return m.group(1).strip()
    # ◆ yoksa ilk kelimeyi al
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
    if 'group-title="' in extinf:
        extinf = re.sub(r'group-title="[^"]*"', f'group-title="{cfg["hedef_grup"]}"', extinf)
    else:
        extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{cfg["hedef_grup"]}"')
    if cfg.get("hedef_logo"):
        if 'tvg-logo="' in extinf:
            extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{cfg["hedef_logo"]}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{cfg["hedef_logo"]}"')
    if cfg.get("ek_kod"):
        ek = cfg["ek_kod"].strip()
        if ek and ek.split("=")[0] not in extinf:
            extinf = extinf.replace("#EXTINF:-1", f"#EXTINF:-1 {ek}")
    return [extinf, url]

def main():
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok!")
        return

    baslik, hedef_records, newline, enc = oku_m3u(HEDEF_DOSYA)

    # Her aktarım için ayrı ayrı uygula - biri diğerini bozmasın
    for cfg in AKTARIMLAR:
        print(f"\n[*] {cfg['kaynak_url']} | kaynak_grup='{cfg['kaynak_grup']}' | aranacak='{cfg['aranacak']}' -> hedef='{cfg['hedef_grup']}'")
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
            # BİLGİLENDİRME kayıtlarını alma
            if "bilgilendirme" in kanal_adi(r).lower():
                continue
            secilen.append(hedefe_uyarla(r, cfg))

        if not secilen:
            print(f"  [!] Kayıt yok, bu grup atlandı, hedef bozulmadı")
            continue

        print(f"  [+] {len(secilen)} kayıt seçildi")

        hedef_grup = cfg["hedef_grup"]
        hedef_baslangic = grup_baslangici(hedef_grup)

        # 1. Hedefte AYNI İSİMDE grup var mı?
        ayni_grup_indexleri = [i for i, r in enumerate(hedef_records) if grup_bul(r) == hedef_grup]
        if ayni_grup_indexleri:
            # Aynı gruptaki eski kayıtları sil, yerine yenilerini koy (aynı yere)
            ilk = min(ayni_grup_indexleri)
            # Aynı grup dışındaki kayıtlar
            digerleri = [r for r in hedef_records if grup_bul(r) != hedef_grup]
            # Aynı grubun eski konumunu bul: ondan önce kaç tane diğer kayıt var?
            onceki = sum(1 for r in hedef_records[:ilk] if grup_bul(r) != hedef_grup)
            hedef_records = digerleri[:onceki] + secilen + digerleri[onceki:]
            print(f"  [YAZILDI] Aynı grup bulundu, içine yazıldı: {hedef_grup}")
            continue

        # 2. Aynı isim yoksa, AYNI ŞEKİL/RENK başlangıcı olan grubu bul
        # Örn: hedef 🟪◆ HAYSİYET ise, 🟪◆ ile başlayan son grubun altına yaz
        benzer_indexleri = [i for i, r in enumerate(hedef_records) if grup_baslangici(grup_bul(r)) == hedef_baslangic and grup_bul(r)]
        if benzer_indexleri:
            son_benzer = max(benzer_indexleri)
            hedef_records = hedef_records[:son_benzer+1] + secilen + hedef_records[son_benzer+1:]
            print(f"  [YAZILDI] Aynı isim yok, aynı başlangıç '{hedef_baslangic}' grubunun altına yazıldı")
            continue

        # 3. Hiç benzer de yoksa en sona ekle
        hedef_records = hedef_records + secilen
        print(f"  [YAZILDI] Benzer grup yok, en sona eklendi")

    shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA + ".bak")
    sonuc = list(baslik)
    for r in hedef_records:
        sonuc.extend(r)
    with open(HEDEF_DOSYA, "w", encoding=enc, newline="") as f:
        f.write(newline.join(sonuc) + newline)
    print(f"\n[TAMAM] {HEDEF_DOSYA} güncellendi | Bilgilendirme: YOK | EPG: KORUNDU | Diğer gruplar: KORUNDU")

if __name__ == "__main__":
    main()
