import os
import re
import requests
import tempfile

# ==========================================
# MIRTI68 - ATOM 【entity-beIN SPORTS¦canonical_name=beIN SPORTS】 - SADECE SONA EKLE
# Senin listene DOKUNMAZ
# ==========================================

SOURCE_M3U_URL = os.environ.get(
    "SOURCE_M3U_URL",
    "https://raw.githubusercontent.com/smtv62/atomspor/refs/heads/main/atom.m3u"
)

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟩◆  beIN SPORTS 🖥"
BEIN_LOGO = "https://i.imgur.com/71TSn0Q.jpeg"

def get_channel_name(line):
    if "," in line:
        return line.split(",", 1)[1].strip()
    return ""

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
        (line.strip() for line in entry[1:] if line.startswith(("http://", "https://"))),
        ""
    )

def add_red_dot(extinf):
    if "," not in extinf:
        return extinf
    head, display = extinf.split(",", 1)
    display = display.strip()
    if display.endswith("⭕"):
        return extinf
    return f"{head},{display} -Atom ⭕"

def set_logo(extinf):
    if 'tvg-logo="' in extinf:
        extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{BEIN_LOGO}"', extinf, count=1)
    elif extinf.startswith("#EXTINF:"):
        extinf = re.sub(
            r'(#EXTINF:-?\d+)',
            rf'\1 tvg-logo="{BEIN_LOGO}"',
            extinf,
            count=1
        )
    return extinf

def update_group(extinf):
    # Sadece YENİ eklenecek kanala uygulanır, eski listeye uygulanmaz
    extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
    if "group-title=" not in extinf:
        extinf = extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)
    extinf = set_logo(extinf)
    return extinf

def main():
    print("=" * 55)
    print("MIRTI68 - beIN SPORTS - SADECE SONA EKLE")
    print("=" * 55)

    try:
        response = requests.get(SOURCE_M3U_URL, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        response.encoding = "utf-8"
    except requests.RequestException as e:
        print("Kaynak liste okunamadı:", e)
        print("Ana liste değiştirilmedi.")
        return

    source_entries = read_entries(response.text.splitlines())
    new_entries = []

    for entry in source_entries:
        if not entry:
            continue
        extinf = entry[0]
        channel_name = get_channel_name(extinf).lower()
        if "bein sports" not in channel_name:
            continue
        stream = get_stream(entry)
        if not stream:
            continue
        # Sadece yeni kanala grup/logo/dot uygula
        new_entries.append([add_red_dot(update_group(extinf)), stream])

    if not new_entries:
        print("beIN Sports kanalı bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    print("Kaynak 【entity-beIN Sports¦canonical_name=beIN SPORTS】:", len(new_entries))

    # --- SENİN LİSTENİ OLDUĞU GİBİ OKU, HİÇ DEĞİŞTİRME ---
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8-sig") as f:
            old_content = f.read()
        old_lines = old_content.splitlines()
    else:
        old_lines = ["#EXTM3U"]
        old_content = "#EXTM3U\n"

    # Zaten sende olan URL'leri atla ki 2 kere eklenmesin
    old_entries = read_entries(old_lines)
    existing_urls = set()
    for entry in old_entries:
        url = get_stream(entry)
        if url:
            existing_urls.add(url)

    to_append = []
    skipped = 0
    for entry in new_entries:
        url = get_stream(entry)
        if url in existing_urls:
            skipped += 1
            continue
        to_append.append(entry)
        existing_urls.add(url)

    print(f"Zaten sende var, atlandı: {skipped}")
    print(f"Sona eklenecek yeni: {len(to_append)}")

    if not to_append:
        print("Eklenecek yeni kanal yok. Liste değiştirilmedi.")
        return

    # --- SADECE SONA EKLE ---
    directory = os.path.dirname(os.path.abspath(M3U_FILE))
    fd, temp_path = tempfile.mkstemp(prefix="mirti68_", suffix=".m3u", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # Eski dosyayı aynen yaz
            text = old_content.rstrip("\n") + "\n"
            if not text.startswith("#EXTM3U"):
                text = "#EXTM3U\n" + text
            f.write(text)
            # Yeni kanalları en sona ekle
            for entry in to_append:
                for line in entry:
                    f.write(line + "\n")
        os.replace(temp_path, M3U_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print("=" * 55)
    print("TAMAMLANDI - Eski listeye dokunulmadı")
    print("=" * 55)
    print("Sona eklenen:", len(to_append))
    print("Grup:", FILM_GROUP)
    print("Ana liste:", M3U_FILE)

if __name__ == "__main__":
    main()
