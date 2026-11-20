# ==================================================
# MIRTI68 - TEK AKTARICI - KOMPLE DÜZELTİLMİŞ
# HATALI URL ATLA - ÇALIŞANLARA DEVAM ET
#
# - 403 / 404 / 500 hatalarında durmaz
# - Zaman aşımında durmaz
# - Boş kaynakları atlar
# - Aynı isimli grupları birleştirir
# - Eski kanalları korur
# - Aynı isimli kanalları yeni linkle günceller
# - Yeni kanalları ekler
# - Benzer renk grubunun altına ekler
# - EPG ve diğer EXTINF bilgilerini korur
# - İşlem sonunda yedek oluşturur
# - Grup ismi esnek eşleşir (büyük/küçük, boşluk, | farkı önemsemez)
# ==================================================

import re
import os
import shutil
import urllib.request
import urllib.error
import socket

HEDEF_DOSYA = "mirti68.m3u"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

TIMEOUT = 30

AKTARIMLAR = [


     {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/livetv/dc73a3a52d0d5be4ba926d7b40a759fb9d5777a3/tv247tr.m3u",
        "kaynak_grup": "Spor-Avva",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Avva",
    },

    
    {
        "kaynak_url": "https://raw.githubusercontent.com/smtv62/atomspor/refs/heads/main/atom.m3u",
        "kaynak_grup": "Atom-Panel",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Atom",
    },

    {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | ULUSAL",
        "aranacak": "",
        "hedef_grup": "🟨◆ ULUSAL ᴴᴰ⁺ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/mzabidin80/OTT_Navigator_Indonesia_Korea_China_Movies.m3u/refs/heads/main/OTT_Navigator_V2_Indonesia_Korea_China_Movies_Knowledge.m3u",
        "kaynak_grup": "",
        "aranacak": "Korea",
        "hedef_grup": "🟨◆ YABANCI 🇰🇷⭕",
        "hedef_logo": "https://upload.wikimedia.org/wikipedia/commons/0/09/Flag_of_South_Korea.svg?utm_source=tr.wikipedia.org&utm_campaign=index&utm_content=original",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/mehmetey03/METV/refs/heads/main/mahsun.m3u",
        "kaynak_grup": "",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

      
    {
        "kaynak_url": "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "Diziler | Prison Break | Prison Break",
        "aranacak": "",
        "hedef_grup": "🟪◆ DİZİLER - PRİSON BREAK ⭕",
        "hedef_logo": "",
        "ek_kod": "",
    },

    {
        "kaynak_url": "http://190502.tomtv.eu:80/get.php?username=MustafaozdemR7808&password=z189b8mv2r&type=m3u_plus&output=ts",
        "kaynak_grup": "SONVIZYON FILMLER",
        "aranacak": "",
        "hedef_grup": "🟪◆ GÜNCEL FİLİMLER ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/Adnan4161/TvDizi/refs/heads/main/Tv%20Dizi.m3u",
        "kaynak_grup": "SONVIZYON FILMLER",
        "aranacak": "",
        "hedef_grup": "🟪◆ GÜNCEL DİZİLER ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | 7/24 DIZI",
        "aranacak": "",
        "hedef_grup": "🟪◆  7/24 DİZİ 📺⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url":  "https://tinyurl.com/24lt9aqs",
        "kaynak_grup": "",
        "aranacak": "",
        "hedef_grup": "🟪◆  YABANCI DİZİLER 📺⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "Yerel / 🔴 SPOR",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "0️⃣⭕",
    },

    {
        "kaynak_url": "http://31.43.191.142:8880/get.php?username=191703089055131&password=01703089055686&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | SPORT",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "1️⃣⭕",
    },

    {
        "kaynak_url": "http://ruzgarplayer.site:8080/get.php?username=KH6Rn39q4WpL&password=bnzSVts6Lner&type=m3u_plus&output=tsrd=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "⫸TR SUPER LİG 1⫷",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "2️⃣⭕",
    },

    {
        "kaynak_url": "http://190502.tomtv.eu/get.php?username=GokmenS947&password=5rr53m3b8c&type=m3u_plus&output=ts",
        "kaynak_grup": "TR-SPOR",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "3️⃣⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/livetv/dc73a3a52d0d5be4ba926d7b40a759fb9d5777a3/tv247tr.m3u",
        "kaynak_grup": "Spor Vavoo",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "4️⃣⭕",
    },
     
    {
        "kaynak_url": "https://ekmek82.shop/get.php?username=adnan678&password=uBjabktvQP&type=m3u_plus&output=ts",
        "kaynak_grup": "TR • BeIN SPORTS",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "5️⃣⭕",
    },

     {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | TABii",
        "aranacak": "",
        "hedef_grup": "🟪◆  TABİİ DİZİLERİ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },
     
     {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/selcuk/refs/heads/main/5.m3u",
        "kaynak_grup": "",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://avatars.mds.yandex.net/i?id=24b2712ebe4929ec4517dca04f79d71fc5a0ec2e-8178604-images-thumbs&n=13",
        "ek_kod": "⭕SELCUK ",
    },




]

# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def normalize(s):
    """Grup / isim karşılaştırması için normalize et."""
    s = (s or "").lower().strip()
    # Türkçe karakterleri sadeleştir
    tr_map = str.maketrans("ıi̇öüçğş", "iiou cgs".replace(" ", ""))  # dikkat: aşağıda manuel yapıyoruz
    # Daha güvenli manuel çevrim:
    cevir = {
        "ı": "i", "İ": "i", "i": "i",
        "ö": "o", "Ö": "o",
        "ü": "u", "Ü": "u",
        "ç": "c", "Ç": "c",
        "ğ": "g", "Ğ": "g",
        "ş": "s", "Ş": "s",
    }
    s = "".join(cevir.get(c, c) for c in s)
    s = s.replace("|", " ").replace("-", " ").replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

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
    ad = (ad or "").lower().strip()
    for son_ek in ["⭕ atom", "⭕", "atom"]:
        if ad.endswith(son_ek):
            ad = ad[:-len(son_ek)].strip()
    ad = re.split(r'\s*-\s*\d+\.?\s*bölüm', ad)[0]
    ad = re.split(r'\s*-\s*\d+\.?\s*bolum', ad)[0]
    ad = re.split(r'\s*-\s*\d{4}-\d{2}-\d{2}', ad)[0]
    return ad.strip().rstrip("-").strip()

def grup_baslangici(grup_adi):
    """Örn: 🟨◆ ULUSAL -> 🟨◆  |  🟪◆ DİZİLER -> 🟪◆"""
    g = (grup_adi or "").strip()
    if not g:
        return ""
    # İlk 2 karakter genelde renk + ◆ oluyor: 🟨◆ / 🟪◆
    # Emoji 1 karakter sayılmayabilir, bu yüzden ◆'ya kadar al
    if "◆" in g:
        idx = g.find("◆")
        return g[:idx + 1].strip()
    # ◆ yoksa ilk kelime
    return g.split()[0] if g.split() else ""

def grup_eslesiyor_mu(kaynak_grup, hedef_kaynak_grup):
    """Esnek eşleşme: birebir değil, içinde geçiyor mu?"""
    if not hedef_kaynak_grup:
        return True
    n_kaynak = normalize(kaynak_grup)
    n_hedef = normalize(hedef_kaynak_grup)
    if not n_kaynak:
        return False
    # İki yönlü kontrol: biri diğerinin içindeyse kabul et
    return n_hedef in n_kaynak or n_kaynak in n_hedef

# ==================================================
# M3U OKUMA
# ==================================================

def oku_m3u(path_or_url):
    if path_or_url.startswith("http"):
        req = urllib.request.Request(
            path_or_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
                "Connection": "close",
            }
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            veri = r.read()
        metin = veri.decode("utf-8-sig", errors="ignore")
    else:
        if not os.path.exists(path_or_url):
            raise FileNotFoundError(path_or_url)
        with open(path_or_url, "rb") as f:
            metin = f.read().decode("utf-8-sig", errors="ignore")

    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()
    ilk = next(
        (i for i, s in enumerate(satirlar) if s.startswith("#EXTINF:")),
        len(satirlar)
    )
    baslik = satirlar[:ilk]
    govde = satirlar[ilk:]
    records = []
    cur = []
    for line in govde:
        if line.startswith("#EXTINF:") and cur:
            records.append(cur)
            cur = []
        cur.append(line)
    if cur:
        records.append(cur)
    return baslik, records, newline, "utf-8"

# ==================================================
# KAYIT DÜZENLEME
# ==================================================

def hedefe_uyarla(rec, cfg):
    yeni_rec = list(rec)
    extinf_index = next(
        (i for i, x in enumerate(yeni_rec) if x.startswith("#EXTINF:")),
        None
    )
    if extinf_index is None:
        return yeni_rec
    extinf = yeni_rec[extinf_index]
    ad = extinf.split(",", 1)[-1].strip()
    hedef_grup = cfg["hedef_grup"]

    # HEDEF GRUP
    if 'group-title="' in extinf:
        extinf = re.sub(
            r'group-title="[^"]*"',
            lambda m: f'group-title="{hedef_grup}"',
            extinf,
            count=1
        )
    else:
        extinf = re.sub(
            r'(#EXTINF:-?\d+)',
            lambda m: m.group(1) + f' group-title="{hedef_grup}"',
            extinf,
            count=1
        )

    # HEDEF LOGO
    logo = cfg.get("hedef_logo", "")
    if logo:
        if 'tvg-logo="' in extinf:
            extinf = re.sub(
                r'tvg-logo="[^"]*"',
                lambda m: f'tvg-logo="{logo}"',
                extinf,
                count=1
            )
        else:
            extinf = re.sub(
                r'(#EXTINF:-?\d+)',
                lambda m: m.group(1) + f' tvg-logo="{logo}"',
                extinf,
                count=1
            )

    # EK KOD
    ek = (cfg.get("ek_kod") or "").strip()
    if ek:
        if "=" in ek:
            anahtar = ek.split("=")[0].strip()
            if anahtar not in extinf:
                extinf = re.sub(
                    r'(#EXTINF:-?\d+)',
                    lambda m: m.group(1) + f' {ek}',
                    extinf,
                    count=1
                )
        else:
            if not ad.endswith(ek) and ek not in ad:
                yeni_ad = f"{ad} {ek}"
                if 'tvg-name="' in extinf:
                    extinf = re.sub(
                        r'tvg-name="[^"]*"',
                        lambda m: f'tvg-name="{yeni_ad}"',
                        extinf,
                        count=1
                    )
                extinf = extinf.rsplit(",", 1)[0] + "," + yeni_ad

    yeni_rec[extinf_index] = extinf
    return yeni_rec

# ==================================================
# KAYNAK FİLTRELEME
# ==================================================

def kaynak_sec(kaynak_records, cfg):
    aranacak = cfg.get("aranacak", "").strip().lower()
    kaynak_grup = cfg.get("kaynak_grup", "").strip()
    secilen = []
    for r in kaynak_records:
        g = grup_bul(r)
        # DÜZELTME: birebir yerine esnek eşleşme
        if kaynak_grup and not grup_eslesiyor_mu(g, kaynak_grup):
            continue
        if aranacak:
            ad = kanal_adi(r).lower()
            url = " ".join(r).lower()
            # aranacak için de normalize + esnek bak
            if normalize(aranacak) not in normalize(ad) and normalize(aranacak) not in normalize(url):
                # Eski davranışa da bak (Korea -> korea gibi)
                if aranacak not in ad and aranacak not in url:
                    continue
        if "bilgilendirme" in kanal_adi(r).lower():
            continue
        secilen.append(hedefe_uyarla(r, cfg))
    return secilen

# ==================================================
# GRUP BİRLEŞTİRME
# ==================================================

def grubu_birlestir(hedef_records, secilen, hedef_grup):
    gelen = {}
    for r in secilen:
        isim = temiz_isim(kanal_adi(r))
        if isim:
            gelen[isim] = r
    yeni_kayitlar = []
    gorulen = set()
    ilk = None
    son = None
    for r in hedef_records:
        if grup_bul(r) != hedef_grup:
            yeni_kayitlar.append(r)
            continue
        if ilk is None:
            ilk = len(yeni_kayitlar)
        isim = temiz_isim(kanal_adi(r))
        if isim in gelen:
            yeni_kayitlar.append(gelen[isim])
            gorulen.add(isim)
            print(f"    [REVİZE] {kanal_adi(r)}")
        else:
            yeni_kayitlar.append(r)
            print(f"    [KORUNDU] {kanal_adi(r)}")
        son = len(yeni_kayitlar)
    eklenecek = []
    for isim, rec in gelen.items():
        if isim not in gorulen:
            eklenecek.append(rec)
            print(f"    [EKLENDİ] {kanal_adi(rec)}")
    if eklenecek:
        if son is not None:
            yeni_kayitlar[son:son] = eklenecek
        else:
            yeni_kayitlar.extend(eklenecek)
    return yeni_kayitlar

def benzer_grubun_bitisini_bul(hedef_records, hedef_baslangic):
    """Benzer renk grubunun bittiği indexi bul. Dağınık gruplarda en son benzeri bulur."""
    benzer_indexler = [
        i for i, r in enumerate(hedef_records)
        if grup_baslangici(grup_bul(r)) == hedef_baslangic and grup_bul(r)
    ]
    if not benzer_indexler:
        return None
    # En son benzer grubun indexi
    son_benzer = max(benzer_indexler)
    # O gruptan sonra aynı prefix devam ediyorsa ilerle, yoksa orada bitir
    # Basit ve güvenli: en son benzer kaydın hemen sonrası
    return son_benzer

# ==================================================
# ANA İŞLEM
# ==================================================

def main():
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} bulunamadı!")
        return

    print("\n====================================")
    print(" MIRTI68 - TEK AKTARICI BAŞLADI")
    print(" HATALI URL ATLANACAK")
    print("====================================")

    try:
        baslik, hedef_records, newline, enc = oku_m3u(HEDEF_DOSYA)
    except Exception as hata:
        print(f"[HATA] Hedef dosya okunamadı: {hata}")
        return

    basarili = 0
    hatali = 0
    eklenen_toplam = 0

    for sira, cfg in enumerate(AKTARIMLAR, 1):
        url = cfg["kaynak_url"]
        print(f"\n[{sira}/{len(AKTARIMLAR)}] KAYNAK:")
        print(url.split("?")[0])
        print(f"HEDEF GRUP: {cfg['hedef_grup']}")
        if cfg.get("kaynak_grup"):
            print(f"ARANAN KAYNAK GRUP: {cfg['kaynak_grup']}")

        try:
            _, kaynak_records, _, _ = oku_m3u(url)
        except urllib.error.HTTPError as hata:
            hatali += 1
            print(f"  [ATLANDI] HTTP {hata.code}")
            print("  [DEVAM] Sonraki kaynağa geçiliyor.")
            continue
        except urllib.error.URLError as hata:
            hatali += 1
            print(f"  [ATLANDI] Bağlantı hatası: {hata.reason}")
            print("  [DEVAM] Sonraki kaynağa geçiliyor.")
            continue
        except (TimeoutError, socket.timeout) as hata:
            hatali += 1
            print(f"  [ATLANDI] Zaman aşımı: {hata}")
            continue
        except Exception as hata:
            hatali += 1
            print(f"  [ATLANDI] {type(hata).__name__}: {hata}")
            continue

        if not kaynak_records:
            hatali += 1
            print("  [ATLANDI] Kaynakta M3U kaydı bulunamadı.")
            continue

        # DEBUG: Kaynakta hangi gruplar var?
        if cfg.get("kaynak_grup"):
            kaynak_gruplar = sorted(set(grup_bul(r) for r in kaynak_records if grup_bul(r)))
            print(f"  [DEBUG] Kaynakta {len(kaynak_gruplar)} grup var, ilk 10:")
            for gg in kaynak_gruplar[:10]:
                print(f"    - {gg}")
            # Benzer grup var mı göster
            eslesen = [gg for gg in kaynak_gruplar if grup_eslesiyor_mu(gg, cfg["kaynak_grup"])]
            if eslesen:
                print(f"  [DEBUG] Eşleşen kaynak grupları: {eslesen}")
            else:
                print(f"  [UYARI] '{cfg['kaynak_grup']}' ile eşleşen grup bulunamadı!")

        try:
            secilen = kaynak_sec(kaynak_records, cfg)
        except Exception as hata:
            hatali += 1
            print(f"  [ATLANDI] Filtreleme hatası: {hata}")
            continue

        if not secilen:
            print("  [BOŞ] Uygun kanal bulunamadı.")
            print("  [DEVAM] Hedef gruba dokunulmadı.")
            basarili += 1
            continue

        print(f"  [OKUNDU] {len(secilen)} kanal bulundu.")
        hedef_grup = cfg["hedef_grup"]

        ayni_grup_var = any(
            grup_bul(r) == hedef_grup
            for r in hedef_records
        )

        if ayni_grup_var:
            onceki_sayi = len(hedef_records)
            hedef_records = grubu_birlestir(
                hedef_records,
                secilen,
                hedef_grup
            )
            fark = len(hedef_records) - onceki_sayi
            eklenen_toplam += max(0, fark)
            print(f"  [YAZILDI] Grup birleştirildi: {hedef_grup}")
            basarili += 1
            continue

        # AYNI İSİMLİ GRUP YOKSA BENZER RENK GRUBUNU BUL - DÜZELTİLDİ
        hedef_baslangic = grup_baslangici(hedef_grup)
        print(f"  [DEBUG] Hedef başlangıç: '{hedef_baslangic}'")

        son_benzer_idx = benzer_grubun_bitisini_bul(hedef_records, hedef_baslangic)

        if son_benzer_idx is not None:
            hedef_records = (
                hedef_records[:son_benzer_idx + 1]
                + secilen
                + hedef_records[son_benzer_idx + 1:]
            )
            print(
                f"  [YAZILDI] Benzer grubun altına eklendi: "
                f"{hedef_baslangic} (son benzer: {grup_bul(hedef_records[son_benzer_idx]) if son_benzer_idx < len(hedef_records) else ''})"
            )
        else:
            hedef_records.extend(secilen)
            print("  [YAZILDI] Yeni grup en sona eklendi.")

        eklenen_toplam += len(secilen)
        basarili += 1

    # ==================================================
    # SONUÇ DOSYASINI KAYDET
    # ==================================================

    print("\n====================================")
    print(" MIRTI68 - DOSYA KAYDEDİLİYOR")
    print("====================================")

    try:
        shutil.copy2(
            HEDEF_DOSYA,
            HEDEF_DOSYA + ".bak"
        )
        print("[YEDEK] mirti68.m3u.bak oluşturuldu.")
    except Exception as hata:
        print(f"[UYARI] Yedek oluşturulamadı: {hata}")

    sonuc = list(baslik)
    for r in hedef_records:
        sonuc.extend(r)

    try:
        with open(
            HEDEF_DOSYA,
            "w",
            encoding=enc,
            newline=""
        ) as f:
            f.write(newline.join(sonuc) + newline)
    except Exception as hata:
        print(f"[HATA] Dosya yazılamadı: {hata}")
        return

    print("\n====================================")
    print(" MIRTI68 - AKTARIM TAMAMLANDI")
    print("====================================")
    print(f"[BAŞARILI] {basarili}")
    print(f"[HATALI / ATLANAN] {hatali}")
    print(f"[EKLENEN KAYIT] {eklenen_toplam}")
    print(f"[TOPLAM KANAL] {len(hedef_records)}")
    print(f"[DOSYA] {HEDEF_DOSYA}")
    print("====================================")
    print("[TAMAM] ÇALIŞAN KAYNAKLAR AKTARILDI")
    print("[TAMAM] Hatalı URL'ler işlemi durdurmadı")
    print("[TAMAM] Eski grup kayıtları korundu")
    print("====================================")

if __name__ == "__main__":
    main()
