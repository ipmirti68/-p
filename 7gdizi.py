import re
import requests

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
    print("=" * 55)
    print("MIRTI68 - 7 URL TOPLU GÜNCELLEME")
    print("=" * 55)

    all_new_entries = []
    seen_urls = set()

    # 7 URL'NİN HEPSİNİ TEK TEK DOLAŞ
    for i, url in enumerate(DAILY_URLS, start=1):
        if not url or "BURAYA" in url:
            print(f"{i}. URL boş, atlandı")
            continue

        print(f"{i}. URL çekiliyor: {url[:60]}...")
        try:
            response = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            response.encoding = "utf-8"
        except Exception as e:
            print(f"{i}. URL HATA: {e}")
            continue

        source_entries = read_entries(response.text.splitlines())
        print(f"{i}. URL'den {len(source_entries)} kanal bulundu")

        for entry in source_entries:
            extinf = entry[0]
            stream = next((x for x in entry[1:] if not x.startswith("#")), "")
            if not stream.startswith(("http://", "https://")):
                continue
            if stream in seen_urls:
                continue
            seen_urls.add(stream)

            # GRUP YOKSA EKLE, VARSA DEĞİŞTİR
            if 'group-title=' in extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
            else:
                if "#EXTINF:-1" in extinf:
                    new_extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)
                else:
                    new_extinf = extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}" ', 1)

            all_new_entries.append([new_extinf, stream])

    if not all_new_entries:
        print("HİÇ KANAL BULUNAMADI - Liste değiştirilmedi")
        return

    # Eski listeyi oku
    old_lines = []
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()
    except FileNotFoundError:
        pass

    old_entries = read_entries(old_lines)

    # Eski GÜNCEL DİZİLER grubunu sil, yenisini koy
    final_entries = []
    inserted = False
    for entry in old_entries:
        if get_group(entry[0]) == FILM_GROUP:
            if not inserted:
                final_entries.extend(all_new_entries)
                inserted = True
            continue
        final_entries.append(entry)

    if not inserted:
        final_entries = all_new_entries + final_entries

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("=" * 55)
    print(f"TOPLAM GÜNCELLENDİ: {len(all_new_entries)} kanal")
    print("=" * 55)

if __name__ == "__main__":
    main()
