import json, urllib.request

URL = "https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/kanald_state.json"
OUT = "kanald.m3u"

print("JSON indiriliyor...")
with urllib.request.urlopen(URL) as r:
    data = json.loads(r.read().decode("utf-8"))

print(f"{len(data)} dizi bulundu")

lines = ["#EXTM3U x-tvg-url=\"\""]

for slug, dizi in data.items():
    name = dizi.get("name", slug)
    group = dizi.get("group", "DIZI")
    logo = dizi.get("logo", "")
    episodes = dizi.get("episodes", [])

    # order'a göre sırala
    episodes = sorted(episodes, key=lambda e: e.get("order", 0))

    for ep in episodes:
        ep_name = ep.get("name", "").replace("Izle.", "").strip()
        # 1/Izle. Bölüm -> 1. Bölüm
        ep_name = ep_name.replace("/", ". ")
        url = ep.get("url", "")
        if not url:
            continue
        title = f"{name} - {ep_name}"
        lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{title}')
        lines.append(url)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Yazildi: {OUT} - {len(lines)//2} bolum")
