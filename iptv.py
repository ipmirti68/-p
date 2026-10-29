import os

output_file = "mirti68.m3u"

# Sadece bu 8 kanalin linki guncellenecek, digerlerine dokunulmayacak
guncellenecek = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "ATV": "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "STAR TV": "https://dogus-live.ercdn.net/startv/startv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "TV8": "https://tv8-live.ercdn.net/tv8/tv8.m3u8",
}

# Eski listeyi oku
lines = []
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    print(f"Eski liste okundu: {len(lines)} satir")

# Eski listeyi dict yap: isim -> [extinf, url]
old_dict = {}
i = 0
while i < len(lines):
    if lines[i].startswith("#EXTINF"):
        extinf = lines[i].strip()
        url = lines[i+1].strip() if i+1 < len(lines) else ""
        # Kanal ismini al (virgulden sonra)
        name = extinf.split(",")[-1].strip().upper()
        old_dict[name] = [extinf, url]
        i += 2
    else:
        i += 1

print(f"Eski kanallar: {len(old_dict)} adet")

# Guncelle veya ekle
for name, new_url in guncellenecek.items():
    key = name.upper()
    if key in old_dict:
        # Varsa sadece linkini guncelle, logosuna dokunma
        old_dict[key][1] = new_url
        print(f"Guncellendi: {name}")
    else:
        # Yoksa yeni ekle
        extinf = f'#EXTINF:-1 tvg-id="{name}.hd" group-title="ULUSAL",{name}'
        old_dict[key] = [extinf, new_url]
        print(f"Eklendi: {name}")

# Dosyayi yaz - HICBIR SEY SILINMEDI
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for extinf, url in old_dict.values():
        out.write(extinf + "\n")
        out.write(url + "\n\n")

print(f"BITTI! Toplam {len(old_dict)} kanal. Eski listen duruyor + 8 ulusal guncellendi.")
