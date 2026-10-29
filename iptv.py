import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# Sabit yedekler - hicbiri bos kalmasin diye
links = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "ATV": "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "STAR TV": "https://dogus-live.ercdn.net/startv/startv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "TV8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "ATV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "STAR TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
    "TV8": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
}

# Eski listeyi koru
old_list = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            # Eski ULUSAL olmayan kanallari al
            blocks = content.split("#EXTINF")
            for b in blocks[1:]:
                if YENI_GRUP not in b and 'group-title="ULUSAL"' not in b:
                    if "http" in b:
                        old_list.append("#EXTINF" + b.strip())
    except:
        pass

print(f"Eski kanallar korundu: {len(old_list)} blok")

# Yeni dosyayi yaz - HER ZAMAN OLUSUR
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    # 8 ULUSAL
    for name, url in links.items():
        logo = logos.get(name, "")
        tvg_id = name.replace(" ", ".") + ".hd"
        out.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'#EXTVLCOPT:http-referrer=https://www.google.com/\n')
        out.write(f'{url}\n\n')
    
    # Eski diger kategoriler
    for block in old_list:
        if not block.endswith("\n"):
            block += "\n"
        out.write(block + "\n\n")

print(f"Bitti! mirti68.m3u olustu, toplam yeni: {len(links)} + eski: {len(old_list)}")

# Kontrol
size = os.path.getsize(output_file)
print(f"Dosya boyutu: {size} byte")
