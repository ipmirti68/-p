import os
import requests
import re

# KAYNAK URL
SOURCE_M3U_URL = "http://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts"

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟨◆  ULUSAL ⭕"

KAYNAKTAKİ_GRUP_ADI = "Turkiye / HEVC"

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
            if KAYNAKTAKİ_GRUP_ADI in line:
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
                        new_entries.append(new_line)
                        new_entries.append(stream)
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

    # --- DÜZELTME BURADA: YERİNDE DEĞİŞTİR ---
    final_lines = []
    inserted = False
    skip_url = False

    for line in old_lines:
        if line.startswith("#EXTM3U"):
            continue

        if line.startswith("#EXTINF:"):
            is_old_group = FILM_GROUP in line
            if is_old_group:
                # Eski grubun ilk kaydını gördüğümüz an, yeni grubu TAM BURAYA koy
                if not inserted:
                    final_lines.extend(new_entries)
                    inserted = True
                skip_url = True
                continue # Eski kaydı ekleme
            else:
                skip_url = False
                final_lines.append(line)
        else:
            # URL satırı
            if not skip_url and line.strip() != "":
                final_lines.append(line)

    # Eğer dosyada daha önce bu grup hiç yoksa, en sona ekle (1. sıraya değil)
    if not inserted:
        final_lines.extend(new_entries)
        print("\nNot: Eski grup bulunamadı, yeni grup en sona eklendi.")

    # Yeni listeyi yaz - SIRALAMA BOZULMADAN
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for line in final_lines:
            f.write(line + "\n")

    print("\nGRUPFİLİM GÜNCELLENDİ!")
    print("Yeni kayıt:", len(new_entries) // 2)
    print("Ana dosya:", M3U_FILE)
    print("Grup kendi yerinde güncellendi, sıralama korundu.")

if __name__ == "__main__":
    main()
