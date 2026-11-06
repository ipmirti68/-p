import re, os, shutil, datetime

def update_group(group_name, new_entries, filename="mirti68.m3u"):
    """
    Güvenli versiyon:
    - Önce yedek alır
    - Yeni liste boşsa hiç dokunmaz
    - Sadece o grubu değiştirir, diğer gruplara dokunmaz
    - Aynı link varsa tekrar eklemez
    """

    # 1. Yeni liste boşsa dosyaya hiç dokunma
    if not new_entries:
        print(f"[!] {group_name}: Yeni liste boş, dosya korunuyor, hiçbir şey silinmedi")
        return False

    # 2. Dosya yoksa sıfırdan oluştur
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n\n" + "\n".join(new_entries) + "\n")
        print(f"[+] {filename} yoktu, sıfırdan oluşturuldu")
        return True

    # 3. Önce yedek al - bu en önemlisi
    backup = filename + ".bak"
    try:
        shutil.copy2(filename, backup)
        print(f"[yedek] {backup} alındı")
    except Exception as e:
        print(f"[!] Yedek alınamadı: {e}")

    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    original_len = len(content)

    # 4. Dosyayı blok blok ayır, regex ile tek seferde silme
    # Her kanal bloğu: #EXTINF satırı + varsa #EXTVLCOPT + link satırı
    lines = content.splitlines()
    kept_lines = []
    i = 0
    removed_count = 0

    while i < len(lines):
        line = lines[i]

        # Bu satır bizim grubumuz mu?
        if line.startswith("#EXTINF") and f'group-title="{group_name}"' in line:
            # Bu bloğu atla, sil
            removed_count += 1
            i += 1
            # Sonraki 1-2 satır VLCOPT veya link ise onları da atla
            while i < len(lines) and (lines[i].startswith("#EXTVLCOPT") or lines[i].startswith("http")):
                i += 1
            continue
        else:
            kept_lines.append(line)
            i += 1

    print(f"[-] {group_name} grubundan {removed_count} eski kanal silindi")

    # 5. Zaten listede olan linkleri tekrar ekleme (çiftleme önleme)
    kept_text = "\n".join(kept_lines)
    clean_new = []
    for entry in new_entries:
        # entry içindeki http linkini bul
        m = re.search(r'https?://[^\s\n]+', entry)
        if m and m.group(0) in kept_text:
            continue
        clean_new.append(entry)

    # 6. Yeni liste çok şüpheli şekilde küçükse ekleme, eskiyi koru
    # Örn: önceden 10 kanal vardı, şimdi 1 kanal geldi -> bir şey ters gitmiş
    if removed_count > 0 and len(clean_new) < removed_count * 0.5:
        print(f"[!] DURDURULDU: Eskiden {removed_count} kanal vardı, şimdi {len(clean_new)} geldi. Dosyaya dokunulmadı, yedekten dönebilirsin.")
        return False

    new_content = "\n".join(kept_lines).rstrip() + "\n\n" + "\n".join(clean_new) + "\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] {group_name}: {len(clean_new)} kanal yazıldı, diğer gruplar korundu. Eski boyut: {original_len} -> Yeni: {len(new_content)}")
    return True
