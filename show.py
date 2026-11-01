import os
import time

m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"
GROUP_NAME = "SHOW Dizileri"
BASE = "https://www.showtv.com.tr"

def get_m3u8(full_url):
    # SADECE tam http link kabul et, yarım olan 145-bolum gibi olanı direkt reddet
    if not full_url.startswith("http"):
        print(f"  SKIP yarim url: {full_url}")
        return None
    if any(x in full_url.lower() for x in ["fragman", "galeri", "fotograf"]):
        return None
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(full_url, download=False)
            for f in info.get("formats", [])[::-1]:
                u = f.get("url", "")
                if ".m3u8" in u and "vmcdn" in u:
                    return u
    except Exception as e:
        print(f"  yt-dlp hata {full_url[-40:]}: {e}")
    return None

# TAZE MANUEL - senin verdiğin hep duracak, 404 olmaz
MANUEL_URL = "https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392"

LAST = {
    "kizilcik-serbeti": 145,
    "sevdan-bir-ates": 8,
    "muhtemel-ask": 10,
    "menekse": 5
}

entries = []
entries.append({"dizi": "Sevdan Bir Ates", "bolum": "8. Bolum", "url": MANUEL_URL, "num": 8})
print(f"MANUEL 8 eklendi")

for slug, last in LAST.items():
    # sevdan-bir-ates 8 manuel var, 7,6 dene
    start = last if slug != "sevdan-bir-ates" else 7
    print(f"\n=== {slug.upper()} ===")
    for num in range(start, start - 2, -1):
        if num <= 0:
            continue
        # TAM URL'ler - kesinlikle tam
        url1 = f"{BASE}/dizi/{slug}/bolum/{num}-bolum"
        url2 = f"{BASE}/dizi/{slug}/bolum/{num}-bolum-izle"
        
        found = False
        for full_url in [url1, url2]:
            print(f"  -> {full_url}")
            m3u8 = get_m3u8(full_url)
            if m3u8 and len(m3u8) > 60:
                dizi_adi = slug.replace("-", " ").title()
                if slug == "kizilcik-serbeti": dizi_adi = "Kizilcik Serbeti"
                if slug == "sevdan-bir-ates": dizi_adi = "Sevdan Bir Ates"
                entries.append({"dizi": dizi_adi, "bolum": f"{num}. Bolum", "url": m3u8, "num": num})
                print(f"  OK {num}")
                found = True
                break
            else:
                print(f"  yok")
        if not found:
            print(f"  BULAMADI {num}")
        time.sleep(0.5)

# tekilleştir ve son 3
final_dict = {}
for e in entries:
    key = f"{e['dizi'].lower()}_{e['num']}"
    if key not in final_dict:
        final_dict[key] = e

all_final = list(final_dict.values())

with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x: (x["dizi"], -x["num"])):
        f.write(f'#EXTINF:-1 group-title="{GROUP_NAME}",TR: SHOW - {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

print(f"\n{m3u_file} -> {len(all_final)} bolum")

if not os.path.exists(mirti_file):
    with open(mirti_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

with open(mirti_file, "r", encoding="utf-8", errors="ignore") as ff:
    cont = ff.read()

first = cont.splitlines()[0] if cont else "#EXTM3U"
old = ["#EXTINF" + p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP_NAME not in p]

with open(m3u_file, "r", encoding="utf-8", errors="ignore") as ff:
    new = ["#EXTINF" + p for p in ff.read().split("#EXTINF")[1:] if "http" in p]

with open(mirti_file, "w", encoding="utf-8") as out:
    out.write(first + "\n")
    for b in old:
        out.write(b.strip() + "\n\n")
    for b in new:
        out.write(b.strip() + "\n\n")

print(f"mirti68.m3u guncellendi - {len(new)} kayit")
print("Bitti")
