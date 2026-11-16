
import os
import re
import tempfile
import requests
from collections import Counter

# ==================================================
# AYARLAR
# ==================================================

INPUT_M3U = "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u"
OUTPUT_M3U = "mirti68.m3u"

WANTED_RAW = [
    "IMDb Top Rated",
    "YERLI FILM",
    "KEMAL SUNAL",
    "KORKU",
    "WESTERN",
    "YeniEklenenler",
    "2026",
    "2025",
    "2023 2024",
    "2021 2022",
    "2019 2020",
    "2017 2018",
    "2015 2016",
    "2013 2014",
    "2011 2012",
    "2001 2010",
]

def norm(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9çğıöşü]+', '', s)
    return s

WANTED = {norm(x): x for x in WANTED_RAW}

EXCLUDED = [
    "【entity-adam sandler¦canonical_name=adam sandler】",
    "clint eastwood",
    "【entity-sylvester stallone¦canonical_name=sylvester stallone】",
    "【entity-jackie chan¦canonical_name=jackie chan】",
    "nicolas cage",
    "【entity-steven seagal¦canonical_name=steven seagal】",
    "jason statham",
    "seri",
    "dizi",
    "series",
    "sezon",
    "season",
    "episode",
    "bölüm",
    "bolum",
    "s01e",
    "s02e",
    "s03e",
]


# ==================================================
# FİLTRELEME
# ==================================================

def is_excluded(text):

    t = " " + re.sub(
        r'[^a-z0-9çğıöşü]+',
        ' ',
        text.lower()
    ) + " "

    for w in EXCLUDED:

        if w in ("s01e", "s02e", "s03e"):

            if w in text.lower().replace(" ", ""):
                return True

        elif f" {w} " in t:
            return True

    return False


# ==================================================
# M3U BAŞLIK VE KANALLARI AYIR
# EPG SATIRLARI KESİNLİKLE KORUNUR
# ==================================================

def read_entries(lines):

    entries = []
    current = []
    header = []

    for line in lines:

        line = line.rstrip("\r\n")

        if line.strip().startswith("#EXTINF:"):

            if current:
                entries.append(current)

            current = [line]

        elif current and line.strip():

            current.append(line)

        elif not current:

            # İLK EXTINF'E KADAR TÜM BAŞLIKLARI KORU
            header.append(line)

    if current:
        entries.append(current)

    return header, entries


# ==================================================
# YAYIN ADRESİ
# ==================================================

def get_stream(entry):

    return next(
        (
            line.strip()
            for line in entry[1:]
            if line.strip().startswith(("http://", "https://"))
        ),
        ""
    )


# ==================================================
# GRUP ADI
# ==================================================

def get_group(entry):

    joined = "\n".join(entry)

    m = re.search(
        r'group-title="([^"]*)"',
        joined,
        re.IGNORECASE | re.DOTALL
    )

    if not m:
        return None

    return re.sub(
        r"\s+",
        " ",
        m.group(1)
    ).strip()


# ==================================================
# FİLM ADI
# ==================================================

def get_name(entry):

    header = "\n".join([
        l for l in entry
        if not l.strip().startswith("http")
    ])

    if "," in header:
        return header.rsplit(",", 1)[-1].strip()

    return ""


# ==================================================
# URL DÜZELTME
# ==================================================

def fix_url(url):

    url = url.strip()

    url = url.replace("?.mp4", "").replace("?ext=.mp4", "")

    if "vixolity.com/vs/" in url and url.endswith(".mp4"):
        url = url[:-4]

    return url


def normalize_url(url):

    url = url.strip()

    url = url.replace("?.mp4", "").replace("?ext=.mp4", "")

    if url.endswith(".mp4"):
        url = url[:-4]

    return url.rstrip("/")


# ==================================================
# GRUP YENİDEN ADLANDIRMA
# ==================================================

