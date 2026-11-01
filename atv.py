import os
import re
import time

m3u_file = "atv_playlist.m3u"
mirti_file = "mirti68.m3u"
BASE_URL = "https://www.atv.com.tr"
GROUP_NAME = "ATV Dizileri"

def get_m3u8(full_url):
    if "bolumler" in full_url.lower():
        return None
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(full_url, download=False)
            formats = info.get("formats", [])
            for f in reversed(formats):
                u = f.get("url", "")
                if ".m3u8" in u and "erbvr" in u:
                    return u
    except Exception as e:
        print(f"  yt-dlp hata: {e}")
    return None

LAST_NUMBERS = {
    "gunesin-dogdugu-yer": 7,
    "alti-ustu-istanbul": 5,
    "abi": 10,
    "ask-ve-taht": 8,
    "mercan-kosk": 6,
    "kurulus-osman": 180,
    "bir-gece-masali": 30,
    "sevdam-bir-ates": 5
}

all_entries = []

for slug, last_num in LAST_NUMBERS.items():
    print(f"\n=== {slug.upper()} SON {last_num} ===")
    for num in range(last_num, last_num - 3, -1):
        if num <= 0:
            continue
        candidates = [
            f"{BASE_URL}/diziler/{slug}/bolum/{num}-bolum",
            f"{BASE_URL}/diziler/{slug}/bolum/{num}-bolum-izle"
        ]
        found = False
        for url in candidates:
            print(f"  -> {url}")
            m3u8_url = get_m3u8(url)
            if m3u8_url and len(m3u8_url) > 50:
                dizi_adi = slug.replace("-", " ").title()
                all_entries.append({
                    "dizi": dizi_adi,
                    "bolum": f"{num}. Bolum",
                    "url": m3u8_url,
                    "num": num
                })
                print(f"  OK {num}")
                found = True
                break
            else:
                print(f"  yok")
        if not found:
            print(f"  BULAMADI {num}")
        time.sleep(0.5)

print(f"\nToplam {len(all_entries)} bolum bulundu")

with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_entries, key=lambda x: (x["dizi"], -x["num"])):
        f.write(f'#EXTINF:-1 group-title="{GROUP_NAME}",{e["dizi"]} - {e["bolum"]}\n')
        f.write(f'#EXTVLCOPT:http-referrer={BASE_URL}/\n')
        f.write(f'{e["url"]}\n\n')

print(f"{m3u_file} yazildi")

if not os.path.exists(mirti_file):
    with open(mirti_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

with open(mirti_file, "r", encoding="utf-8", errors="ignore") as ff:
    content = ff.read()

first_line = content.splitlines()[0] if content else "#EXTM3U"
old_blocks = ["#EXTINF" + p for p in content.split("#EXTINF")[1:] if "http" in p and GROUP_NAME not in p]

with open(m3u_file, "r", encoding="utf-8", errors="ignore") as ff:
    new_content = ff.read()

new_blocks = ["#EXTINF" + p for p in new_content.split("#EXTINF")[1:] if "http" in p]

with open(mirti_file, "w", encoding="utf-8") as out:
    out.write(first_line + "\n")
    for b in old_blocks:
        out.write(b.strip() + "\n\n")
    for b in new_blocks:
        out.write(b.strip() + "\n\n")

print(f"mirti68.m3u guncellendi - {GROUP_NAME} {len(new_blocks)} eklendi, diger gruplar korundu")
print("Bitti")
