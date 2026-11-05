import re, os

def update_group(group_name, new_entries, filename="mirti68.m3u"):
    """
    group-title="GRUP" olan bloklari silip yeni entries ile degistirir
    Diger gruplari korur, dosyayi silmez
    """
    if not os.path.exists(filename):
        with open(filename,"w",encoding="utf-8") as f:
            f.write("#EXTM3U\n\n" + "\n".join(new_entries) + "\n")
        return

    with open(filename,"r",encoding="utf-8",errors="ignore") as f:
        content = f.read()

    # group-title="BEIN" olan tum EXTINF + URL bloklarini sil
    pattern = re.compile(r'#EXTINF.*group-title="%s".*\n.*\n.*m3u8.*\n?' % re.escape(group_name), re.IGNORECASE)
    # daha genis pattern: group-title iceren 2-3 satirlik blok
    pattern2 = re.compile(r'#EXTINF[^\n]*group-title="%s"[^\n]*\n(?:#EXTVLCOPT[^\n]*\n)?[^\n]*m3u8[^\n]*\n?' % re.escape(group_name), re.IGNORECASE)
    
    # once dar pattern sonra genis
    new_content = pattern2.sub("", content)
    # eger hala ayni ise eski pattern
    if new_content == content:
        new_content = pattern.sub("", new_content)
    
    # bos satirlari temizle ama dosya yapisini koru
    new_content = new_content.rstrip() + "\n\n" + "\n".join(new_entries) + "\n"
    
    # eger dosya cok kuculduyse (silme oldu) geri al
    if len(new_content) < 80000 and len(content) > 80000:
        print(f"[!] m3u_manager: dosya cok kuculdu {len(content)} -> {len(new_content)}, koruma devreye girdi")
        # sadece eski grubu silmeden ekle
        new_content = content.rstrip() + "\n\n" + "\n".join(new_entries) + "\n"
    
    with open(filename,"w",encoding="utf-8") as f:
        f.write(new_content)
    print(f"[m3u_manager] {group_name}: {len(new_entries)} kanal yazildi, dosya korundu")
