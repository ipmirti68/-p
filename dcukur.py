import os
import re
import requests
from collections import Counter

# Kaynak - beIN ile aynı adres
SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "https://raw.githubusercontent.com/ramazansancar/UzunMuhalefet_Legal-IPTV/e1720991093a5952656096663500b58d1d8f9d4c/lists/video/sources/puhutv-com/diziler/cukur.m3u")

M3U_FILE = "mirti68.m3u"
TARGET_GROUP = "🟪◆ DİZİLER - ÇUKUR ⭕"

def norm_group(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9çğıöşü]+', '', s)
    return s

def get_group(line):
    m = re.search(r'group-title="([^"]*)"', line)
    return m.group(1).strip() if m else ""

def is_source_group(g):
    n = norm_group(g)
    # birebir + esnek: içinde prison + break geçiyorsa al
    return n == norm_group(SOURCE_GROUP) or ("prison" in n and "break" in n)

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

def make_key(extinf):
    # Bölüm ismiyle ayırt et: Prison Break S01 E01 gibi
    name = get_channel_name(extinf).lower()
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def rename_entry(entry):
    extinf = entry[0]
    # 1. Grup ismini değiştir
    new_extinf = re.sub(
        r'group-title="[^"]*"',
        f'group-title="{TARGET_GROUP}"',
        extinf
    )
    if 'group-title=' not in new_extinf:
        new_extinf = new_extinf.replace(
            "#EXTINF:",
            f'#EXTINF:-1 group-title="{TARGET_GROUP}"',
            1
        )
    # 2. Dizi olduğunu söyle
    new_extinf = re.sub(r'\s*tvg-type="[^"]*"', '', new_extinf, count=1)
    new_extinf = re.sub(r'#EXTINF:-?\d+', '#EXTINF:-1 tvg-type="series"', new_extinf, count=1)
    return [new_extinf] + entry[1:]

def main():
    print("=" * 55)
    print(f"MIRTI68 - {TARGET_GROUP}")
    print("=" * 55)

    try:
        r = requests.get(SOURCE_M3U_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.RequestException as e:
        print("Kaynak okunamadı:", e)
        return

    source_entries = read_entries(r.text.splitlines())
    print(f"Kaynakta toplam kayıt: {len(source_entries)}")

    # Kaynakta Prison Break ile ilgili grupları göster
    groups = Counter([get_group(e[0]) for e in source_entries if e])
    print("--- PRISON BREAK İLE İLGİLİ GRUPLAR ---")
    for g, c in groups.most_common():
        if "prison" in g.lower() or "break" in g.lower():
            print(f"{g}: {c} adet")
    print("--- ---")

    new_entries = []
    for entry in source_entries:
        if not is_source_group(get_group(entry[0])):
            continue
        if len(entry) < 2:
            continue
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue
        new_entries.append(rename_entry(entry))

    print(f"'{SOURCE_GROUP}' grubunda bulunan: {len(new_entries)}")

    if not new_entries:
        print("Kaynak grupta yayın bulunamadı. Grup ismini kontrol et.")
        return

    old_entries = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_entries = read_entries(f.read().splitlines())

    final_entries = [list(e) for e in old_entries]

    # Eski PRISON BREAK grubunu tanı
    url_to_index = {}
    name_to_index = {}
    for idx, entry in enumerate(final_entries):
        if get_group(entry[0]) != TARGET_GROUP:
            continue
        url = get_stream(entry)
        if url:
            url_to_index[url] = idx
        key = make_key(entry[0])
        if key:
            name_to_index[key] = idx

    added = []
    updated = 0
    already_same = 0

    for entry in new_entries:
        url = get_stream(entry).strip()
        key = make_key(entry[0])

        # 1. Aynı link var -> dokunma
        if url in url_to_index:
            already_same += 1
            continue

        # 2. Aynı bölüm ismi var ama link değişmiş -> linki güncelle
        if key in name_to_index:
            idx = name_to_index[key]
            old_entry = final_entries[idx]
            for j in range(1, len(old_entry)):
                if old_entry[j].strip().startswith(("http://", "https://")):
                    old_entry[j] = url
                    break
            else:
                old_entry.append(url)
            # Grup ismini de yenile
            old_entry[0] = entry[0]
            url_to_index[url] = idx
            updated += 1
            continue

        # 3. Yeni bölüm
        added.append(entry)
        name_to_index[key] = -1
        url_to_index[url] = -1

    # Yeni bölümleri grubun sonuna ekle
    if added:
        insert_at = None
        for idx in range(len(final_entries) - 1, -1, -1):
            if get_group(final_entries[idx][0]) == TARGET_GROUP:
                insert_at = idx + 1
                break
        if insert_at is None:
            final_entries.extend(added)
        else:
            for k, e in enumerate(added):
                final_entries.insert(insert_at + k, e)

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("GÜNCELLEME TAMAMLANDI")
    print(f"Kaynakta bulunan: {len(new_entries)}")
    print(f"Eklenen yeni bölüm: {len(added)}")
    print(f"Linki güncellenen bölüm: {updated}")
    print(f"Zaten var olan: {already_same}")
    print(f"Toplam kontrol: {len(added) + updated + already_same} / {len(new_entries)}")
    print(f"Toplam kayıt: {len(final_entries)}")

if __name__ == "__main__":
    main()
