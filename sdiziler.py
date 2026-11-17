import os
import re
import requests

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

M3U_FILE = "mirti68.m3u"
YAML_FILE = "sdiziler.yaml"

def get_group(line):
    m = re.search(r'group-title="([^"]+)"', line)
    return m.group(1).strip() if m else ""

def get_channel_name(line):
    m = re.search(r',\s*(.*)$', line)
    return m.group(1).strip() if m else ""

def parse_season_episode(name):
    # "1. Sezon - 1. Bölüm" -> (1,1)
    m = re.search(r'(\d+)\s*\.\s*Sezon\s*-\s*(\d+)\s*\.\s*Bölüm', name, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'S(\d+)\s*E(\d+)', name, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None

def load_yaml_manual():
    # yaml bozulsa bile name/group/url satırından okur
    series = []
    cur = {}
    with open(YAML_FILE, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("- name:"):
                if cur.get("url"):
                    series.append(cur)
                cur = {}
                v = line.split(":", 1)[1].strip().strip('"').strip("'")
                cur["name"] = v
            elif line.startswith("group:"):
                v = line.split(":", 1)[1].strip().strip('"').strip("'")
                cur["group"] = v
            elif line.startswith("url:"):
                v = line.split(":", 1)[1].strip().strip('"').strip("'")
                cur["url"] = v
    if cur.get("url"):
        series.append(cur)
    return series

def load_yaml():
    if HAS_YAML:
        try:
            with open(YAML_FILE, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and data.get("series"):
                return data["series"]
        except Exception as e:
            print(f"YAML parse hatası, manuel okunuyor: {e}")
    return load_yaml_manual()

def fetch_m3u(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text.splitlines()

def clean_old_groups(lines, target_groups):
    out = []
    skip = False
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            g = get_group(line)
            if g in target_groups:
                skip = True
                continue
            else:
                skip = False
                out.append(line)
        else:
            if skip:
                # bir sonraki EXTINF'e kadar url satırını atla
                if line.startswith("http"):
                    skip = False
                    continue
                # boş satır vs atla
                continue
            out.append(line)
    return out

def main():
    print("=======================================================")
    print("MIRTI68 - DİZİLER YAML TOPLU ÇEKİM")
    print("=======================================================")
    if not os.path.exists(YAML_FILE):
        print(f"{YAML_FILE} bulunamadı!")
        return
    if not os.path.exists(M3U_FILE):
        print(f"{M3U_FILE} bulunamadı!")
        return

    series_list = load_yaml()
    print(f"{len(series_list)} dizi bulundu: {[s.get('name') for s in series_list]}")

    with open(M3U_FILE, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]

    target_groups = set(s["group"] for s in series_list)
    lines = clean_old_groups(lines, target_groups)

    if not lines or lines[0].strip().startswith("#EXTM3U")
        lines.insert(0, "#EXTM3U")

    for s in series_list:
        name = s["name"]
        group = s["group"]
        url = s["url"]
        print(f"\n-> {name} çekiliyor...")
        try:
            src_lines = fetch_m3u(url)
        except Exception as e:
            print(f"  HATA: {e}")
            continue

        count = 0
        for i, line in enumerate(src_lines):
            if line.startswith("#EXTINF"):
                raw_name = get_channel_name(line)
                sezon, bolum = parse_season_episode(raw_name)
                if sezon is not None:
                    new_name = f"{name} S{sezon:02d} E{bolum:02d}"
                else:
                    new_name = f"{name} - {raw_name}"
                new_inf = f'#EXTINF:-1 tvg-name="{new_name}" group-title="{group}",{new_name}'
                lines.append(new_inf)
                # url satırı
                if i + 1 < len(src_lines):
                    u = src_lines[i + 1].strip()
                    if u and not u.startswith("#"):
                        lines.append(u)
                        count += 1
        print(f"  {count} bölüm eklendi")

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\nBİTTİ")

if __name__ == "__main__":
    main()
