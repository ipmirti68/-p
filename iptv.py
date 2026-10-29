import os
import requests
import re

# Senin formatin
channel_info = {
    "ATV": ["ATV.hd", "ATV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "ULUSAL", "ATV"],
    "STAR TV": ["Star.TV.hd", "Star TV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "ULUSAL", "Star TV"],
    "NOW TV": ["NOW.TV.hd", "NOW TV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "ULUSAL", "NOW TV"],
    "KANAL 7": ["Kanal.7.hd", "Kanal 7.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "ULUSAL", "Kanal 7"],
    "TV8": ["TV8.hd", "TV8.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "ULUSAL", "TV8"],
    "TRT 1": ["TRT.1.hd", "TRT 1.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "ULUSAL", "TRT 1"],
    "SHOW TV": ["Show.TV.hd", "Show TV.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "ULUSAL", "Show TV"],
    "KANAL D": ["Kanal.D.hd", "Kanal D.tr", "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "ULUSAL", "Kanal D"],
}

# GARANTI CALISAN YEDEKLER - iptv-org bulamazsa bunlar girer
fallback = {
    "ATV": "https://trkvz-live.ercdn.net/atv/atv.m3u8",
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "TV8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
    "STAR TV": "https://dogus-live.ercdn.net/startv/startv.m3u8",
    "NOW TV": "https://foxtv-live.ercdn.net/foxtv/foxtv.m3u8",
    "KANAL 7": "https://kanal7-live.ercdn.net/kanal7/kanal7.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
}

output_file = "mirti68.m3u"

print("iptv-org listesi cekiliyor...")
try:
    r = requests.get("https://iptv-org.github.io/iptv/countries/tr.m3u", timeout=20)
    tr_list = r.text
except:
    tr_list = ""

def find_in_iptvorg(name):
    # iptv-org icinde EXTINF ile linki bul
    pattern = r'#EXTINF.*' + re.escape(name) + r'.*\n(https?://[^\n]+)'
    m = re.search(pattern, tr_list, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

# Eski listeyi koru
old_channels = {}
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                if i+1 < len(lines):
                    link = lines[i+1].strip()
                    if link.startswith("http"):
                        old_channels[lines[i].strip()] = link
    print(f"Eski liste korundu: {len(old_channels)} kanal")

updated = {}
for key in channel_info:
    print(f"Kontrol: {key}")
    link = find_in_iptvorg(key)
    if not link:
        # isim farkli olabilir ATV icin "ATV" diye ara
        short = key.split()[0]
        link = find_in_iptvorg(short)
    if not link:
        print(f"  -> iptv-org'da bulunamadi, yedek kullaniliyor")
        link = fallback.get(key)
    
    if link:
        info = channel_info[key]
        extinf = '#EXTINF:-1 tvg-id="' + info[0] + '" tvg-name="' + info[1] + '" tvg-logo="' + info[2] + '" group-title="' + info[3] + '",' + info[4]
        updated[extinf] = link
        print(f"  OK: {link[:60]}")

final_list = old_channels.copy()
final_list.update(updated)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for extinf, link in final_list.items():
        out.write(extinf + "\n")
        out.write(link + "\n\n")

print(f"\nBITTI! Toplam {len(final_list)} kanal yazildi.")
for k in updated:
    print(k)
