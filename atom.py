
import os
import re
import requests
import tempfile

# ==========================================
# MIRTI68 - Atom GÜNCELLEME
# ==========================================

SOURCE_M3U_URL = os.environ.get(
    "SOURCE_M3U_URL",
    "https://raw.githubusercontent.com/smtv62/smtv/refs/heads/main/turkce.m3u"
)

M3U_FILE = "mirti68.m3u"

FILM_GROUP = "🖥beINSPORTS"
SOURCE_GROUP = "Atom-Panel"

# Kanal adında bu kelime geçenler de alınacak.
EXTRA_KEYWORDS = ["beIN Sports "]


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
    """
    Kanal kimliği:
    Kanal adını esas alır.
    Büyük/küçük harf ve gereksiz boşlukları önemsemez.
    """
    name = get_channel_name(extinf)
    name = name.lower()
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


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


def main():

    print("=" * 55)
    print("MIRTI68 - ATOM GÜNCELLEME")
    print("=" * 55)

    try:
        response = requests.get(
            SOURCE_M3U_URL,
            timeout=40,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        response.encoding = "utf-8"

    except requests.RequestException as e:
        print("Kaynak okunamadı:", e)
        print("Ana liste değiştirilmedi.")
        return

    source_entries = read_entries(response.text.splitlines())

    new_entries = []

    for entry in source_entries:

        if not entry:
            continue

        extinf = entry[0]
        group = get_group(extinf)
        channel_name = get_channel_name(extinf).lower()

        # Kaynak grup veya Ahmet geçen kanal
        is_source_group = group == SOURCE_GROUP

        is_keyword_channel = any(
            keyword.lower() in channel_name
            for keyword in EXTRA_KEYWORDS
        )

        if "beIN Sports " not in channel_name:
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
        print("Yeni kaynak yayın bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    # ==========================================
    # ESKİ ANA LİSTEYİ OKU
    # ==========================================

    if os.path.exists(M3U_FILE):

        with open(M3U_FILE, "r", encoding="utf-8-sig") as f:
            old_lines = f.read().splitlines()

    else:
        old_lines = []

    old_entries = read_entries(old_lines)

    # Diğer bütün grupları koru.
    preserved = [
        entry for entry in old_entries
        if get_group(entry[0]) != FILM_GROUP
    ]

    # ==========================================
    # MEVCUT GRUPTAKİ KANALLARI GÜNCELLE
    # ==========================================

    existing_group = [
        entry for entry in old_entries
        if get_group(entry[0]) == FILM_GROUP
    ]

    channel_map = {}

    # Önce eski kayıtları yerleştir.
    for entry in existing_group:

        if len(entry) < 2:
            continue

        key = make_channel_key(entry[0])

        if key:
            channel_map[key] = entry

    added_count = 0
    updated_count = 0

    # Yeni kayıtları işle.
    for entry in new_entries:

        key = make_channel_key(entry[0])

        if not key:
            continue

        if key in channel_map:

            old_stream = get_stream(channel_map[key])
            new_stream = get_stream(entry)

            if old_stream != new_stream:

                # Aynı kanal, yeni yayın adresi.
                channel_map[key] = entry
                updated_count += 1

        else:

            # Yeni kanal mevcut gruba eklenir.
            channel_map[key] = entry
            added_count += 1

    final_group = list(channel_map.values())

    # ==========================================
    # ANA M3U DOSYASINI GÜVENLİ YAZ
    # ==========================================

    final_entries = preserved + final_group

    output = ["#EXTM3U"]

    for entry in final_entries:
        output.extend(entry)

    content = "\n".join(output) + "\n"

    directory = os.path.dirname(os.path.abspath(M3U_FILE))

    fd, temp_path = tempfile.mkstemp(
        prefix="mirti68_",
        suffix=".m3u",
        dir=directory
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        os.replace(temp_path, M3U_FILE)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print("=" * 55)
    print("GÜNCELLEME BAŞARILI")
    print("=" * 55)
    print("Kaynak bulunan:", len(new_entries))
    print("Yeni kanal:", added_count)
    print("Yayın adresi güncellenen:", updated_count)
    print("Korunan diğer grup kayıtları:", len(preserved))
    print("Son grup kayıtları:", len(final_group))
    print("Ana dosya:", M3U_FILE)


if __name__ == "__main__":
    main()
