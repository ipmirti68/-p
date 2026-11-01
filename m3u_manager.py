
import os
import re
import tempfile

M3U_FILE = "mirti68.m3u"


def parse_entries(text):
    """M3U içeriğini kanal kayıtlarına ayırır."""
    lines = text.splitlines()
    header = []
    entries = []
    current = []

    for line in lines:
        if line.startswith("#EXTM3U"):
            continue

        if line.startswith("#EXTINF:"):
            if current:
                entries.append(current)
            current = [line]

        elif current:
            current.append(line)

        else:
            if line.strip():
                header.append(line)

    if current:
        entries.append(current)

    return header, entries


def entry_title(entry):
    for line in entry:
        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip().casefold()
    return ""


def entry_group(entry):
    for line in entry:
        if line.startswith("#EXTINF:"):
            match = re.search(r'group-title="([^"]*)"', line)
            return match.group(1) if match else ""
    return ""


def update_group(group_title, new_entries, filename=M3U_FILE):
    """
    Aynı isimli kanalı günceller.
    Yeni bulunmayan eski kanalı korur.
    Diğer kategorilere dokunmaz.
    """

    if not new_entries:
        print("Yeni kayıt yok. Mevcut liste korunuyor.")
        return False

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8-sig") as f:
            old_text = f.read()
    else:
        old_text = ""

    header, old_entries = parse_entries(old_text)

    # Yeni kayıtları doğrula ve hazırla
    new_map = {}

    for item in new_entries:
        if isinstance(item, str):
            lines = item.strip().splitlines()
        else:
            lines = [str(x).strip() for x in item]

        if not lines or not any(x.startswith("#EXTINF:") for x in lines):
            print("Geçersiz M3U kaydı atlandı.")
            continue

        if entry_group(lines) != group_title:
            print("Kategori uyuşmazlığı nedeniyle kayıt atlandı.")
            continue

        title = entry_title(lines)

        if title:
            new_map[title] = lines

    if not new_map:
        print("Geçerli yeni kayıt bulunamadı. Eski liste korundu.")
        return False

    # Eski kayıtları koru, aynı isimlileri yenile
    merged = {}
    target_order = []

    for entry in old_entries:
        if entry_group(entry) == group_title:
            title = entry_title(entry)

            if title and title not in merged:
                merged[title] = entry
                target_order.append(title)

    for title, entry in new_map.items():
        if title not in merged:
            target_order.append(title)

        merged[title] = entry

    target_entries = [merged[x] for x in target_order]

    # Diğer kategorileri aynen koru
    output_entries = []
    inserted = False

    for entry in old_entries:
        if entry_group(entry) == group_title:
            if not inserted:
                output_entries.extend(target_entries)
                inserted = True
            continue

        output_entries.append(entry)

    if not inserted:
        output_entries.extend(target_entries)

    # Dosyayı güvenli şekilde hazırla
    output = ["#EXTM3U"]
    output.extend(header)

    for entry in output_entries:
        output.extend(entry)

    final_text = "\n".join(output).rstrip() + "\n"

    directory = os.path.dirname(os.path.abspath(filename))

    fd, temp_path = tempfile.mkstemp(
        prefix="m3u_",
        suffix=".tmp",
        dir=directory
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(final_text)

        os.replace(temp_path, filename)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    print("M3U GÜNCELLENDİ:", filename)
    print("Kategori:", group_title)
    print("Yeni bulunan kayıt:", len(new_map))
    print("Korunan/eski kayıtlarla toplam:", len(target_entries))

    return True
