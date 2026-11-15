import os
import re
import tempfile
import requests

INPUT_M3U = "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u"
OUTPUT_M3U = "mirti68.m3u"

# SADECE BU GRUPLAR EKLENECEK - YABANCI TR DB CIKARILDI
WANTED_RAW = [
    "【entity-IMDb¦canonical_name=IMDb】 Top Rated",
    "YERLI FILM",
    "KEMAL SUNAL",
    "KORKU",
    "WESTERN",
    "Yeni Eklenenler",
    "2026",
    "2025",
    "2023 2024",
    "2021",
    "2019 2020",
    "2017 2018",
    "2015 2016",
    "2013 2014",
    "2011 2012",
    "2022",
    "2001 2010",
]

def norm(s):
    s = re.sub(r"\s+", " ", s).strip().lower()
    for e in ["✨", "💥", "💎", "🔥", "💢"]:
        s = s.replace(e, "")
    return re.sub(r"\s+", " ", s).strip()

WANTED = {norm(x): x for x in WANTED_RAW}

EXCLUDED = [
    " 【entity-adam sandler¦canonical_name=adam sandler】",
    "clint eastwood",
    " 【entity-sylvester stallone¦canonical_name=sylvester stallone】",
    "【entity-jackie chan¦canonical_name=jackie chan】",
    "nicolas cage",
    " 【entity-steven seagal¦canonical_name=steven seagal】",
    " 【entity-jason statham¦canonical_name=jason statham】",
    "seri",
    "dizi",
    "series",
    "sezon",
    "season",
    "episode",
    "bölüm",
    "bolum",
    "s01e",
    "s02e",
    "s03e",
]

def read_entries(lines):
    entries = []
    current = []
    for line in lines:
        line = line.rstrip("\n")
        if line.strip().startswith("#EXTINF:"):
            if current:
                entries.append(current)
            current = [line]
        elif current and line.strip():
            current.append(line)
    if current:
        entries.append(current)
    return entries

def get_stream(entry):
    return next(
        (line.strip() for line in entry[1:] if line.strip().startswith(("http://", "https://"))),
        ""
    )

def get_group(entry):
    joined = "\n".join(entry)
    m = re.search(r'group-title="([^"]*)"', joined, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()

def rename_group(entry):
    g = get_group(entry)
    if not g:
        return entry
    clean = WANTED.get(norm(g), g)
    clean = re.sub(r"\s+", " ", clean).strip()
    new_group = f"🟪◆ {clean} ⭕"
    out = []
    done = False
    for line in entry:
        if not done and 'group-title="' in line:
            line = re.sub(r'group-title="[^"]*', f'group-title="{new_group}', line, count=1)
            done = True
        out.append(line)
    return out

def is_movie(entry):
    if not entry:
        return False
    joined = "\n".join(entry)
    name = joined.split(",", 1)[-1].strip() if "," in joined else ""
    g = get_group(entry)
    if not g:
        return False
    if norm(g) not in WANTED:
        return False
    if any(word in g.casefold() for word in EXCLUDED):
        return False
    if any(word in name.casefold() for word in EXCLUDED):
        return False
    return True

def download_m3u(url):
    urls = [url, "https://cdn.jsdelivr.net/gh/GitLatte/patr0n@site/lists/power-sinema.m3u"]
    headers = {"User-Agent": "Mozilla/5.0"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=60)
            print(f"Indirildi: {u} -> status: {r.status_code} len: {len(r.text)}")
            if r.status_code == 200 and "#EXTM3U" in r.text[:500]:
                return r.text
        except Exception as e:
            print(f"Indirme hatasi {u}: {e}")
    return None

def write_atomic(lines):
    directory = os.path.dirname(os.path.abspath(OUTPUT_M3U)) or "."
    fd, temp_path = tempfile.mkstemp(prefix="mirti68_", suffix=".m3u", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for line in lines:
                f.write(line + "\n")
        os.replace(temp_path, OUTPUT_M3U)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

def main():
    if INPUT_M3U.startswith("http://") or INPUT_M3U.startswith("https://"):
        text = download_m3u(INPUT_M3U)
        if not text:
            print(f"{INPUT_M3U} bulunamadi / indirilemedi.")
            return
        source_entries = read_entries(text.splitlines())
    else:
        if not os.path.exists(INPUT_M3U):
            print(f"{INPUT_M3U} bulunamadi.")
            return
        with open(INPUT_M3U, "r", encoding="utf-8-sig") as f:
            source_entries = read_entries(f.read().splitlines())

    # ESKI LISTEYE HIC DOKUNMA - OLDUGU GIBI KORU
    old_entries = []
    if os.path.exists(OUTPUT_M3U):
        with open(OUTPUT_M3U, "r", encoding="utf-8-sig") as f:
            old_entries = read_entries(f.read().splitlines())

    seen_urls = {get_stream(e) for e in old_entries if get_stream(e)}

    added = []
    filtered = 0
    for entry in source_entries:
        if not get_stream(entry):
            continue
        if not is_movie(entry):
            filtered += 1
            continue
        if get_stream(entry) not in seen_urls:
            seen_urls.add(get_stream(entry))
            added.append(rename_group(entry))

    if not added:
        print("Yeni film yok. Eski liste aynen duruyor, hicbir sey silinmedi.")
        print(f"Toplam (eski): {len(old_entries)}")
        return

    final_lines = []
    for e in old_entries:
        final_lines.extend(e)
    for e in added:
        final_lines.extend(e)

    write_atomic(final_lines)
    print(f"Eski liste korundu: {len(old_entries)}")
    print(f"Yeni eklenen: {len(added)}")
    print(f"Filtrelenen / atlanan: {filtered}")
    print(f"Toplam: {len(old_entries) + len(added)}")

if __name__ == "__main__":
    main()
