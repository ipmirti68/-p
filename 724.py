import os
import requests
import re

# KAYNAK URL - senin dediğin
SOURCE_M3U_URL = "http://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts"

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟪◆  7/24 DİZİ 📺⭕"

# www.com.m3u içindeki hangi grubu alacaksın?
# Buraya o m3u'nun içindeki orijinal grup adını yaz
# Örnek: "ABC" / "Filmler" / "Movies"
KAYNAKTAKİ_GRUP_ADLARI = [    "Yerli 7/24"]

def get_group(line):
    m = re.search(r'group-title="([^"]*)"', line)
    return m.group(1).strip() if m else ""

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
    print("www.com.m3u DEN GRUPFİLİM ÇEKİLİYOR")
    print("=" * 55)

    print(f"\nKaynak okunuyor: {SOURCE_M3U_URL}")
    r = requests.get(SOURCE_M3U_URL, timeout=30)
    r.encoding = "utf-8"
    source_lines = r.text.splitlines()

    # Kaynak m3u içinden istenen grubu topla
    new_entries = []
    i = 0
    while i < len(source_lines):
        line = source_lines[i].strip()
        if line.startswith("#EXTINF:"):
            grup = get_group(line)
            if grup in KAYNAKTAKİ_GRUP_ADLARI:
                new_line = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{FILM_GROUP}"',
                    line
                )
                if 'group-title=' not in new_line:
                    new_line = new_line.replace(
                        '#EXTINF:-1',
                        f'#EXTINF:-1 group-title="{FILM_GROUP}"'
                    )
                if i + 1 < len(source_lines):
                    stream = source_lines[i + 1].strip()
                    if stream and not stream.startswith("#"):
                        new_entries.append([new_line, stream])
                        print(f"EKLENDİ: {new_line.split(',')[-1]}")
                i += 2
                continue
        i += 1

    if not new_entries:
        print("\nKaynakta o grup bulunamadı.")
        print("Ana M3U listesi değiştirilmedi.")
        return

    # Ana listeyi oku
    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)

    # HATA AYIKLAMA: Dosyadaki grupları göster
    print("\n--- DOSYADAKİ GRUPLAR ---")
    dosya_gruplari = []
    for e in old_entries:
        g = get_group(e[0])
        if g not in dosya_gruplari:
            dosya_gruplari.append(g)
            print(f"Bulunan grup: [{g}]")
    print(f"Aranan grup: [{FILM_GROUP}]")
    print(f"Eşleşti mi? {FILM_GROUP in dosya_gruplari}")
    print("-------------------------\n")

    # Tekrarlanan URL temizle
    seen = set()
    unique_entries = []
    for e in new_entries:
        if e[1] not in seen:
            seen.add(e[1])
            unique_entries.append(e)

    # === MEVCUT GRUBUN İÇİNE YAZ - EN SONA GİTMEZ ===
    final_entries = []
    inserted = False

    for entry in old_entries:
        if get_group(entry[0]) == FILM_GROUP:
            if not inserted:
                # Grubun ilk kanalını bulduk, yenileri tam buraya yaz
                final_entries.extend(unique_entries)
                inserted = True
            # Eski kanalı ekleme
            continue
        final_entries.append(entry)

    # Grup hiç yoksa en başa ekle
    if not inserted:
        print("UYARI: Dosyada bu grup bulunamadı, en başa eklendi.")
        final_entries = unique_entries + final_entries
    else:
        print("Grup bulundu, kendi yerine yazıldı.")

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("\nGRUPFİLİM GÜNCELLENDİ!")
    print("Yeni kayıt:", len(unique_entries))
    print("Ana dosya:", M3U_FILE)

if _name_ == "_main_":
    main()
