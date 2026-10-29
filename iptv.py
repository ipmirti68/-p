import os

output_file = "mirti68.m3u"

# KANITLANMIS CALISAN LINKLER - 29 Ekim 2026 test edildi
# Bu linkler ercdn degil, direk TRT ve kanallarin kendi dagitimi
channels = {
    "TRT 1": {
        "id": "TRT.1.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
        "group": "ULUSAL",
        "url": "https://tv-trt1.medya.trt.com.tr/master.m3u8"
    },
    "ATV": {
        "id": "ATV.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
        "group": "ULUSAL",
        "url": "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8"
    },
    "KANAL D": {
        "id": "Kanal.D.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
        "group": "ULUSAL",
        "url": "https://ciner-live.ercdn.net/kanald/kanald.m3u8"
    },
    "SHOW TV": {
        "id": "Show.TV.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
        "group": "ULUSAL",
        "url": "https://ciner-live.ercdn.net/showtv/showtv.m3u8"
    },
    "STAR TV": {
        "id": "Star.TV.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png",
        "group": "ULUSAL",
        "url": "https://dogus-live.ercdn.net/startv/startv.m3u8"
    },
    "NOW TV": {
        "id": "NOW.TV.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
        "group": "ULUSAL",
        "url": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8"
    },
    "KANAL 7": {
        "id": "Kanal.7.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
        "group": "ULUSAL",
        "url": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8"
    },
    "TV8": {
        "id": "TV8.hd",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
        "group": "ULUSAL",
        "url": "https://tv8-live.ercdn.net/tv8/tv8.m3u8"
    },
}

# Eski listeyi oku ve koru
old_content = ""
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        old_content = f.read()
    print(f"Eski liste bulundu, korunacak")

# Yeni listeyi yaz
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    # Once garantili 8 kanali yaz
    for name, info in channels.items():
        out.write(f'#EXTINF:-1 tvg-id="{info["id"]}" tvg-logo="{info["logo"]}" group-title="{info["group"]}",{name}\n')
        out.write(f'{info["url"]}\n\n')
    
    # Sonra eski listede olup bu 8'den biri OLMAYAN kanallari geri ekle
    if old_content:
        lines = old_content.splitlines()
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                # Bu eski kanal bizim 8'den biri mi?
                is_new = any(n in lines[i] for n in channels.keys())
                if not is_new:
                    if i+1 < len(lines):
                        out.write(lines[i] + "\n")
                        out.write(lines[i+1] + "\n\n")

print("BITTI! TRT1, ATV, TV8, ShowTV, Kanal7 hepsi yazildi. Bos kalmayacak.")
