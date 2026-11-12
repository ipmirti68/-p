import os
import re
import requests

# Kaynak adresini GitHub Secrets üzerinden al
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

def get_stream(entry):
    return next(
        (x.strip() for x in entry[1:] if x.strip().startswith(("http://", "https://"))),
        ""
    )

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
    # Karşılaştırırken - 🔴'yi yok say, yoksa her seferinde yeni sanır
    name = name.replace("🔴", "")
    name = re.sub(r'\s*-?\s*atom\s*$', '', name)
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
    return f"{head},{display} - 🔴"

def main():
    print("=" * 55)
    print("MIRTI68 - 【entity-BEİNSPORTS¦canonical_name=beIN】")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL GitHub Secret tanımlanmamış.")
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

    # === MEVCUT LİSTEYİ KORU, SİLME ===
    # old_entries olduğu gibi kalacak, sadece üzerine ilave yapacağız
    final_entries = [list(e) for e in old_entries]

    # Eski beIN kanallarını tanı
    url_to_index = {}
    name_to_index = {}

    for idx, entry in enumerate(final_entries):
        if get_group(entry[0]) != FILM_GROUP:
            continue
        url = get_stream(entry)
        if url:
            url_to_index[url] = idx
        key = make_channel_key(entry[0])
        if key:
            name_to_index[key] = idx

    added = []
    updated = 0

    for entry in new_entries:
        url = entry[1].strip()
        key = make_channel_key(entry[0])

        # 1. Aynı link zaten var -> hiç dokunma
        if url in url_to_index:
            continue

        # 2. Aynı isim var ama link değişmiş -> eski kanalın linkini güncelle, isim aynen kalsın
        if key in name_to_index:
            idx = name_to_index[key]
            old_entry = final_entries[idx]
            # Link satırını bulup değiştir
            for j in range(1, len(old_entry)):
                if old_entry[j].strip().startswith(("http://", "https://")):
                    old_entry[j] = url
                    break
            else:
                old_entry.append(url)
            # URL haritasını güncelle
            url_to_index[url] = idx
            updated += 1
            continue

        # 3. Gerçekten yeni -> - 🔴 ile ilave listesine ekle
        new_extinf = add_atom_suffix(entry[0])
        new_entry = [new_extinf, url]
        added.append(new_entry)
        # Bir daha aynı ismi yeni sanmasın diye haritaya ekle
        name_to_index[key] = -1
        url_to_index[url] = -1

    # Yeni kanalları beIN grubunun sonuna ekle
    if added:
        # beIN grubunun sonuncu olduğu yeri bul
        insert_at = None
        for idx in range(len(final_entries) - 1, -1, -1):
            if get_group(final_entries[idx][0]) == FILM_GROUP:
                insert_at = idx + 1
                break

        if insert_at is None:
            # Grup hiç yoksa en sona ekle
            final_entries.extend(added)
        else:
            for k, new_entry in enumerate(added):
                final_entries.insert(insert_at + k, new_entry)

    # Ana listeyi yeniden oluştur - eskiler silinmedi, yeniler ilave edildi
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("GÜNCELLEME TAMAMLANDI")
    print("İlave edilen yeni kanal:", len(added))
    print("Linki güncellenen kanal:", updated)
    print("Toplam kayıt:", len(final_entries))
    print("Ana dosya:", M3U_FILE)

if __name__ == "__main__":
    main()
