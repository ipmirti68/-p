import os
import re
import requests
import tempfile

# ==========================================
# MIRTI68 - tv724 BEIN SPORTS GUNCELLEME
# Bu listeden alir: BEIN + BEİN + EXTVLCOPT + ayni URL'li farkli kanallar
# ==========================================

SOURCE_M3U_URL = os.environ.get(
    "SOURCE_M3U_URL",
    "https://raw.githubusercontent.com/kadirsener1/livetv/cbb795920a991c5d694b5ba9740336e30d29604b/tv247tr.m3u"
)

# Attigin listeyi kaynak.m3u diye kaydedersen ondan okur, yoksa linkten indirir
LOCAL_SOURCE = "kaynak.m3u"
M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟩◆  beIN SPORTS 🖥"
# ==========================================
# M3U YARDIMCI FONKSIYONLARI
# ==========================================

def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""

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
        (
            line.strip()
            for line in entry[1:]
            if line.startswith(("http://", "https://"))
        ),
        ""
    )

def norm_tr(s):
    # BEİN -> 【entity-BEIN¦canonical_name=BEIN】 sorunu: Turkce I harfini duzelt
    # Önce buyuk I'lari duzelt, sonra kucult
    s = s.replace("İ", "I").replace("ı", "i")
    s = s.replace("BEİN", "BEIN").replace("Bein", "Bein")
    # Tum harfleri kucult, sonra tekrar kontrol
    low = s.lower()
    low = low.replace("beın", "bein")
    # Bosluk, tire, alt cizgi sil: beinsports1 oluyor
    return re.sub(r'[^a-z0-9]', '', low)

def make_channel_key(extinf):
    # -TV, -BS, -A, -B, -Z, -M eklerini SILME
    # Yoksa 【entity-BEIN SPORTS¦canonical_name=BEIN】 1-TV ile 【entity-BEIN SPORTS¦canonical_name=BEIN】 1-BS ayni sanilir
    name = get_channel_name(extinf)
    name = name.replace("⭕", "")
    name = re.sub(r'\s+', ' ', name)
    return norm_tr(name)

def is_bein(entry):
    # Sadece virgülden sonraki isme degil, tum satıra bak
    # tvg-name, group-title dahil
    txt = norm_tr(entry[0])
    return "BEIN" in txt

def has_red_dot(extinf):
    return get_channel_name(extinf).strip().startswith("⭕")

def add_red_dot(extinf):
    if "," not in extinf:
        return extinf
    head, display = extinf.split(",", 1)
    display = display.strip()
    if display.endswith("⭕"):
        return extinf
    return f"{head},{display} - ⭕"

def update_group(extinf):
    if 'group-title="' in extinf:
        extinf = re.sub(
            r'group-title="[^"]*"',
            lambda m: f'group-title="{FILM_GROUP}"',
            extinf
        )
    else:
        # #EXTINF: diye degistirme, #EXTINF:-1 den sonra ekle
        extinf = extinf.replace(
            "#EXTINF:-1",
            f'#EXTINF:-1 group-title="{FILM_GROUP}"',
            1
        )
    return extinf

# ==========================================
# ANA ISLEM
# ==========================================

