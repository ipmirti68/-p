#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIRTI TV - TEK ADRES / KATEGORILI M3U
Kaynak dosyalari degistirmez. Mevcut otomatik listeleri birlestirip
Tivimate ve Televizo icin tek MIRTI_TV.m3u olusturur.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "MIRTI_TV.m3u"

# Ana liste ilk sirada tutulur. Diger otomatik listeler eksik kalan
# film/dizi/spor iceriklerini tamamlar. URL tekrarlarina izin verilmez.
SOURCES = [
    "mirti68.m3u",
    "mirti.m3u",
    "film.tmp.m3u",
    "atvdizi.m3u",
    "showdizi.m3u",
    "kanalddizi.m3u",
    "stardizi.m3u",
    "spor.m3u",
    "a.m3u",
    "atv.m3u",
    "atom.m3u",
    "esref_ruya.m3u",
    "hayat_bilgisi.m3u",
    "ihlamurlar_altinda.m3u",
    "ikinci_bahar.m3u",
    "ikincibhr.m3u",
    "kinali_kar.m3u",
    "sbaba.m3u",
    "yilan_hikayesi.m3u",
]

def read_playlist(path: Path):
    try:
        data = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return [], []
    lines = [line.strip("\ufeff\r") for line in data.splitlines()]
    lines = [line for line in lines if line.strip()]
    first = next((i for i, line in enumerate(lines) if line.startswith("#EXTINF:")), len(lines))
    header = lines[:first]
    body = lines[first:]
    records, current = [], []
    for line in body:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []
        if current or line.startswith("#EXTINF:"):
            current.append(line)
    if current:
        records.append(current)
    return header, records

def media_url(record):
    for line in record:
        value = line.strip()
        if value and not value.startswith("#") and re.match(r"^(https?|rtmp|rtsp|udp|ftp)://", value, re.I):
            return value
    return ""

def clean_group(value):
    value = re.sub(r"[🟪🟨🟩🟦🟧🟫⬜⬛🟥🩷◆📺🎬⚽⭕🏟️📡📰]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" -|")
    value = re.sub(r"\s+", " ", value)
    return value

def categorized_group(record):
    for i, line in enumerate(record):
        if not line.startswith("#EXTINF:"):
            continue
        match = re.search(r'group-title="([^"]*)"', line, re.I)
        group = match.group(1).strip() if match else ""
        low = group.casefold()
        clean = clean_group(group)

        is_movie = any(word in low for word in ("film", "f\u0131lm", "filim", "sinema", "movie", "cinema"))
        is_series = any(word in low for word in ("dizi", "d\u0131z\u0131", "series", "serial"))

        # tvg-type=movie bilgisini de kullan.
        if not is_movie and re.search(r'tvg-type="movie"|type="video"', line, re.I):
            name = line.rsplit(",", 1)[-1].casefold()
            if any(word in low for word in ("sinema", "film")) or "tvg-type=\"movie\"" in line.casefold():
                is_movie = True

        if is_movie:
            clean = re.sub(r"^(FILMLER?|F\u0130LMLER?|F\u0130L\u0130MLER?)\s*[/:\-]?\s*", "", clean, flags=re.I)
            clean = re.sub(r"\s+", " ", clean).strip(" -|")
            new_group = "🎬 FİLMLER" + (f" | {clean}" if clean else "")
        elif is_series:
            clean = re.sub(r"^(DIZI|D\u0130Z\u0130|DIZILER|D\u0130Z\u0130LER)\s*[/:\-]?\s*", "", clean, flags=re.I)
            clean = re.sub(r"\s+", " ", clean).strip(" -|")
            new_group = "📺 DİZİLER" + (f" | {clean}" if clean else "")
        else:
            return record

        if match:
            record[i] = line[:match.start(1)] + new_group + line[match.end(1):]
        else:
            # group-title yoksa EXTINF satirina ekle.
            comma = line.rfind(",")
            if comma >= 0:
                record[i] = line[:comma] + f' group-title="{new_group}"' + line[comma:]
            else:
                record[i] = line + f' group-title="{new_group}"'
        return record
    return record

def main():
    if not (ROOT / "mirti68.m3u").is_file() or (ROOT / "mirti68.m3u").stat().st_size == 0:
        sys.exit("[HATA] Ana kaynak mirti68.m3u bulunamadi veya bos. Eski cikti korunuyor.")

    header = ["#EXTM3U"]
    seen_urls = set()
    output_records = []
    source_stats = []

    for filename in SOURCES:
        path = ROOT / filename
        if not path.is_file() or path.stat().st_size == 0:
            continue
        source_header, records = read_playlist(path)
        if filename == "mirti68.m3u":
            # EPG tanimlarini ana listeden koru.
            header = [line for line in source_header if line.startswith("#EXTM3U")]
            if not header:
                header = ["#EXTM3U"]
        added = 0
        for original in records:
            url = media_url(original)
            if not url or url in seen_urls:
                continue
            record = categorized_group(list(original))
            output_records.append(record)
            seen_urls.add(url)
            added += 1
        source_stats.append(f"{filename}: {added} yeni kayit")

    if not output_records:
        sys.exit("[HATA] Hic yayin kaydi bulunamadi. Eski cikti korunuyor.")

    temp = OUTPUT.with_suffix(".m3u.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        for line in header:
            f.write(line + "\n")
        for record in output_records:
            for line in record:
                f.write(line + "\n")
    temp.replace(OUTPUT)

    movie_count = sum(1 for r in output_records if any('group-title="🎬 FİLMLER' in x for x in r))
    series_count = sum(1 for r in output_records if any('group-title="📺 DİZİLER' in x for x in r))
    print("[OK] MIRTI_TV.m3u olusturuldu")
    print(f"[TOPLAM] {len(output_records)} kayit | Film: {movie_count} | Dizi: {series_count}")
    print("[KAYNAKLAR]")
    for item in source_stats:
        print(" - " + item)

if __name__ == "__main__":
    main()
