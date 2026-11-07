
import os
import re
import requests
import tempfile

# ==========================================
# MIRTI68 - TÜM FİLMLERİ ANA LİSTEYE EKLE
# ==========================================

SOURCE_M3U_URL = os.environ.get(
    "SOURCE_M3U_URL",
    "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u"
)

M3U_FILE = "mirti68.m3u"


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


def get_stream(entry):
    return next(
        (
            line.strip()
            for line in entry[1:]
            if line.startswith(("http://", "https://"))
        ),
        ""
    )


def is_movie(entry):
    if not entry:
        return False

    extinf = entry[0].lower()
    name = extinf.split(",", 1)[-1].strip()

    # Dizi/seri bölümlerini film listesinden ayır
    excluded = [
        "sezon",
        "season",
        "episode",
        "bölüm",
        "bolum",
        "s01e",
        "s02e",
        "s03e",
    ]

    if any(word in name for word in excluded):
        return False

    return True


def main():

    print("=" * 55)
    print("MIRTI68 - TÜM FİLM LİSTESİ")
    print("=" * 55)

    # Kaynak listeyi indir
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

    source_entries = read_entries(
        response.text.splitlines()
    )

    # Bütün geçerli film kayıtlarını al
    new_entries = []

    for entry in source_entries:

        if not get_stream(entry):
            continue

        if not is_movie(entry):
            continue

        new_entries.append(entry)

    if not new_entries:
        print("Kaynakta geçerli film bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    # Mevcut ana listeyi oku
    old_lines = []

    if os.path.exists(M3U_FILE):
        with open(
            M3U_FILE,
            "r",
            encoding="utf-8-sig"
        ) as f:
            old_lines = f.read().splitlines()

    old_entries = read_entries(old_lines)

    # Mevcut yayın URL'lerini koru
    seen_urls = set()

    for entry in old_entries:
        url = get_stream(entry)

        if url:
            seen_urls.add(url)

    # Sadece yeni URL'leri ekle
    added_entries = []

    for entry in new_entries:

        url = get_stream(entry)

        if url and url not in seen_urls:

            seen_urls.add(url)
            added_entries.append(entry)

    if not added_entries:
        print("Yeni film bulunamadı. Liste zaten güncel.")
        return

    # Mevcut listeyi aynen koru
    final_lines = []

    for entry in old_entries:
        final_lines.extend(entry)

    # Yeni filmleri kaynak gruplarıyla ekle
    for entry in added_entries:
        final_lines.extend(entry)

    # Güvenli dosya yazımı
    directory = os.path.dirname(
        os.path.abspath(M3U_FILE)
    )

    fd, temp_path = tempfile.mkstemp(
        prefix="mirti68_",
        suffix=".m3u",
        dir=directory
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as f:

            f.write("#EXTM3U\n")

            for line in final_lines:
                f.write(line + "\n")

        os.replace(temp_path, M3U_FILE)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print("=" * 55)
    print("FİLM GÜNCELLEME TAMAMLANDI")
    print("=" * 55)
    print("Kaynak film:", len(new_entries))
    print("Yeni eklenen:", len(added_entries))
    print("Mevcut kayıt:", len(old_entries))
    print("Ana dosya:", M3U_FILE)
    print("=" * 55)


if __name__ == "__main__":
    main()
