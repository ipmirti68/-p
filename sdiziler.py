
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
# ==================================================

M3U_FILE = "mirti68.m3u"
YAML_FILE = "sdiziler.yaml"

TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}


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
                v = v.strip('"').strip("'")

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

    return response.text.splitlines()


# ==================================================
# ESKİ GRUPLARI TEMİZLEME
# ==================================================

def clean_old_groups(lines, target_groups):

    out = []
    skip = False

    for line in lines:

        if line.startswith("#EXTINF"):

            g = get_group(line)

            skip = g in target_groups

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
                url = next_line
                break

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
    print("MIRTI68 - DİZİLER YAML TOPLU ÇEKİM + LOGO")
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

    target_groups = set(
        s["group"] for s in series_list
    )

    lines = clean_old_groups(lines, target_groups)

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
    
