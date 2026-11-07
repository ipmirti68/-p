
import os
import re
import requests

# Kaynak adresini GitHub Secrets üzerinden al
SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "http://07falcontr.com:8080/get.php?username=x3ulkusinanoba43&password=gNR4DyD4QXsp&type=m3u_plus&output=ts")

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🎥 DİZİ SON BÖLÜM PAZARTESİ"
SOURCE_GROUP = "TR/FILM ► PAZARTESİ"


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
    print("MIRTI68 - PAZARTESİ DİZİ GÜNCELLEME")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL GitHub Secret tanımlanmamış.")
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

        if len(entry) < 2:
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
        print("Kaynak grupta geçerli yayın bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    old_lines = []

    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)

    preserved = [
        entry for entry in old_entries
        if get_group(entry[0]) != FILM_GROUP
    ]

    # Diğer grupların yayın adreslerini koruyarak
    # yeni kayıtların kendi içinde tekrarlanmasını önle.
    seen_urls = set()
    unique_entries = []

    for entry in new_entries:
        url = entry[1]

        if url not in seen_urls:
            seen_urls.add(url)
            unique_entries.append(entry)

    # Ana listeyi yeniden oluştur
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for entry in preserved + unique_entries:
            for line in entry:
                f.write(line + "\n")

    print("GÜNCELLEME TAMAMLANDI")
    print("Yeni kayıt:", len(unique_entries))
    print("Korunan eski kayıt:", len(preserved))
    print("Ana dosya:", M3U_FILE)


if __name__ == "__main__":
    main()
