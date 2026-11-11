import os
import requests
import re

# KAYNAK URL - buraya 724 kaynagin tam adresini yaz
SOURCE_M3U_URL = "http://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts"

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟪◆ 2026 FİLİMLER"

# www.com.m3u icindeki hangi gruplari alacaksin?
KAYNAKTAKİ_GRUP_ADLARI = [
    " TR/FILM ► 2026 Filmler ",
    " TR/FILM ► Yerli 2026 "
]

def main():
    print("=" * 55)
    print("www.com.m3u DEN GRUPFILIM CEKILIYOR")
    print("=" * 55)
    print(f"\nKaynak okunuyor: {SOURCE_M3U_URL}")
    r = requests.get(SOURCE_M3U_URL, timeout=30)
    r.encoding = "utf-8"
    source_lines = r.text.splitlines()
    new_entries = []
    i = 0
    while i < len(source_lines):
        line = source_lines[i].strip()
        if line.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', line)
            grup = m.group(1) if m else ""
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
                        new_entries.append(new_line)
                        new_entries.append(stream)
                        print(f"EKLENDI: {new_line.split(',')[-1]}")
                i += 2
                continue
        i += 1
    if not new_entries:
        print("\nKaynakta o grup bulunamadi.")
        print("Ana M3U listesi degistirilmedi.")
        return
    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()
    preserved = []
    skip_url = False
    for line in old_lines:
        if line.startswith("#EXTINF:"):
            skip_url = FILM_GROUP in line
            if not skip_url:
                preserved.append(line)
        elif line.startswith("#EXTM3U"):
            continue
        else:
            if not skip_url and line.strip() != "":
                preserved.append(line)
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for line in preserved:
            f.write(line + "\n")
        for line in new_entries:
            f.write(line + "\n")
    print("\nGRUPFILIM GUNCELLENDI!")
    print("Yeni kayit:", len(new_entries) // 2)
    print("Ana dosya:", M3U_FILE)
    print("Diger kategoriler korundu.")

if __name__ == "__main__":
    main()
