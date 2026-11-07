import os
import requests
import re

# KAYNAK URL - senin dediğin
SOURCE_M3U_URL = "http://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts"

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🎥 DİZİ SON BÖLÜM"

# www.com.m3u içindeki hangi grubu alacaksın?
# Buraya o m3u'nun içindeki orijinal grup adını yaz
# Örnek: "ABC" / "Filmler" / "Movies"
KAYNAK_GRUP_LISTESI = "TR/FILM ► PERSEMBE"
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
            # Bu satır istenen gruptan mı?
            if KAYNAKTAKİ_GRUP_ADI in line:
                # Grup adını grupfilim olarak değiştir
                new_line = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{FILM_GROUP}"',
                    line
                )
                # group-title yoksa ekle
                if 'group-title=' not in new_line:
                    new_line = new_line.replace(
                        '#EXTINF:-1',
                        f'#EXTINF:-1 group-title="{FILM_GROUP}"'
                    )
                # Bir sonraki satır yayın adresi
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

    # Eski grupfilim kayıtlarını sil, diğerlerini koru
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

    # Yeni listeyi yaz
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for line in preserved:
            f.write(line + "\n")
        for line in new_entries:
            f.write(line + "\n")

    print("\nGRUPFİLİM GÜNCELLENDİ!")
    print("Yeni kayıt:", len(new_entries) // 2)
    print("Ana dosya:", M3U_FILE)
    print("Diğer kategoriler korundu.")

if __name__ == "__main__":
    main()
