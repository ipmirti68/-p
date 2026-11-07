
import os
import re
import requests

# ==========================================
# MIRTI68 - DIZI SON BOLUM
# ==========================================

SOURCE_M3U_URL = "https://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts"

M3U_FILE = "mirti68.m3u"

FILM_GROUP = "🎥 DİZİ SON BÖLÜM"

SOURCE_GROUP = "TR/FILM ► PAZARTESI"


# ==========================================
# M3U GRUPLARINI AYIKLA
# ==========================================

def get_group(line):

    match = re.search(
        r'group-title="([^"]*)"',
        line
    )

    return match.group(1) if match else ""


def read_entries(lines):

    entries = []
    current = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTM3U"):
            continue

        if line.startswith("#EXTINF:"):

            if current:
                entries.append(current)

            current = [line]

        elif current is not None:

            current.append(line)

    if current:
        entries.append(current)

    return entries


# ==========================================
# KAYNAKTAN İSTENEN GRUBU AL
# ==========================================

def fetch_source():

    print("Kaynak M3U okunuyor...")

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        SOURCE_M3U_URL,
        headers=headers,
        timeout=60
    )

    response.raise_for_status()

    response.encoding = "utf-8"

    source_entries = read_entries(
        response.text.splitlines()
    )

    new_entries = []
    seen = set()

    for entry in source_entries:

        extinf = entry[0]

        if get_group(extinf) != SOURCE_GROUP:
            continue

        if len(entry) < 2:
            continue

        stream = entry[1].strip()

        if not stream or stream.startswith("#"):
            continue

        # Aynı yayın adresini tekrar ekleme.
        if stream in seen:
            continue

        seen.add(stream)

        # Grup adını değiştir.
        new_extinf = re.sub(
            r'group-title="[^"]*"',
            f'group-title="{FILM_GROUP}"',
            extinf,
            count=1
        )

        new_entries.append([
            new_extinf,
            stream
        ])

    print("Kaynakta bulunan kayıt:", len(new_entries))

    return new_entries


# ==========================================
# ANA LİSTEYİ GÜNCELLE
# ==========================================

def update_master(new_entries):

    if not new_entries:

        print("Yeni kayıt bulunamadı.")
        print("Ana liste korunuyor.")
        return

    if os.path.exists(M3U_FILE):

        with open(
            M3U_FILE,
            "r",
            encoding="utf-8-sig"
        ) as file:

            old_lines = file.read().splitlines()

    else:

        old_lines = ["#EXTM3U"]

    old_entries = read_entries(old_lines)

    preserved = []

    # Yalnızca kendi grubumuzu çıkar.
    for entry in old_entries:

        group = get_group(entry[0])

        if group == FILM_GROUP:
            continue

        preserved.append(entry)

    # Yeni kayıtları ekle.
    final_entries = preserved + new_entries

    # Tekrarlanan URL kayıtlarını temizle.
    result = []
    seen_urls = set()

    for entry in final_entries:

        if len(entry) < 2:
            continue

        stream = entry[1].strip()

        if stream in seen_urls:
            continue

        seen_urls.add(stream)
        result.append(entry)

    # Dosyayı baştan, tek başlıkla yaz.
    with open(
        M3U_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("#EXTM3U\n")

        for entry in result:

            for line in entry:
                file.write(line + "\n")

    print("===================================")
    print("MIRTI68 LİSTESİ GÜNCELLENDİ")
    print("===================================")
    print("Yeni dizi kaydı:", len(new_entries))
    print("Korunan diğer kayıt:", len(preserved))
    print("Toplam kayıt:", len(result))
    print("Ana dosya:", M3U_FILE)
    print("Yedek dosya: YOK")


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    try:

        new_entries = fetch_source()

        update_master(new_entries)

    except Exception as error:

        print("HATA:", error)
        print("Ana liste değiştirilmedi.")


if __name__ == "__main__":
    main()
