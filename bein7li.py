import os
import re
import requests

# GitHub Secrets'ten 7 URL al
# Secrets'e SOURCE_M3U_URL_1, SOURCE_M3U_URL_2 ... diye 7 tane ekleyeceksin
# İstersen tek Secrets'e virgülle de yazabilirsin, altta ikisini de destekliyor
def get_source_urls():
    urls = []
    # Yöntem 1: Tek Secrets içinde virgüllü: SOURCE_M3U_URLS = "url1,url2,url3..."
    multi = os.environ.get("SOURCE_M3U_URLS", "")
    if multi:
        urls = [u.strip() for u in multi.split(",") if u.strip()]
        return urls
    # Yöntem 2: 7 ayrı Secrets
    for i in range(1, 8):
        u = os.environ.get(f"SOURCE_M3U_URL_{i}", "").strip()
        if u:
            urls.append(u)
    # Eski tek URL ile uyumlu olsun diye
    single = os.environ.get("SOURCE_M3U_URL", "").strip()
    if single and single not in urls:
        urls.append(single)
    return urls

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟩◆  beIN SPORTS 📡"

def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""

def get_channel_name(line):
    if "," in line:
        return line.split(",", 1)[1].strip()
    return ""

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

# --- ⭕ İŞLEMLERİ ---
def make_channel_key(extinf):
    name = get_channel_name(extinf).lower()
    name = name.replace("⭕", "")
    name = re.sub(r'\s*-?\s*atom\s*$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def add_atom_suffix(extinf):
    if "," not in extinf:
        return extinf
    head, display = extinf.split(",", 1)
    display = display.strip()
    if display.endswith("⭕"):
        return extinf
    return f"{head},{display} - ⭕"

def main():
    print("=" * 55)
    print("MIRTI68 - SPORTS FİLTRESİ - 7 URL")
    print("=" * 55)

    source_urls = get_source_urls()
    if not source_urls:
        print("HATA: Hiç kaynak URL bulunamadı.")
        print("Secrets'e SOURCE_M3U_URL_1 ... _7 veya SOURCE_M3U_URLS ekle")
        return

    print(f"Toplam {len(source_urls)} kaynak taranacak")

    new_entries = []
    seen_in_new = set()

    for idx_url, SOURCE_M3U_URL in enumerate(source_urls, start=1):
        print(f"\n--- {idx_url}. Kaynak çekiliyor ---")
        try:
            response = requests.get(SOURCE_M3U_URL, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            response.encoding = "utf-8"
        except Exception as e:
            print(f"{idx_url}. Kaynak okunamadı: {e}")
            continue

        source_entries = read_entries(response.text.splitlines())
        count_this = 0

        for entry in source_entries:
            extinf = entry[0]
            channel_name = get_channel_name(extinf)

            # === ASIL FİLTRE BURADA: Adında SPORTS geçiyor mu? ===
            # Büyük/küçük harf fark etmez, sports / SPORTS / Sports hepsi olur
            if "sports" not in channel_name.lower():
                continue

            if len(entry) < 2:
                continue

            stream = get_stream(entry)
            if not stream:
                continue

            # Aynı link 7 URL içinde tekrar ediyorsa 1 kere al
            if stream in seen_in_new:
                continue
            seen_in_new.add(stream)

            # Grubu değiştir -> Hepsini beIN SPORTS grubuna bas
            if 'group-title=' in extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
            else:
                new_extinf = extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)

            new_entries.append([new_extinf, stream])
            count_this += 1

        print(f"{idx_url}. Kaynak: {count_this} adet SPORTS kanalı bulundu")

    if not new_entries:
        print("\nHiçbir kaynakta adında SPORTS geçen kanal bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    # Eski listeyi oku
    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)
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

        # 2. Aynı isim var ama link değişmiş -> sadece linki güncelle, isim aynen kalsın
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

        # 3. Gerçekten yeni -> ⭕ ile ekle
        new_extinf = add_atom_suffix(entry[0])
        new_entry = [new_extinf, url]
        added.append(new_entry)
        name_to_index[key] = -1
        url_to_index[url] = -1

    # Yeni kanalları beIN grubunun sonuna ekle
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

    print("\nGÜNCELLEME TAMAMLANDI")
    print("İlave edilen yeni kanal:", len(added))
    print("Linki güncellenen kanal:", updated)
    print("Toplam kayıt:", len(final_entries))

if __name__ == "__main__":
    main()
