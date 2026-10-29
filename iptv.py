import os
import requests
import re

# Senin istediğin formatın bilgileri - YENİLERİ BURAYA EKLİYOR
channel_info = {
    "trt1": {"tvg_id": "TRT.1.hd", "tvg_name": "TRT 1.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "group": "📺 ULUSAL.", "name": "TRT 1"},
    "trtspor": {"tvg_id": "TRT.Spor.hd", "tvg_name": "TRT Spor.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trtspor.png", "group": "📺 SPOR.", "name": "TRT Spor"},
    "trthaber": {"tvg_id": "TRT.Haber.hd", "tvg_name": "TRT Haber.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trthaber.png", "group": "📺 HABER.", "name": "TRT Haber"},
    "atv": {"tvg_id": "ATV.hd", "tvg_name": "ATV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "group": "📺 ULUSAL.", "name": "ATV"},
    "showtv": {"tvg_id": "Show.TV.hd", "tvg_name": "Show TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "group": "📺 ULUSAL.", "name": "Show TV"},
    "kanald": {"tvg_id": "Kanal.D.hd", "tvg_name": "Kanal D.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "group": "📺 ULUSAL.", "name": "Kanal D"},
}

source_urls = {
    "trt1": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
    "trtspor": "https://www.tabii.com/watch/live/trtspor?trackId=150022",
    "trthaber": "https://www.tabii.com/watch/live/trthaber?trackId=150017",
    "atv": "https://www.atv.com.tr/canli-yayin",
    "showtv": "https://www.showtv.com.tr/canli-yayin",
    "kanald": "https://www.kanald.com.tr/canli-yayin",
}

def extract_m3u8(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=10, headers=headers)
        m = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', r.text)
        if m:
            return m[0]
    except:
        pass
    return None

output_file = "mirti68.m3u"

# 1. MEVCUT LİSTEYİ OKU VE KORU
old_channels = {}
if os.path.exists(output_file):
    print(f"[>] Mevcut {output_file} okunuyor, korunacak...")
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                # Bir sonraki satır link
                if i+1 < len(lines):
                    link = lines[i+1].strip()
                    if link and not link.startswith("#"):
                        old_channels[lines[i].strip()] = link
    print(f"[>] {len(old_channels)} eski kanal korundu")

# 2. YENİ LİNKLERİ ÇEK VE GÜNCELLE
updated = {}
for name, page_url in source_urls.items():
    print(f"[+] {name} kontrol...")
    m3u8_link = extract_m3u8(page_url)
    if name == "trt1" and not m3u8_link:
        m3u8_link = "https://tv-trt1.medya.trt.com.tr/master.m3u8"
    
    if m3u8_link:
        info = channel_info.get(name)
        if info:
            extinf = f'#EXTINF:-1 tvg-id="{info["tvg_id"]}" tvg-name="{info["tvg_name"]}" tvg-logo="{info["logo"]}" group-title="{info["group"]}",{info["name"]}'
            updated[extinf] = m3u8_link
            print(f"[✓] {info['name']} guncellendi")

# 3. ESKİ + YENİYİ BİRLEŞTİR - ESKİLERİ SİLME
# Yeniler eskilerin üzerine yazsın, geri kalan eskiler kalsın
final_list = {**old_channels, **updated}

# 4. DOSYAYI YAZ
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for extinf, link in final_list.items():
        out.write(extinf + "\n")
        out.write(link + "\n\n")

print(f"\nHAZIR! {len(final_list)} kanal ile {output_file} korundu ve guncellendi.")
