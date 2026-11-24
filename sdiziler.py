import os
import re
import shutil
import requests

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ==================================================
# MIRTI68 - DİZİLER YAML TOPLU ÇEKİM + LOGO
# YAMALI VERSİYON - Bölünmüş EXTINF düzeltmeli
# ==================================================

M3U_FILE = "mirti68.m3u"
YAML_FILE = "sdiziler.yaml"

TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}

# ==================================================
# YENİ - BOZUK M3U SATIRLARINI BİRLEŞTİRME
# ==================================================

def normalize_m3u_lines(lines):
    """
    Bizimkiler gibi dosyalarda #EXTINF satırı 2 satıra bölünmüş oluyor:
    #EXTINF:-1 ... ,Bizimkiler.3.Bolum.(Horozlar
    Oterken).21.01.1989

    Bu fonksiyon o bölünmüş satırları tekrar tek satır yapar.
    Ayrıca group-title=" \n 2.Sezon" gibi kırılmaları da düzeltir.
    """
    out = []
    buf = ""

    for raw in lines:
        s = raw.strip()
        if not s:
            continue

        # Yeni bir EXTINF başladı
        if s.startswith("#EXTINF"):
            if buf:
                out.append(buf)
            buf = s
            continue

        # Elimizde yarım bir EXTINF var ve gelen satır URL değilse,
        # bu satır EXTINF'in devamıdır.
        if buf:
            # URL mi? http, https, rtmp, rtsp ile başlıyorsa URL'dir
            if re.match(r'^(https?|rtmp|rtsp|ftp)://', s, re.IGNORECASE):
                out.append(buf)
                buf = ""
                out.append(s)
                continue
            # # ile başlayan başka bir tag ise, EXTINF bitmiştir
            if s.startswith("#"):
                out.append(buf)
                buf = ""
                out.append(s)
                continue
            # Değilse devam satırıdır, birleştir
            buf += " " + s
            continue

        out.append(s)

    if buf:
        out.append(buf)

    return out

# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def get_group(line):
    m = re.search(r'group-title="([^"]+)"', line)
    return m.group(1).strip() if m else ""

def get_channel_name(line):
    m = re.search(r',\s*(.*)$', line)
    return m.group(1).strip() if m else ""

