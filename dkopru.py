import os
import re
import requests

# --- KÖPRÜ KAYNAĞI ---
SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "https://raw.githubusercontent.com/ramazansancar/UzunMuhalefet_Legal-IPTV/refs/heads/main/lists/video/sources/puhutv-com/diziler/kopru.m3u")

M3U_FILE = "mirti68.m3u"

# --- Tek yerden kontrol ---
SERIES_NAME = "Köprü"
TARGET_GROUP = "🟪◆ DİZİLER - KÖPRÜ ⭕"
# --- ---

def get_group(line):
    m = re.search(r'group-title="([^"]*)"', line)
    return m.group(1).strip() if m else ""

def get_channel_name(line):
    if "," in line:
        return line.split(",", 1)[1].strip()
    return ""

def get_stream(entry):
    return next(
        (x.strip() for x in entry[1:] if x.strip().startswith(("http://", "https://"))),
        ""
    )

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

# 1. Sezon - 1. Bölüm -> Köprü S01 E01
def normalize_episode_name(raw_name):
    name = raw_name.strip()

    m_already = re.search(r'[Ss](\d+)\s*[Ee](\d+)', name)
    if m_already:
        s = int(m_already.group(1))
        e = int(m_already.group(2))
        return f"{SERIES_NAME} S{s:02d} E{e:02d}"

    m = re.search(
        r'(\d+)\s*\.?\s*sezon.*?(\d+)\s*\.?\s*b[öo]l[üu]m',
        name, re.IGNORECASE
    )
    if m:
        s = int(m.group(1))
        e = int(m.group(2))
        return f"{SERIES_NAME} S{s:02d} E{e:02d}"

    m2 = re.search(r'(\d+)\s*\.?\s*b[öo]l[üu]m', name, re.IGNORECASE)
    if m2:
        e = int(m2.group(1))
        return f"{SERIES_NAME} S01 E{e:02d}"

    clean = re.sub(r'^\s*k[öo]pr[üu]\s*[-–—:]*\s*', '', name, flags=re.IGNORECASE).strip()
    if clean:
        return f"{SERIES_NAME} - {clean}"
    return SERIES_NAME

def make_key(extinf):
    return normalize_episode_name(get_channel_name(extinf)).lower()

def rename_entry(entry):
    extinf = entry[0]
    old_name = get_channel_name(extinf)
    new_name = normalize_episode_name(old_name)

    new_extinf = re.sub(
        r'group-title="[^"]*"',
        f'group-title="{TARGET_GROUP}"',
        extinf
    )
    if 'group-title=' not in new_extinf:
        new_extinf = new_extinf.replace(
            "#EXTINF:",
            f'#EXTINF:-1 group-title="{TARGET_GROUP}"',
            1
        )
    if "," in new_extinf:
        head, _ = new_extinf.split(",", 1)
        new_extinf = f"{head},{new_name}"

    if 'tvg-name="' in new_extinf:
        new_extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{new_name}"', new_extinf, count=1)

    new_extinf = re.sub(r'\s*tvg-type="[^"]*"', '', new_extinf, count=1)
    new_extinf = re.sub(r'#EXTINF:-?\d+', '#EXTINF:-1 tvg-type="series"', new_extinf, count=1)
    return [new_extinf] + entry[1:]

def main():
    print("=" * 55)
    print(f"MIRTI68 - {TARGET_GROUP}")
    print(f"Series Name: {SERIES_NAME}")
    print("=" * 55)

    try:
        r = requests.get(SOURCE_M3U_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.RequestException as e:
        print("Kaynak okunamadı:", e)
        return

    source_entries = read_entries(r.text.splitlines())
    print(f"Kaynakta toplam kayıt: {len(source_entries)}")

    new_entries = []
    for entry in source_entries:
        if len(entry) < 2:
            continue
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue
        new_entries.append(rename_entry(entry))

    new_entries.sort(key=lambda e: make_key(e[0]))

    print(f"Direkt çekilen: {len(new_entries)}")
    print("--- ÖRNEK ---")
    for e in new_entries[:5]:
        print(f"Grup: {get_group(e[0])} | İsim: {get_channel_name(e[0])}")
    print("--- ---")

    if not new_entries:
        print("Kaynakta yayın bulunamadı.")
        return

    old_entries = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_entries = read_entries(f.read().splitlines())

    final_entries = [list(e) for e in old_entries]

    url_to_index = {}
    name_to_index = {}
    for idx, entry in enumerate(final_entries):
        if get_group(entry[0]) != TARGET_GROUP:
            continue
        url = get_stream(entry)
        if url:
            url_to_index[url] = idx
        key = make_key(entry
