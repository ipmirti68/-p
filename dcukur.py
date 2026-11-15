import os
import re
import requests

SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "https://raw.githubusercontent.com/ramazansancar/UzunMuhalefet_Legal-IPTV/e1720991093a5952656096663500b58d1d8f9d4c/lists/video/sources/puhutv-com/diziler/cukur.m3u")

M3U_FILE = "mirti68.m3u"
TARGET_GROUP = "🟪◆ DİZİLER - ÇUKUR ⭕"

def get_group(line):
    m = re.search(r'group-title="([^"]*)"', line)
    return m.group(1).strip() if m else ""

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
    name = get_channel_name(extinf).lower()
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def rename_entry(entry):
    extinf = entry[0]
    # Grup ne olursa olsun bizim gruba çevir
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
    new_extinf = re.sub(r'\s*tvg-type="[^"]*"', '', new_extinf, count=1)
    new_extinf = re.sub(r'#EXTINF:-?\d+', '#EXTINF:-1 tvg-type="series"', new_extinf, count=1)
    return [new_extinf] + entry[1:]

def main():
    print("=" * 55)
    print(f"MIRTI68 - {TARGET_GROUP} - GRUPSUZ DİREKT ÇEKİM")
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

    # Grup yok, hepsini al
    new_entries = []
    for entry in source_entries:
        if len(entry) < 2:
            continue
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue
        new_entries.append(rename_entry(entry))

    print(f"Direkt çekilen: {len(new_entries)}")

    if not new_entries:
        print("Kaynakta yayın bulunamadı.")
        return

    old_entries = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_entries = read_entries(f.read().splitlines())

    final_entries = [list(e) for e in old_entries]

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

        if url in url_to_index:
            already_same += 1
            continue

        if key in name_to_index:
            idx = name_to_index[key]
            old_entry = final_entries[idx]
            for j in range(1, len(old_entry)):
                if old_entry[j].strip().startswith(("http://", "https://")):
                    old_entry[j] = url
                    break
            else:
                old_entry.append(url)
            old_entry[0] = entry[0]
            url_to_index[url] = idx
            updated += 1
            continue

        added.append(entry)
        name_to_index[key] = -1
        url_to_index[url] = -1

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
