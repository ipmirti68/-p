import os
import re
import requests

SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8")

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟩◆  beIN SPORTS 📡⭕"
SOURCE_GROUP = "Yerel / 🔴 SPOR"

NEW_LOGO = "https://i.imgur.com/TgW5452.png"
GROUP_ICON = "⚽ ⭕"

def norm_group(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9çğıöşü]+', '', s)
    return s

def get_group(line):
    m = re.search(r'group-title="([^"]*)"', line)
    return m.group(1).strip() if m else ""

def is_source_group(g):
    n = norm_group(g)
    return n == norm_group(SOURCE_GROUP) or ("yerel" in n and "spor" in n)

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

def set_logo(extinf):
    if 'tvg-logo="' in extinf:
        extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{NEW_LOGO}"', extinf, count=1)
    else:
        extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{NEW_LOGO}"', 1)
        if 'tvg-logo="' not in extinf:
            extinf = extinf.replace("#EXTINF:", f'#EXTINF:-1 tvg-logo="{NEW_LOGO}"', 1)
    return extinf

def make_channel_key(extinf):
    # Artık sadece karşılaştırma için, eşleştirme için değil
    name = get_channel_name(extinf).lower()
    name = name.replace("🔴", "").replace("⚽", "").replace("⭕", "")
    name = re.sub(r'\s*\(\d+\)\s*$', '', name)  # (2) (3) eklerini yok say
    name = re.sub(r'\s*-?\s*atom\s*$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def has_group_icon(extinf):
    return get_channel_name(extinf).strip().endswith(GROUP_ICON) or GROUP_ICON in get_channel_name(extinf)

def add_group_icon(extinf, suffix=""):
    if "," not in extinf:
        return extinf
    head, display = extinf.split(",", 1)
    display = display.strip()
    display = display.replace(" - 🔴", "").replace("🔴", "").strip()
    # eski (2) varsa temizle, yeniden ekleyeceğiz
    display = re.sub(r'\s*\(\d+\)\s*$', '', display)
    if display.endswith(GROUP_ICON):
        display = display[:-len(GROUP_ICON)].strip()
    # suffix = " (2)" gibi
    return f"{head},{display} {GROUP_ICON}{suffix}"

def main():
    print("=" * 55)
    print("MIRTI68 - 🟩◆  beIN SPORTS 📡")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL yok")
        return

    try:
        response = requests.get(SOURCE_M3U_URL, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        response.encoding = "utf-8"
    except requests.RequestException as e:
        print("Kaynak okunamadı:", e)
        return

    source_entries = read_entries(response.text.splitlines())
    print(f"Kaynakta toplam kayıt: {len(source_entries)}")

    from collections import Counter
    groups = Counter([get_group(e[0]) for e in source_entries if e])
    print("--- KAYNAK GRUPLAR ---")
    for g, c in groups.most_common():
        print(f"{g}: {c} adet")
    print("--- ---")

    new_entries = []
    for entry in source_entries:
        extinf = entry[0]
        if not is_source_group(get_group(extinf)):
            continue
        if len(entry) < 2:
            continue
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue
        new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
        if 'group-title=' not in new_extinf:
            new_extinf = new_extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)
        new_extinf = set_logo(new_extinf)
        new_entries.append([new_extinf, stream])

    print(f"Kaynakta '{SOURCE_GROUP}' grubunda bulunan: {len(new_entries)}")
    if not new_entries:
        print("Kaynak grupta yayın bulunamadı.")
        return

    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)
    final_entries = [list(e) for e in old_entries]

    # === ARTIK SADECE URL İLE EŞLEŞTİR ===
    url_to_index = {}
    # isim -> kaç tane var, (2) (3) vermek için
    name_count = {}

    for idx, entry in enumerate(final_entries):
        if get_group(entry[0]) != FILM_GROUP:
            continue
        url = get_stream(entry)
        if url:
            url_to_index[url] = idx
        key = make_channel_key(entry[0])
        if key:
            name_count[key] = name_count.get(key, 0) + 1

    added = []
    already_same = 0

    for entry in new_entries:
        url = entry[1].strip()
        key = make_channel_key(entry[0])

        # 1. Aynı URL zaten var -> hiç dokunma, sadece logo/ikon tazeleyelim
        if url in url_to_index:
            idx = url_to_index[url]
            old_extinf = final_entries[idx][0]
            old_extinf = set_logo(old_extinf)
            # ikon yoksa ekle, varsa dokunma
            if GROUP_ICON not in old_extinf:
                # (2) varsa koru
                m = re.search(r'\(\d+\)', get_channel_name(old_extinf))
                suffix = f" {m.group(0)}" if m else ""
                old_extinf = add_group_icon(old_extinf, suffix)
            final_entries[idx][0] = old_extinf
            already_same += 1
            continue

        # 2. URL farklı -> YENİ SAY, isim aynı olsa bile üstüne yazma!
        # Aynı isimden kaç tane var, ona göre (2), (3) ekle
        count = name_count.get(key, 0)
        if count == 0:
            suffix = ""
        else:
            suffix = f" ({count + 1})"

        new_extinf = add_group_icon(entry[0], suffix)
        new_entry = [new_extinf, url]
        added.append(new_entry)
        url_to_index[url] = -1
        name_count[key] = count + 1

    if added:
        insert_at = None
        for idx in range(len(final_entries) - 1, -1, -1):
            if get_group(final_entries[idx][0]) == FILM_GROUP:
                insert_at = idx + 1
                break
        if insert_at is None:
            final_entries.extend(added)
        else:
            for k, new_entry in enumerate(added):
                final_entries.insert(insert_at + k, new_entry)

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("GÜNCELLEME TAMAMLANDI")
    print(f"Kaynakta bulunan: {len(new_entries)}")
    print(f"Eklenen yeni yayın (farklı URL): {len(added)}")
    print(f"Zaten aynı URL ile var olan: {already_same}")
    print(f"Toplam kontrol: {len(added) + already_same} / {len(new_entries)}")
    print(f"Toplam kayıt: {len(final_entries)}")

if __name__ == "__main__":
    main()
