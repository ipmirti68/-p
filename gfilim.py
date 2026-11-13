
import os
import re
import requests

SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "http://190502.tomtv.eu:80/get.php?username=MustafaozdemR7808&password=z189b8mv2r&type=m3u_plus&output=ts")

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟪◆ GÜNCEL FİLİMLER ⭕"
SOURCE_GROUP = "SONVIZYON FILMLER"



def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""

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

def main():
    print("=" * 55)
    print("MIRTI68 - PAZAR DİZİ GÜNCELLEME")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL tanımlanmamış.")
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
        print("PAZAR grubunda yayın bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    old_lines = []

    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)

    seen_urls = set()
    unique_entries = []

    for entry in new_entries:
        if entry[1] not in seen_urls:
            seen_urls.add(entry[1])
            unique_entries.append(entry)

    # === REVİZE EDİLEN KISIM: MEVCUT GRUBA YAZ ===
    final_entries = []
    inserted = False

    for entry in old_entries:
        if get_group(entry[0]) == FILM_GROUP:
            # Grubun ilk kanalını bulduk, yenileri tam buraya yaz
            if not inserted:
                final_entries.extend(unique_entries)
                inserted = True
            # Eski PAZAR kanalını ekleme, yenisiyle değişmiş oluyor
            continue
        final_entries.append(entry)

    # Listede hiç PAZAR grubu yoksa, en başa ekle
    if not inserted:
        final_entries = unique_entries + final_entries
    # === REVİZE SONU ===

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("PAZAR GÜNCELLENDİ")
    print("Yeni kayıt:", len(unique_entries))
    print("Ana dosya:", M3U_FILE)

if __name__ == "__main__":
    main()