def parse_season_episode(name):
    m = re.search(
        r'(\d+)\s*\.\s*Sezon\s*-\s*(\d+)\s*\.\s*Bölüm',
        name,
        re.IGNORECASE
    )
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.search(r'S(\d+)\s*E(\d+)', name, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None, None

def clean_name_for_sort(name):
    """Bizimkiler.21.Bolum.(Aska Vakit yok) gibi isimlerden bölüm no bulmak için"""
    m = re.search(r'(\d+)\s*\.\s*Bolum', name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 9999

# ==================================================
# YAML MANUEL OKUMA
# ==================================================

def load_yaml_manual():
    series = []
    cur = {}
    with open(YAML_FILE, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("- name:"):
                if cur.get("url"):
                    series.append(cur)
                cur = {}
                v = line.split(":", 1)[1].strip()
                v = v.strip('"').strip("'")
                cur["name"] = v
            elif line.startswith("group:"):
                v = line.split(":", 1)[1].strip()
                v = v.strip('"').strip("'")
                cur["group"] = v
            elif line.startswith("logo:"):
                v = line.split(":", 1)[1].strip()
                # logo: "logo: "https://..." gibi bozuk satırları temizle
                v = v.replace('logo:', '').strip()
                v = v.strip('"').strip("'")
                # Eğer içinde hala logo: varsa en sondaki http'den al
                if "http" in v:
                    idx = v.rfind("http")
                    v = v[idx:]
                cur["logo"] = v
            elif line.startswith("url:"):
                v = line.split(":", 1)[1].strip()
                v = v.strip('"').strip("'")
                cur["url"] = v
    if cur.get("url"):
        series.append(cur)
    return series

# ==================================================
# YAML OKUMA
# ==================================================

def load_yaml():
    if HAS_YAML:
        try:
            with open(YAML_FILE, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and data.get("series"):
                return data["series"]
        except Exception as e:
            print(f"[UYARI] YAML parse hatası: {e}")
            print("[BİLGİ] Manuel okuma deneniyor.")
    return load_yaml_manual()

# ==================================================
# M3U KAYNAK OKUMA
# ==================================================

def fetch_m3u(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    # YAMA: Gelen satırları hemen normalize et
    return normalize_m3u_lines(response.text.splitlines())

# ==================================================
# ESKİ GRUPLARI TEMİZLEME - YAMALI
# ==================================================

def clean_old_groups(lines, target_groups, target_names):
    """
    YAMA: Eskiden sadece group-title'a bakıyordu.
    Bizimkiler gibi dosyalarda eski grup 1.Sezon, 2.Sezon vs olduğu için
    ve bazı EXTINF'ler bozuk olduğu için silinemiyordu.
    Artık hem grup adına hem de kanal ismine bakıyor.
    Ayrıca eski dosyadaki bölünmüş satırları da normalize ediyor.
    """
    # Önce gelen listeyi de normalize et ki eski bozuk satırlar tanınsın
    lines = normalize_m3u_lines(lines)
    out = []
    skip = False

    for line in lines:
        if line.startswith("#EXTINF"):
            g = get_group(line)
            ch_name = get_channel_name(line)

            # 1. Grup hedef gruplardaysa sil
            # 2. Kanal ismi hedef dizi ismini içeriyorsa sil (örn: BİZİMKİLER)
            #    Bu, eski 1.Sezon / 2.Sezon gruplarını da yakalar
            should_skip = g in target_groups

            if not should_skip:
                upper_name = ch_name.upper()
                for tname in target_names:
                    # BİZİMKİLER -> BIZIMKILER gibi Türkçe karakter farkı için basit kontrol
                    # İsim içinde geçiyorsa eski kayıttır
                    if tname.upper() in upper_name:
                        should_skip = True
                        break
                    # Bizimkiler.1.Bolum gibi noktasız hali
                    if tname.replace(" ", "").upper() in upper_name.replace(" ", "").replace(".", "").upper():
                        should_skip = True
                        break

            skip = should_skip
            if not skip:
                out.append(line)
        else:
            if skip:
                continue
            out.append(line)

    return out

# ==================================================
# M3U KAYIT OLUŞTURMA + LOGO
# ==================================================

def make_records(src_lines, name, group, logo=""):
    # YAMA: Kaynak zaten normalize edilmiş geliyor ama yine de garantiye al
    src_lines = normalize_m3u_lines(src_lines)

    records = []
    count = 0
    i = 0

    while i < len(src_lines):
        line = src_lines[i].strip()

        if not line.startswith("#EXTINF"):
            i += 1
            continue

        raw_name = get_channel_name(line)

        sezon, bolum = parse_season_episode(raw_name)

        if sezon is not None:
            new_name = f"{name} S{sezon:02d} E{bolum:02d}"
        else:
            # Bizimkiler.21.Bolum... gibi isimlerden bölüm no çıkar
            # Sıralama bozulmasın diye ismi temiz tut
            # Eğer isim boşsa atla
            if not raw_name:
                i += 1
                continue
            new_name = f"{name} - {raw_name}"

        # EXTINF SATIRI + LOGO
        new_inf = (
            f'#EXTINF:-1 '
            f'tvg-name="{new_name}" '
            f'tvg-logo="{logo}" '
            f'group-title="{group}",'
            f'{new_name}'
        )

        # SONRAKİ URL SATIRINI BUL
        url = ""
        j = i + 1
        while j < len(src_lines):
            next_line = src_lines[j].strip()
            if next_line.startswith("#EXTINF"):
                break
            if next_line and not next_line.startswith("#"):
                # URL kontrolü: http ile başlamalı, yoksa bozuk satırdır atla
                if re.match(r'^(https?|rtmp|rtsp|ftp)://', next_line, re.IGNORECASE):
                    url = next_line
                    break
                else:
                    # URL olmayan satır (bölünmüş parça vs) - atla, devam et
                    j += 1
                    continue
            j += 1

        if url:
            records.append(new_inf)
            records.append(url)
            count += 1

        i = j if j > i else i + 1

    return records, count

# ==================================================
# ANA İŞLEM
# ==================================================

def main():
    print("=======================================================")
    print("MIRTI68 - DİZİLER YAML TOPLU ÇEKİM + LOGO - YAMALI")
    print("=======================================================")

    if not os.path.exists(YAML_FILE):
        print(f"[HATA] {YAML_FILE} bulunamadı!")
        return

    if not os.path.exists(M3U_FILE):
        print(f"[HATA] {M3U_FILE} bulunamadı!")
        return

    # YAML OKU
    try:
        series_list = load_yaml()
    except Exception as e:
        print(f"[HATA] YAML okunamadı: {e}")
        return

    if not series_list:
        print("[HATA] YAML içerisinde dizi bulunamadı!")
        return

    # EKSİK ALANLARI KONTROL ET
    series_list = [
        s for s in series_list
        if isinstance(s, dict)
        and s.get("name")
        and s.get("group")
        and s.get("url")
    ]

    if not series_list:
        print("[HATA] Geçerli dizi kaydı bulunamadı!")
        return

    print(f"[BİLGİ] {len(series_list)} dizi bulundu.")

    # HEDEF M3U OKU
    try:
        with open(M3U_FILE, encoding="utf-8-sig") as f:
            lines = [l.rstrip("\r\n") for l in f]
    except Exception as e:
        print(f"[HATA] M3U okunamadı: {e}")
        return

    # YEDEK OLUŞTUR
    try:
        shutil.copy2(
            M3U_FILE,
            M3U_FILE + ".bak"
        )
        print("[YEDEK] mirti68.m3u.bak oluşturuldu.")
    except Exception as e:
        print(f"[UYARI] Yedek oluşturulamadı: {e}")

    # ESKİ DİZİ GRUPLARINI TEMİZLE
    target_groups = set(s["group"] for s in series_list)
    target_names = set(str(s["name"]).strip() for s in series_list)

    # YAMA: Artık isim bazlı da temizliyor, eski 1.Sezon grupları kalmayacak
    lines = clean_old_groups(lines, target_groups, target_names)

    # EXTINF YOKSA BAŞLIK EKLE
    if not lines or not lines[0].strip().startswith("#EXTM3U"):
        lines.insert(0, "#EXTM3U")

    # ==================================================
    # DİZİLERİ TEK TEK ÇEK
    # ==================================================

    basarili = 0
    hatali = 0
    toplam_bolum = 0

    for sira, s in enumerate(series_list, 1):
        name = str(s["name"]).strip()
        group = str(s["group"]).strip()
        url = str(s["url"]).strip()
        logo = str(s.get("logo", "") or "").strip()

        # Logo içindeki bozuk "logo:" kalıntısını temizle
        if "logo:" in logo and "http" in logo:
            logo = logo[logo.rfind("http"):]

        print(f"\n[{sira}/{len(series_list)}] -> {name}")

        if logo:
            print("  [LOGO] Logo adresi mevcut.")
        else:
            print("  [LOGO] Logo adresi boş.")

        try:
            src_lines = fetch_m3u(url)
        except requests.exceptions.HTTPError as e:
            print(f"  [ATLANDI] HTTP hatası: {e}")
            hatali += 1
            continue
        except requests.exceptions.Timeout:
            print("  [ATLANDI] Zaman aşımı.")
            hatali += 1
            continue
        except requests.exceptions.RequestException as e:
            print(f"  [ATLANDI] Bağlantı hatası: {e}")
            hatali += 1
            continue
        except Exception as e:
            print(f"  [ATLANDI] {e}")
            hatali += 1
            continue

        if not src_lines:
            print("  [ATLANDI] Kaynak boş.")
            hatali += 1
            continue

        try:
            records, count = make_records(
                src_lines,
                name,
                group,
                logo
            )
        except Exception as e:
            print(f"  [ATLANDI] Kayıt işleme hatası: {e}")
            hatali += 1
            continue

        if not records:
            print("  [ATLANDI] Bölüm bulunamadı.")
            hatali += 1
            continue

        lines.extend(records)
        toplam_bolum += count
        basarili += 1
        print(f"  [OK] {count} bölüm eklendi.")

    # ==================================================
    # DOSYAYI KAYDET
    # ==================================================

    try:
        with open(
            M3U_FILE,
            "w",
            encoding="utf-8",
            newline=""
        ) as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"\n[HATA] Dosya kaydedilemedi: {e}")
        return

    # ==================================================
    # RAPOR
    # ==================================================

    print("\n=======================================================")
    print("MIRTI68 - İŞLEM TAMAMLANDI")
    print("=======================================================")
    print(f"Başarılı dizi: {basarili}")
    print(f"Atlanan dizi: {hatali}")
    print(f"Eklenen bölüm: {toplam_bolum}")
    print(f"Dosya: {M3U_FILE}")
    print("=======================================================")

if __name__ == "__main__":
    main()
