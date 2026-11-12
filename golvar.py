import os
import re
import requests
import tempfile

# ==========================================
# MIRTI68 - ATOM 【entity-beIN SPORTS¦canonical_name=beIN SPORTS】 GÜNCELLEME
# ==========================================

SOURCE_M3U_URL = os.environ.get(
    "SOURCE_M3U_URL",
    "https://raw.githubusercontent.com/smtv62/golvar/refs/heads/main/golvar.m3u"
)

M3U_FILE = "mirti68.m3u"

FILM_GROUP = "🟩◆  beIN SPORTS 🖥"

# ==========================================
# M3U YARDIMCI FONKSİYONLARI
# ==========================================

def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""

def get_channel_name(line):
    if "," in line:
        return line.split(",", 1)[1].strip()
    return ""

def read_entries(lines):
    entries = []
    current = []

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF:"):

            if current:
                entries.append(current)

            current = [line]

        elif current and line:
            current.append(line)

    if current:
        entries.append(current)

    return entries

def get_stream(entry):
    return next(
        (
            line.strip()
            for line in entry[1:]
            if line.startswith(("http://", "https://"))
        ),
        ""
    )

def make_channel_key(extinf):

    name = get_channel_name(extinf).lower()

    # 🔴 işaretini karşılaştırmadan çıkar, yoksa her seferinde yeni sanır
    name = name.replace("🔴", "")

    name = re.sub(r'\s+', ' ', name)

    return name.strip()

def has_red_dot(extinf):
    return get_channel_name(extinf).strip().startswith("🔴")

def add_red_dot(extinf):
    if "," not in extinf:
        return extinf

    head, display = extinf.split(",", 1)
    display = display.strip()

    if display.endswith("🔴"):
        return extinf

    return f"{head},{display} -Gol 🔴"

def update_group(extinf):

    extinf = re.sub(
        r'group-title="[^"]*"',
        lambda m: f'group-title="{FILM_GROUP}"',
        extinf
    )

    if "group-title=" not in extinf:

        extinf = extinf.replace(
            "#EXTINF:",
            f'#EXTINF:-1 group-title="{FILM_GROUP}"',
            1
        )

    return extinf

# ==========================================
# ANA İŞLEM
# ==========================================

