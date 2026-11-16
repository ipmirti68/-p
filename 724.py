import os
import re

M3U_FILE = "mirti68.m3u"

# Burayı kendin doldur:
# (kaynak_adresi, kaynakta_aranacak_grup_adi)
KAYNAKLAR = [
    ("http://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts", "Yerli 7/24"),
    ("http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts", "TR | 7/24 DIZI"),
]

# Hedef dosyada hangi grup adıyla yazılacak?
HEDEF_GRUP = "🟪◆  7/24 DİZİ 📺⭕"

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

def kaynaktan_grup_cek(url, aranan_grup):
    """Bir kaynaktan sadece istenen grubu çeker. Olmazsa boş liste döner."""
    import requests

    try:
        r = requests.get(url, timeout=30)
        r.encoding = "utf-8"
        if r.status_code != 200:
            print(f"HATA: {url} -> HTTP {r.status_code}")
            return []
        lines = r.text.splitlines()
    except Exception as e:
        print(f"HATA: {url} okunamadı: {e}")
        return []

    yeni = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            grup = get_group(line)
            if grup == aranan_grup:
                yeni_satir = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{HEDEF_GRUP}"',
                    line
                )
                if 'group-title=' not in yeni_satir:
                    yeni_satir = yeni_satir.replace(
                        '#EXTINF:-1',
                        f'#EXTINF:-1 group-title="{HEDEF_GRUP}"'
                    )

                # === KANAL ADININ YANINA ⭕ EKLE ===
                if "," in yeni_satir:
                    baslik, kanal_adi = yeni_satir.rsplit(",", 1)
                    kanal_adi = kanal_adi.strip()
                    if not kanal_adi.endswith("⭕"):
                        kanal_adi = kanal_adi + " ⭕"
                    yeni_satir = baslik + "," + kanal_adi
                # ================================

                if i + 1 < len(lines):
                    stream = lines[i + 1].strip()
                    if stream and not stream.startswith("#"):
                        yeni.append([yeni_satir, stream])
                i += 2
                continue
        i += 1
    return yeni

def main():
    print("=" * 55)
    print("GRUP GÜNCELLENİYOR")
    print("=" * 55)

    # 1. Sırayla kaynakları dene, ilk dolu geleni al
    new_entries = []
    kullanilan_kaynak = None

    for url, grup in KAYNAKLAR:
        print(f"\nDeneniyor: {url} | Grup: {grup}")
        bulunan = kaynaktan_grup_cek(url, grup)
        print(f"Bulunan: {len(bulunan)}")
        if bulunan:
            new_entries = bulunan
            kullanilan_kaynak = (url, grup)
            break
        else:
            print("Boş geldi, sıradaki kaynağa geçiliyor...")

    if not new_entries:
        print("\nHiçbir kaynakta grup bulunamadı.")
        print("Ana dosya değiştirilmedi.")
        return

    print(f"\nKullanılan kaynak: {kullanilan_kaynak}")

    # 2. Ana listeyi oku
    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)

    # 3. Tekrarlanan URL temizle
    seen = set()
    unique_entries = []
    for e in new_entries:
        if e[1] not in seen:
            seen.add(e[1])
            unique_entries.append(e)

    # 4. Eski grubu sil, yenisini aynı yere yaz
    final_entries = []
    inserted = False

    for entry in old_entries:
        if get_group(entry[0]) == HEDEF_GRUP:
            if not inserted:
                final_entries.extend(unique_entries)
                inserted = True
            continue
        final_entries.append(entry)

    if not inserted:
        print("UYARI: Hedef grup dosyada yoktu, en başa eklendi.")
        final_entries = unique_entries + final_entries
    else:
        print("Grup bulundu, kendi yerine yazıldı.")

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("\nGÜNCELLENDİ!")
    print("Yeni kayıt:", len(unique_entries))
    print("Ana dosya:", M3U_FILE)

if __name__ == "__main__":
    main()
