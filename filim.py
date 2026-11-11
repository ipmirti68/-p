import os
import re
import tempfile
import requests

# KENDİ YASAL LİSTENİ BURAYA YAZ
INPUT_M3U = "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u"
OUTPUT_M3U = "mirti68.m3u"

EXCLUDED = [
    "【entity-adam sandler¦canonical_name=adam sandler】",
    "clint eastwood",
    "【entity-sylvester stallone¦canonical_name=sylvester stallone】",
    "【entity-jackie chan¦canonical_name=jackie chan】",
    "nicolas cage",
    "【entity-steven seagal¦canonical_name=steven seagal】",
    "【entity-jason statham¦canonical_name=jason statham】",
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

def is_movie(entry):
    if not entry:
        return False
    extinf = entry[0]
    name = extinf.split(",", 1)[-1].strip()

    group_match = re.search(r'group-title="([^"]*)"', extinf, re.IGNORECASE)
    if group_match:
        group_name = group_match.group(1).casefold()
        if any(word in group_name for word in EXCLUDED):
            return False

    if any(word in name.casefold() for word in EXCLUDED):
        return False
    return True

def download_m3u(url):
    # Önce normal link, olmazsa yedek link
    urls = [
        url,
        "https://cdn.jsdelivr.net/gh/GitLatte/patr0n@site/lists/power-sinema.m3u",
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=60)
            print(f"Indirildi: {u} -> status: {r.status_code} len: {len(r.text)}")
            if r.status_code == 200 and "#EXTM3U" in r.text[:500]:
                return r.text
        except Exception as e:
            print(f"Indirme hatası {u}: {e}")
    return None

def main():
    # URL ise indir, yerel dosya ise dosyadan oku
    if INPUT_M3U.startswith("http://") or INPUT_M3U.startswith("https://"):
        text = download_m3u(INPUT_M3U)
        if not text:
            print(f"{INPUT_M3U} bulunamadı / indirilemedi.")
            return
        source_entries = read_entries(text.splitlines())
    else:
        if not os.path.exists(INPUT_M3U):
            print(f"{INPUT_M3U} bulunamadı.")
            return
        with open(INPUT_M3U, "r", encoding="utf-8-sig") as f:
            source_entries = read_entries(f.read().splitlines())

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
            added.append(entry)

    if not added:
        print("Yeni film yok. Liste zaten güncel.")
        return

    final_lines = []
    for e in old_entries:
        final_lines.extend(e)
    for e in added:
        final_lines.extend(e)

    directory = os.path.dirname(os.path.abspath(OUTPUT_M3U))
    fd, temp_path = tempfile.mkstemp(prefix="mirti68_", suffix=".m3u", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for line in final_lines:
                f.write(line + "\n")
        os.replace(temp_path, OUTPUT_M3U)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print(f"Yeni eklenen: {len(added)}")
    print(f"Filtrelenen: {filtered}")
    print(f"Toplam: {len(old_entries) + len(added)}")

if __name__ == "__main__":
    main()
