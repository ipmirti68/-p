import os
import re
import requests

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

M3U_FILE = "mirti68.m3u"
YAML_FILE = "diziler.yaml"

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

def load_yaml():
    if HAS_YAML:
        with open(YAML_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("series", []) if data else []
    # YAML yoksa basit elle okuma
    series = []
    cur = {}
    with open(YAML_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- name:"):
                if cur:
                    series.append(cur)
                cur = {"name": line.split(":", 1)[1].strip().strip('"')}
            elif line.startswith("group:"):
                cur["group"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("url:"):
                cur["url"] = line.split(":", 1)[1].strip().strip('"')
    if cur:
        series.append(cur)
    return series

def normalize_episode_name(raw_name, series_name):
    name = raw_name.strip()

    # Zaten S01 E01 ise
    m_already = re.search(r'[Ss](\d+)\s*[Ee](\d+)', name)
    if m_already:
        s = int(m_already.group(1))
        e = int(m_already.group(2))
        return f"{series_name} S{s:02d} E{e:02d}"

    # 1. Sezon - 1. Bölüm -> S01 E01
    m = re.search(
        r'(\d+)\s*\.?\s*sezon.*?(\d+)\s*\.?\s*b[öo]l[üu]m',
        name, re.IGNORECASE
    )
    if m:
        s = int(m.group(1))
        e = int(m.group(2))
        return f"{series_name} S{s:02d} E{e:02d}"

    # Sadece 1. Bölüm -> S01 E01
    m2 = re.search(r'(\d+)\s*\.?\s*b[öo]l[üu]m', name, re.IGNORECASE)
    if m2:
        e = int(m2.group(1))
        return f"{series_name} S01 E{e:02d}"

    # Dizi ismini baştan temizle
    base = re.escape(series_name.split()[0])
    clean = re.sub(rf'^\s*{base}.*?[-–—:]*\s*', '', name, flags=re.IGNORECASE).strip()
    if clean and clean.lower() != name.lower():
        return f"{series_name} - {clean}"
    if series_name.lower() not in name.lower():
        return f"{series_name} - {name}"
    return name

def rename_entry(entry, series_name, target_group):
    extinf = entry[0]
    new_name = normalize_episode_name(get_channel_name(extinf), series_name)

    new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{target_group}"', extinf)
    if 'group-title=' not in new_extinf:
        new_extinf = new_extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{target_group}"', 1)
    if "," in new_extinf:
        head, _ = new_extinf.split(",", 1)
        new_extinf = f"{head},{new_name}"
    if 'tvg-name="' in new_extinf:
        new_extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{new_name}"', new_extinf, count=1)
    new_extinf = re.sub(r'\s*tvg-type="[^"]*"', '', new_extinf, count=1)
    new_extinf = re.sub(r'#EXTINF:-?\d+', '#EXTINF:-1 tvg-type="series"', new_extinf, count=1)
    return [new_extinf] + entry[1:]

def process_one(series, final_entries):
    name = series["name"]
    target_group = series["group"]
    url = series["url"]
    print(f"\n--- {name} -> {target_group} ---")

    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.RequestException as e:
        print(f"Kaynak okunamadı: {e}")
        return final_entries

    source_entries = read_entries(r.text.splitlines())
    new_entries = []
    for entry in source_entries:
        if len(entry) < 2:
            continue
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue
        new_entries.append(rename_entry(entry, name, target_group))

    def make_key(extinf):
        return normalize_episode_name(get_channel_name(extinf), name).lower()
    new_entries.sort(key=lambda e: make_key(e[0]))

    print(f"Kaynakta: {len(new_entries)} bölüm")
    if new_entries:
        print(f"Örnek: {get_channel_name(new_entries[0][0])}")

    if not new_entries:
        return final_entries

    # Bu dizinin eski halini sil, yenisini ekle
    final_entries = [e for e in final_entries if get_group(e[0]) != target_group]
    final_entries.extend(new_entries)
    print(f"Eklendi: {len(new_entries)}")
    return final_entries

def main():
    print("=" * 55)
    print("MIRTI68 - DİZİLER YAML TOPLU ÇEKİM")
    print("=" * 55)

    series_list = load_yaml()
    print(f"YAML'da {len(series_list)} dizi var")

    old_entries = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_entries = read_entries(f.read().splitlines())

    final_entries = [list(e) for e in old_entries]

    for s in series_list:
        final_entries = process_one(s, final_entries)

    # --- YENİ: YAML'dan çıkarılan grupları listeden de sil ---
    wanted_groups = {s["group"] for s in series_list}
    cleaned = []
    removed_groups = set()
    for e in final_entries:
        g = get_group(e[0])
        # Sadece 🟪◆ DİZİLER ile başlayanlara dokun, beIN / film gruplarına dokunma
        if g.startswith("🟪◆ DİZİLER") and g not in wanted_groups:
            removed_groups.add(g)
            continue
        cleaned.append(e)
    final_entries = cleaned

    if removed_groups:
        print(f"\nYAML'dan çıkarıldığı için silinen gruplar: {removed_groups}")
    # --- ---

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print("\nGÜNCELLEME TAMAMLANDI")
    print(f"Toplam kayıt: {len(final_entries)}")

if __name__ == "__main__":
    main()
