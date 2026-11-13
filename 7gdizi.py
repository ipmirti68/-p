import re
import requests
from datetime import datetime

# 7 TANE URL'Yİ BURAYA YAZ
# 0=Pazartesi, 1=Salı, 2=Çarşamba, 3=Perşembe, 4=Cuma, 5=Cumartesi, 6=Pazar
DAILY_URLS = [
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/pazartesi.m3u",
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/sali.m3u",
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/carsamba.m3u",
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/persembe.m3u",
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/cuma.m3u",
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/cumartesi.m3u",
    "https://raw.githubusercontent.com/raalbatros/serie/refs/heads/main/pazar.m3u",
]

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟪◆ GÜNCEL DİZİLER ⭕"

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
    weekday = datetime.now().weekday()
    gun_isimleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    SOURCE_M3U_URL = DAILY_URLS[weekday]

    print("=" * 55)
    print(f"MIRTI68 - {gun_isimleri[weekday]} GÜNCELLEMESİ")
    print(f"Kaynak: {SOURCE_M3U_URL}")
    print("=" * 55)

    try:
        response = requests.get(SOURCE_M3U_URL, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        response.encoding = "utf-8"
    except Exception as e:
        print("Kaynak okunamadı:", e)
        return

    source_entries = read_entries(response.text.splitlines())
    new_entries = []

    for entry in source_entries:
        extinf = entry[0]
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue

        # GRUP YOKSA EKLE, VARSA DEĞİŞTİR - HEPSİNE AYNI GRUBU BAS
        if 'group-title=' in extinf:
            new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
        else:
            # group-title yoksa, EXTINF satırına ekle
            new_extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)
            # Eğer #EXTINF:-1 değil de #EXTINF:0 gibi ise
            if 'group-title=' not in new_extinf:
                new_extinf = extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}" ', 1)

        new_entries.append([new_extinf, stream])

    if not new_entries:
        print("Kaynakta hiç yayın bulunamadı.")
        return

    # Eski listeyi oku
    old_lines = []
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()
    except FileNotFoundError:
        pass

    old_entries = read_entries(old_lines)

    # Tekrar eden linkleri temizle
    seen = set()
    unique_entries = []
    for e in new_entries:
        if e[1] not in seen:
            seen.add(e[1])
            unique_entries.append(e)

    # Eski GÜNCEL DİZİLER grubunu sil, yenisini koy
    final_entries = []
    inserted = False
    for entry in old_entries:
        if get_group(entry[0]) == FILM_GROUP:
            if not inserted:
                final_entries.extend(unique_entries)
                inserted = True
            continue
        final_entries.append(entry)

    if not inserted:
        final_entries = unique_entries + final_entries

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("GÜNCELLENDİ - Yeni kayıt:", len(unique_entries))

if __name__ == "__main__":
    main()
