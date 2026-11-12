import os
import re
import requests

# Kaynak adresini 【entity-GitHub¦canonical_name=GitHub】 Secrets üzerinden al
SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8")

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟩◆  beIN SPORTS 📡"
SOURCE_GROUP = "Yerel / 🔴 SPOR"

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

# --- -Atom 🔴 İŞLEMLERİ ---
def make_channel_key(extinf):
    name = get_channel_name(extinf).lower()
    # Karşılaştırırken -A 🔴'yi yok say, yoksa her seferinde yeni sanır
    name = name.replace("🔴", "")
    name = re.sub(r'\s*-?\s*a\s*$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def has_atom_suffix(extinf):
    return get_channel_name(extinf).strip().endswith("🔴")

def add_atom_suffix(extinf):
    if "," not in extinf:
        return extinf
    head, display = extinf.split(",", 1)
    display = display.strip()
    if display.endswith("🔴"):
        return extinf
    return f"{head},{display} -A 🔴"

def main():
    print("=" * 55)
    print("MIRTI68 - BEİNSPORTS")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL 🟩◆  beIN SPORTS 📡 Secret tanımlanmamış.")
        return

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
        extinf = entry[0]

        if get_group(extinf) != SOURCE_GROUP:
            continue

        if len(entry) < 2:
            continue

        stream = next(
            (x for x in entry[1:] if not x.startswith("#")),
            ""
        )

        if not stream.startswith(("http://", "https://")):
            continue

        new_extinf = re.sub(
            r'group-title="[^"]*"',
            f'group-title="{FILM_GROUP}"',
            extinf
        )

        if 'group-title=' not in new_extinf:
            new_extinf = new_extinf.replace(
                "#EXTINF:",
                f'#EXTINF:-1 group-title="{FILM_GROUP}"',
                1
            )

        new_entries.append([new_extinf, stream])

    if not new_entries:
        print("Kaynak grupta geçerli yayın bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    old_lines = []

    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)

    preserved = [
        entry for entry in old_entries
        if get_group(entry[0]) != FILM_GROUP
    ]

    # Eski beIN grubunu al - yeniyi anlamak için lazım
    old_bein_group = [
        entry for entry in old_entries
        if get_group(entry[0]) == FILM_GROUP
    ]

    # Eski kanalları URL ve isim ile tanı
    old_urls = set()
    old_names = set()
    old_atom_names = set()

    for entry in old_bein_group:
        url = next((x for x in entry[1:] if x.startswith(("http://", "https://"))), "")
        if url:
            old_urls.add(url)
        key = make_channel_key(entry[0])
        if key:
            old_names.add(key)
            if has_atom_suffix(entry[0]):
                old_atom_names.add(key)

    # Diğer grupların yayın adreslerini koruyarak
    # yeni kayıtların kendi içinde tekrarlanmasını önle.
    seen_urls = set()
    unique_entries = []

    for entry in new_entries:
        url = entry[1]

        if url not in seen_urls:
            seen_urls.add(url)

            # YENİ Mİ?
            key = make_channel_key(entry[0])
            is_new = url not in old_urls and key not in old_names

            new_extinf = entry[0]

            if is_new:
                # Yeni kanal -> -A 🔴 ekle
                new_extinf = add_atom_suffix(new_extinf)
            elif key in old_atom_names:
                # Eskiden yeni diye işaretlenmişse koru
                new_extinf = add_atom_suffix(new_extinf)

            unique_entries.append([new_extinf, url])

    # Ana listeyi yeniden oluştur
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for entry in preserved + unique_entries:
            for line in entry:
                f.write(line + "\n")

    print("GÜNCELLEME TAMAMLANDI")
    print("Yeni kayıt:", len(unique_entries))
    print("Korunan eski kayıt:", len(preserved))
    print("Ana dosya:", M3U_FILE)

if __name__ == "__main__":
    main()
