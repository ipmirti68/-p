import os
import re
import requests

# 7 URL desteği: Secrets'e tek tek veya virgüllü yazabilirsin
# Yöntem 1: SOURCE_M3U_URLS = "url1,url2,url3,url4,url5,url6,url7"
# Yöntem 2: SOURCE_M3U_URL_1 ... SOURCE_M3U_URL_7
# Yöntem 3: Tek URL için eski SOURCE_M3U_URL de çalışır
def get_source_urls():
    urls = []
    multi = os.environ.get("SOURCE_M3U_URLS", "https://raw.githubusercontent.com/yavuzelidurmaz-sketch/hdfilm/refs/heads/main/showtv.m3u")
    if multi:
        return [u.strip() for u in multi.split(",") if u.strip()]
    for i in range(1, 8):
        u = os.environ.get(f"SOURCE_M3U_URL_{i}", "").strip()
        if u:
            urls.append(u)
    single = os.environ.get("SOURCE_M3U_URL", "").strip()
    if single and single not in urls:
        urls.append(single)
    return urls

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟪◆ SHOWTV DİZİLERİ ⭕"

def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""

def get_channel_name(line):
    return line.split(",", 1)[1].strip() if "," in line else ""

def get_stream(entry):
    return next((x.strip() for x in entry[1:] if x.strip().startswith(("http://", "https://"))), "")

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

def make_channel_key(extinf):
    name = get_channel_name(extinf).lower().replace("🔴", "")
    return re.sub(r'\s+', ' ', name).strip()

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
    print("MIRTI68 - SERİ DİZİLER - NE VARSA AL")
    print("=" * 55)

    source_urls = get_source_urls()
    if not source_urls:
        print("HATA: URL bulunamadı")
        return

    new_entries = []
    seen_urls = set()

    for i, url in enumerate(source_urls, start=1):
        print(f"{i}. URL çekiliyor...")
        try:
            r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            r.encoding = "utf-8"
        except Exception as e:
            print(f"{i}. URL HATA: {e}")
            continue

        entries = read_entries(r.text.splitlines())
        print(f"{i}. URL: {len(entries)} kanal bulundu, hepsi alınıyor")

        for entry in entries:
            extinf = entry[0]
            stream = get_stream(entry)
            if not stream or stream in seen_urls:
                continue
            seen_urls.add(stream)

            # Grup yoksa ekle, varsa değiştir - hepsi SERİ DİZİLER olacak
            if 'group-title=' in extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
            else:
                new_extinf = extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)

            new_entries.append([new_extinf, stream])

    if not new_entries:
        print("Hiç kanal bulunamadı, liste değiştirilmedi")
        return

    # Eski listeyi oku
    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)
    final_entries = [list(e) for e in old_entries]

    # Eski SERİ DİZİLER kanallarını tanı
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

        # 1. Aynı link var -> dokunma
        if url in url_to_index:
            continue

        # 2. Aynı isim var, link değişmiş -> sadece linki güncelle
        if key in name_to_index:
            idx = name_to_index[key]
            old_entry = final_entries[idx]
            for j in range(1, len(old_entry)):
                if old_entry[j].strip().startswith(("http://", "https://")):
                    old_entry[j] = url
                    break
            else:
                old_entry.append(url)
            url_to_index[url] = idx
            updated += 1
            continue

        # 3. Yeni kanal -> 🔴 ile ekle
        added.append([add_atom_suffix(entry[0]), url])
        name_to_index[key] = -1
        url_to_index[url] = -1

    # Yeni kanalları SERİ DİZİLER grubunun sonuna ekle
    if added:
        insert_at = None
        for idx in range(len(final_entries) - 1, -1, -1):
            if get_group(final_entries[idx][0]) == FILM_GROUP:
                insert_at = idx + 1
                break
        if insert_at is None:
            final_entries.extend(added)
        else:
            for k, ne in enumerate(added):
                final_entries.insert(insert_at + k, ne)

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("TAMAMLANDI")
    print("Yeni eklenen:", len(added))
    print("Linki güncellenen:", updated)
    print("Toplam:", len(final_entries))

if __name__ == "__main__":
    main()