def main():

    print("=" * 55)
    print("MIRTI68 - GOLVAR 【entity-beIN SPORTS¦canonical_name=beIN SPORTS】 BOT")
    print("=" * 55)

    # Kaynak listeyi indir
    try:

        response = requests.get(
            SOURCE_M3U_URL,
            timeout=40,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()
        response.encoding = "utf-8"

    except requests.RequestException as e:

        print("Kaynak liste okunamadı:", e)
        print("Ana liste değiştirilmedi.")
        return

    # Kaynak kayıtlarını oku
    source_entries = read_entries(
        response.text.splitlines()
    )

    new_entries = []

    # ==========================================
    # SADECE 【entity-beIN SPORTS¦canonical_name=beIN SPORTS】 KANALLARINI AL
    # ==========================================

    for entry in source_entries:

        if not entry:
            continue

        extinf = entry[0]

        channel_name = get_channel_name(
            extinf
        ).lower()

        # Yalnızca beIN Sports kanal isimleri
        if "bein sports" not in channel_name:
            continue

        stream = get_stream(entry)

        if not stream:
            continue

        new_extinf = update_group(extinf)

        new_entries.append([
            new_extinf,
            stream
        ])

    if not new_entries:

        print("beIN Sports kanalı bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    print("Kaynak beIN Sports:", len(new_entries))

    # ==========================================
    # MEVCUT ANA LİSTEYİ OKU
    # ==========================================

    if os.path.exists(M3U_FILE):

        with open(
            M3U_FILE,
            "r",
            encoding="utf-8-sig"
        ) as f:

            old_lines = f.read().splitlines()

    else:

        old_lines = ["#EXTM3U"]

    old_entries = read_entries(old_lines)

    # Hedef gruptaki mevcut kanallar
    existing_group = [
        entry
        for entry in old_entries
        if get_group(entry[0]) == FILM_GROUP
    ]

    # ==========================================
    # ESKİ KANALLARI KORU
    # ==========================================

    
    # ==========================================
    # KANALLARI URL ÜZERİNDEN EŞLEŞTİR
    # ==========================================

    
    # ==========================================
    # URL + KANAL ADI İLE AKILLI GÜNCELLEME
    # ==========================================

    channel_map = {}
    name_map = {}

    # Eski kanalları koru
    for entry in existing_group:

        url = get_stream(entry)
        name = make_channel_key(entry[0])

        if not url:
            continue

        if url not in channel_map:
            channel_map[url] = entry

        if name and name not in name_map:
            name_map[name] = url

    added_count = 0
    updated_count = 0

    for entry in new_entries:

        url = get_stream(entry)
        name = make_channel_key(entry[0])

        if not url:
            continue

        # Aynı URL zaten varsa tekrar ekleme
        if url in channel_map:
            continue

        # Aynı isim farklı URL ise eski yayını güncelle
        if name in name_map:

            old_url = name_map[name]

            if old_url in channel_map:

                old_entry = channel_map.pop(old_url)

                # Eski kanalda 🔴 varsa, güncellenen kanalda da koru
                new_entry = entry
                if has_red_dot(old_entry[0]):
                    new_entry = [add_red_dot(entry[0]), entry[1]]

                channel_map[url] = new_entry

                name_map[name] = url

                updated_count += 1

        else:

            # Yeni isim ve yeni URL -> 🔴 ekle
            new_entry = [add_red_dot(entry[0]), entry[1]]

            channel_map[url] = new_entry
            name_map[name] = url

            added_count += 1

    updated_group = list(channel_map.values())
    # ==========================================
    # GRUBUN ESKİ YERİNİ KORU
    # ==========================================

    final_lines = []
    inserted = False

    i = 0

    while i < len(old_lines):

        line = old_lines[i].strip()

        if line.startswith("#EXTINF:"):

            entry = [line]

            i += 1

            while i < len(old_lines):

                next_line = old_lines[i].strip()

                if next_line.startswith("#EXTINF:"):
                    break

                if next_line:
                    entry.append(next_line)

                i += 1

            if get_group(entry[0]) == FILM_GROUP:

                if not inserted:

                    for new_entry in updated_group:
                        final_lines.extend(new_entry)

                    inserted = True

            else:

                final_lines.extend(entry)

        else:

            if line and line != "#EXTM3U":
                final_lines.append(line)

            i += 1

    # Hedef grup henüz yoksa listenin sonuna ekle
    if not inserted:

        for entry in updated_group:
            final_lines.extend(entry)

    # ==========================================
    # DOSYAYI GÜVENLİ KAYDET
    # ==========================================

    directory = os.path.dirname(
        os.path.abspath(M3U_FILE)
    )

    fd, temp_path = tempfile.mkstemp(
        prefix="mirti68_",
        suffix=".m3u",
        dir=directory
    )

    try:

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as f:

            f.write("#EXTM3U\n")

            for line in final_lines:
                f.write(line + "\n")

        os.replace(temp_path, M3U_FILE)

    except Exception:

        if os.path.exists(temp_path):
            os.remove(temp_path)

        raise

    # ==========================================
    # SONUÇ
    # ==========================================

    print("=" * 55)
    print("MIRTI68 GÜNCELLEME TAMAMLANDI")
    print("=" * 55)

    print("Kaynak beIN Sports:", len(new_entries))
    print("Yeni kanal:", added_count)
    print("Güncellenen kanal:", updated_count)
    print("Son grup kanal:", len(updated_group))
    print("Grup yeri korundu:", FILM_GROUP)
    print("Ana liste:", M3U_FILE)

    print("=" * 55)

if __name__ == "__main__":
    main()