def rename_group(entry):

    g = get_group(entry)

    if not g:
        return entry

    clean = WANTED.get(norm(g), g)

    clean = re.sub(
        r"\s+",
        " ",
        clean
    ).strip()

    if "FILM" not in clean.upper():
        clean = f"FILM - {clean}"

    new_group = f"🟪◆ {clean} ⭕"

    joined = "\n".join(entry)

    new_joined = re.sub(
        r'group-title="[^"]*"',
        f'group-title="{new_group}"',
        joined,
        count=1,
        flags=re.DOTALL
    )

    new_joined = re.sub(
        r'\s*tvg-type="[^"]*"',
        '',
        new_joined,
        count=1
    )

    new_joined = re.sub(
        r'#EXTINF:-?\d+',
        '#EXTINF:-1 tvg-type="movie"',
        new_joined,
        count=1
    )

    lines = new_joined.split("\n")

    fixed_lines = []

    for line in lines:

        s = line.strip()

        if s.startswith(("http://", "https://")):
            fixed_lines.append(fix_url(s))

        else:
            fixed_lines.append(line)

    return fixed_lines


# ==================================================
# FİLM KONTROLÜ
# ==================================================

def is_movie(entry):

    if not entry:
        return False

    g = get_group(entry)

    if not g:
        return False

    if norm(g) not in WANTED:
        return False

    if is_excluded(g):
        return False

    if is_excluded(get_name(entry)):
        return False

    return True


# ==================================================
# KAYNAK M3U İNDİR
# ==================================================

