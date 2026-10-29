import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# Sadece calisanlar guncellenecek
backup = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
}

def get_m3u8(url):
    try:
        h = {"User-Agent": "Mozilla/5.0", "Referer": url}
        r = requests.get(url, headers=h, timeout=10)
        m = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        if m:
            return m[0].replace("\\/", "/")
    except:
        pass
    return None

epg_header = "#EXTM3U"
old_blocks = []

if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first = content.splitlines()[0] if content else "#EXTM3U"
        if "url-tvg" in first.lower() or "x-tvg-url" in first.lower() or "#EXTM3U" in first:
            if len(first) > 10:
                epg_header = first.strip()
        parts = content.split("#EXTINF")
        for p in parts[1:]:
            block = "#EXTINF" + p.strip()
            # SADECE yeni grup olan 📺 ULUSAL 🔗'yi sil, diger ULUSAL kalsin ki ATV STAR TV8 silinmesin
            if YENI_GRUP in block:
                continue
            if "http" in block:
                old_blocks.append(block)

print("Eski korunan blok: " + str(len(old_blocks)))
print("EPG: " + epg_header[:80])

final_new = {}
final_new["TRT 1"] = backup["TRT 1"]
for name, site in [
    ("KANAL D", "https://www.kanald.com.tr/canli-yayin"),
    ("SHOW TV", "https://www.showtv.com.tr/canli-yayin"),
    ("NOW TV", "https://www.nowtv.com.tr/canli-yayin"),
    ("KANAL 7", "https://www.kanal7.com/canli-izle")
]:
    link = get_m3u8(site)
    final_new[name] = link if link else backup[name]
    print(name + " -> " + final_new[name][:60])

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    # 1- Yeni 📺 ULUSAL 🔗 grubu - 5 calisan
    for name in ["TRT 1", "KANAL D", "SHOW TV", "NOW TV", "KANAL 7"]:
        url = final_new.get(name)
        logo = logos.get(name, "")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + name + '\n')
        out.write(url + '\n\n')
    # 2- Eski listenin TAMAMI - ATV STAR TV8 dahil bozulmadan
    for b in old_blocks:
        out.write(b + '\n\n')

print("Bitti")