def main():
    print("=" * 55)
    print("MIRTI68 - ATOM 【entity-beIN SPORTS¦canonical_name=BEIN】 BOT")
    print("=" * 55)

    # 1. Kaynak listeyi al
    source_text = ""
    if os.path.exists(LOCAL_SOURCE):
        print(f"Kaynak dosyadan okunuyor: {LOCAL_SOURCE}")
        with open(LOCAL_SOURCE, "r", encoding="utf-8-sig", errors="ignore") as f:
            source_text = f.read()
    else:
        try:
            response = requests.get(
                SOURCE_M3U_URL,
                timeout=40,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()
            response.encoding = "utf-8"
            source_text = response.text
        except requests.RequestException as e:
            print("Kaynak liste okunamadi:", e)
            print("Ana liste degistirilmedi.")
            return

    source_entries = read_entries(source_text.splitlines())
    new_entries = []

    # ==========================================
    # SADECE 【entity-beIN¦canonical_name=BEIN】 KANALLARINI AL - BEİN dahil
    # ==========================================

    for entry in source_entries:
        if not entry:
            continue
        extinf = entry[0]
        if not is_bein(entry):
            continue
        stream = get_stream(entry)
        if not stream:
            continue
        new_extinf = update_group(extinf)
        # EXTVLCOPT satirlarini koru: [extinf, stream] yapma
        rest = entry[1:]
        new_entry = [new_extinf] + rest
        new_entries.append(new_entry)

    if not new_entries:
        print("【entity-beIN Sports¦canonical_name=BEIN】 kanali bulunamadi.")
        print("Ana liste degistirilmedi.")
        return

    print("Kaynak 【entity-beIN Sports¦canonical_name=BEIN】:", len(new_entries))

    # ==========================================
    # MEVCUT ANA LISTEYI OKU
    # ==========================================

    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8-sig") as f:
            old_lines = f.read().splitlines()
    else:
        old_lines = ["#EXTM3U"]

    old_entries = read_entries(old_lines)

    existing_group = [
        entry
        for entry in old_entries
        if get_group(entry[0]) == FILM_GROUP
    ]

    # ==========================================
    # URL + ISIM ILE AKILLI GUNCELLEME
    # Ayni URL farkli isimse silme, ikisini de tut
    # ==========================================

    channel_map = {}
    name_map = {}

    for entry in existing_group:
        url = get_stream(entry)
        name = make_channel_key(entry[0])
        if not url:
            continue
        key = (url, name)
        if key not in channel_map:
            channel_map[key] = entry
        if name and name not in name_map:
            name_map[name] = key

    added_count = 0
    updated_count = 0

    for entry in new_entries:
        url = get_stream(entry)
        name = make_channel_key(entry[0])
        if not url:
            continue
        key = (url, name)

        # Ayni URL + ayni isim zaten varsa tekrar ekleme
        if key in channel_map:
            continue

        # Ayni isim farkli URL ise eski yayini guncelle
        # Ama -TV, -BS, -A, -B gibi ekler farkliysa isim farkli sayilir, o yuzden buraya dusmez
        if name in name_map:
            old_key = name_map[name]
            if old_key in channel_map:
                old_entry = channel_map.pop(old_key)
                new_entry = entry
                if has_red_dot(old_entry[0]):
                    new_entry = [add_red_dot(entry[0])] + entry[1:]
                channel_map[key] = new_entry
                name_map[name] = key
                updated_count += 1
        else:
            new_entry = [add_red_dot(entry[0])] + entry[1:]
            channel_map[key] = new_entry
            name_map[name] = key
            added_count += 1

    updated_group = list(channel_map.values())

    # ==========================================
    # GRUBUN ESKI YERINI KORU
    # ==========================================

    final_lines = []
    inserted = False
    i = 0
    while i < len(old_lines):
        line = old_lines[i].strip()
        if line.startswith("#EXTINF:"):
            entry = [line]
            i += 1
            while i < len(old_lines):
                next_line = old_lines[i].strip()
                if next_line.startswith("#EXTINF:"):
                    break
                if next_line:
                    entry.append(next_line)
                i += 1
            if get_group(entry[0]) == FILM_GROUP:
                if not inserted:
                    for new_entry in updated_group:
                        final_lines.extend(new_entry)
                    inserted = True
            else:
                final_lines.extend(entry)
        else:
            if line and line != "#EXTM3U":
                final_lines.append(line)
            i += 1

    if not inserted:
        for entry in updated_group:
            final_lines.extend(entry)

    # ==========================================
    # DOSYAYI GUVENLI KAYDET
    # ==========================================

    directory = os.path.dirname(os.path.abspath(M3U_FILE))
    fd, temp_path = tempfile.mkstemp(prefix="mirti68_", suffix=".m3u", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for line in final_lines:
                f.write(line + "\n")
        os.replace(temp_path, M3U_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print("=" * 55)
    print("MIRTI68 GUNCELLEME TAMAMLANDI")
    print("=" * 55)
    print("Kaynak 【entity-beIN Sports¦canonical_name=BEIN】:", len(new_entries))
    print("Yeni kanal:", added_count)
    print("Guncellenen kanal:", updated_count)
    print("Son grup kanal:", len(updated_group))
    print("Grup yeri korundu:", FILM_GROUP)
    print("Ana liste:", M3U_FILE)
    print("=" * 55)

if __name__ == "__main__":
    main()