def download_m3u(url):

    urls = [
        url,
        "https://cdn.jsdelivr.net/gh/GitLatte/patr0n@site/lists/power-sinema.m3u"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for u in urls:

        try:

            r = requests.get(
                u,
                headers=headers,
                timeout=60
            )

            print(
                f"Indirildi: {u} -> "
                f"status: {r.status_code} "
                f"len: {len(r.text)}"
            )

            if r.status_code == 200 and "#EXTM3U" in r.text[:500]:

                return r.text

        except Exception as e:

            print(f"Indirme hatasi {u}: {e}")

    return None


# ==================================================
# GÜVENLİ DOSYA YAZMA
# ESKİ EPG BAŞLIKLARI AYNEN KORUNUR
# ==================================================

def write_atomic(lines, header=None):

    directory = os.path.dirname(
        os.path.abspath(OUTPUT_M3U)
    ) or "."

    fd, temp_path = tempfile.mkstemp(
        prefix="mirti68_",
        suffix=".m3u",
        dir=directory
    )

    try:

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f:

            # ESKİ EPG VE TÜM BAŞLIK SATIRLARI
            if header:

                for line in header:
                    f.write(line + "\n")

            else:

                f.write("#EXTM3U\n")

            # TÜM KANAL KAYITLARI
            for line in lines:

                f.write(line + "\n")

        # DOSYA BOŞ MU KONTROL ET
        if not os.path.exists(temp_path):
            raise Exception("Geçici dosya oluşturulamadı.")

        if os.path.getsize(temp_path) == 0:
            raise Exception("Geçici dosya boş.")

        # M3U BAŞLIK KONTROLÜ
        with open(
            temp_path,
            "r",
            encoding="utf-8"
        ) as check:

            first_line = check.readline().strip()

            if not first_line.startswith("#EXTM3U"):
                raise Exception("M3U başlık kontrolü başarısız.")

        # ANA DOSYAYI DEĞİŞTİR
        os.replace(temp_path, OUTPUT_M3U)

    except Exception:

        if os.path.exists(temp_path):
            os.remove(temp_path)

        raise


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 55)
    print("       MIRTI68 - POWER SINEMA")
    print("=" * 55)

    # ----------------------------------------------
    # KAYNAK LİSTEYİ OKU
    # ----------------------------------------------

    if INPUT_M3U.startswith(("http://", "https://")):

        text = download_m3u(INPUT_M3U)

        if not text:

            print("[HATA] Kaynak indirilemedi.")
            print("[KORUMA] Ana liste değiştirilmedi.")
            return

        _, source_entries = read_entries(
            text.splitlines()
        )

    else:

        if not os.path.exists(INPUT_M3U):

            print(f"[HATA] {INPUT_M3U} bulunamadı.")
            return

        with open(
            INPUT_M3U,
            "r",
            encoding="utf-8-sig"
        ) as f:

            _, source_entries = read_entries(
                f.read().splitlines()
            )

    if not source_entries:

        print("[HATA] Kaynak listede yayın bulunamadı.")
        print("[KORUMA] Ana liste değiştirilmedi.")
        return

    # ----------------------------------------------
    # KAYNAK GRUP SAYILARI
    # ----------------------------------------------

    found = Counter()

    for e in source_entries:

        g = get_group(e)

        if g:
            found[norm(g)] += 1

    print()
    print("--- KAYNAKTA BULUNAN İSTENEN GRUPLAR ---")

    for k, v in WANTED.items():

        print(f"{v}: {found.get(k, 0)} adet")

    print("----------------------------------------")

    # ----------------------------------------------
    # ESKİ LİSTEYİ OKU
    # ----------------------------------------------

    old_entries = []

    old_header = ["#EXTM3U"]

    migrated = 0

    if os.path.exists(OUTPUT_M3U):

        with open(
            OUTPUT_M3U,
            "r",
            encoding="utf-8-sig"
        ) as f:

            old_header, raw_old_entries = read_entries(
                f.read().splitlines()
            )

        # BOŞ BAŞLIK DURUMUNDA M3U BAŞLIĞI EKLE
        if not old_header:
            old_header = ["#EXTM3U"]

        for e in raw_old_entries:

            if is_movie(e):

                old_entries.append(
                    rename_group(e)
                )

                migrated += 1

            else:

                old_entries.append(e)

    print(
        f"Eski film kaydı yeni formata çevrildi: {migrated}"
    )

    print(
        f"Korunan başlık / EPG satırı: {len(old_header)}"
    )

    # ----------------------------------------------
    # TEKRAR EDEN URL KONTROLÜ
    # ----------------------------------------------

    seen_urls = {
        normalize_url(get_stream(e))
        for e in old_entries
        if get_stream(e)
    }

    # ----------------------------------------------
    # YENİ FİLMLERİ EKLE
    # ----------------------------------------------

    added = []

    filtered = 0

    for entry in source_entries:

        if not get_stream(entry):
            continue

        if not is_movie(entry):

            filtered += 1
            continue

        stream = normalize_url(
            get_stream(entry)
        )

        if stream not in seen_urls:

            seen_urls.add(stream)

            added.append(
                rename_group(entry)
            )

    # ----------------------------------------------
    # SON LİSTEYİ OLUŞTUR
    # ----------------------------------------------

    final_lines = []

    for e in old_entries:

        final_lines.extend(e)

    for e in added:

        final_lines.extend(e)

    # ----------------------------------------------
    # DOSYAYI GÜVENLİ KAYDET
    # ----------------------------------------------

    try:

        write_atomic(
            final_lines,
            old_header
        )

    except Exception as e:

        print("[HATA] Dosya kaydedilemedi:", e)
        print("[KORUMA] Ana liste değiştirilmedi.")
        return

    # ----------------------------------------------
    # SONUÇ
    # ----------------------------------------------

    print()
    print("=" * 55)
    print("       POWER SINEMA GÜNCELLENDİ")
    print("=" * 55)

    print(f"Korunan eski kayıt: {len(old_entries)}")
    print(f"Eski film kaydı dönüştürüldü: {migrated}")
    print(f"Yeni eklenen film: {len(added)}")
    print(f"Filtrelenen / atlanan: {filtered}")
    print(f"Toplam kanal: {len(old_entries) + len(added)}")

    print("----------------------------------------")

    print("EPG BAŞLIKLARI: KORUNDU")
    print("DİĞER GRUPLAR: KORUNDU")
    print("TEKRAR EDEN URL: ENGELLENDİ")
    print("ANA DOSYA:", OUTPUT_M3U)

    print("=" * 55)


# ==================================================
# ÇALIŞTIR
# ==================================================

if __name__ == "__main__":

    main()
