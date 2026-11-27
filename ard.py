import os
import re

TARGET_URL = "https://selcuksports180.top"
OUTPUT_FILE = "mirti68.m3u"

# Kanal adı, URL kodu/yolu, tip ve logosu
channels = [
    ("Bein Sports 1", "b1", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("Bein Sports 2", "b2", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("Bein Sports 3", "b3", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("Bein Sports 4", "b4", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("Bein Sports 5", "b5", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("Bein Sports Max 1", "bm1", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("Bein Sports Max 2", "bm2", "tracks", "https://resmim.net/cdn/2026/07/22/ETtrXH.png"),
    ("S Sport", "ss", "tracks", "https://yt3.googleusercontent.com/vJ6tfodHaOIAQbgPIN6Oa0cPUk5gdFAuXbLEPxMlnthgOQ2tBr8FU2UweMk-ksmyKiW3bIiFyRU=s900-c-k-c0x00ffffff-no-rj"),
    ("S Sport 2", "ss2", "tracks", "https://yt3.googleusercontent.com/vJ6tfodHaOIAQbgPIN6Oa0cPUk5gdFAuXbLEPxMlnthgOQ2tBr8FU2UweMk-ksmyKiW3bIiFyRU=s900-c-k-c0x00ffffff-no-rj"),
    ("TRT Spor", "trtspor", "tracks", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjuGO-ReknxTi5qGL5Y2gaAfXj3HfGoRcgBzcnGFLow29NQxwFk_gUGls&s=10"),
    ("TRT 1", "trt1", "tracks", "https://www.trt.net.tr/_nuxt/img/trt-1-televizyon-kanali.4c9c3dd.png"),
    ("A Spor", "aspor", "tracks", "https://cdn.aptoide.com/imgs/5/0/d/50d4bfd3c109b25b96c8e95c4d9d7df9_icon.png")
]

BASE_DOMAIN = "https://css.d6e3ess6e065r5.help/"

def build_new_entries():
    entries = []
    for idx, (name, code_or_path, path_type, logo) in enumerate(channels):
        if path_type == "hls":
            stream_url = f"{BASE_DOMAIN}/{code_or_path}"
        elif idx == 0:
            stream_url = f"{BASE_DOMAIN}//beyin1/tracks-v1a1/mono.m3u8"
        else:
            stream_url = f"{BASE_DOMAIN}//{code_or_path}/tracks-v1a1/mono.m3u8"

        # DUZELTILDI: Bein Sports iceriyorsa Bein Sports grubuna, digerleri SPORTS grubuna
        if "Bein Sports" in name.lower():
            group = "🟩◆ Bein Sports 🖥"
        else:
            group = "🟩◆ SPORTS ⭕"

        extinf = (
            f'#EXTINF:-1 tvg-name="{name}" '
            f'tvg-logo="{logo}" '
            f'group-title="{group}",{name}'
        )
        entries.append((extinf, stream_url))
        print(f"[+] Hazir: {name} | Grup: {group}")
    return entries

def generate_playlist():
    new_entries = build_new_entries()
    managed_names = {name.lower() for name, _, _, _ in channels}

    header_lines = []
    kept_lines = []

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("#EXTM3U") or line.startswith("#EXTVLCOPT") or line.startswith("#EXTGRP") or line.startswith("#PLAYLIST") or line.startswith("#EXT-X-"):
                header_lines.append(lines[i])
                i += 1
                continue

            if line.startswith("#EXTINF"):
                m = re.search(r'tvg-name="([^"]+)"', line)
                after_comma = line.split(",", 1)[-1].strip() if "," in line else ""
                tvg_name = (m.group(1) if m else after_comma).lower()

                url_line = lines[i + 1] if i + 1 < len(lines) else ""

                if tvg_name in managed_names:
                    print(f"[-] Eski kayit silindi, yenilenecek: {after_comma}")
                    i += 2
                    continue

                kept_lines.append(lines[i])
                if url_line and not url_line.startswith("#"):
                    kept_lines.append(url_line)
                    i += 2
                else:
                    i += 1
                continue

            if line == "":
                i += 1
                continue

            if not line.startswith("#"):
                kept_lines.append(lines[i])
            i += 1
    else:
        header_lines = [
            "#EXTM3U",
            "#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            f"#EXTVLCOPT:http-referrer={TARGET_URL}",
        ]

    if not any(l.startswith("#EXTM3U") for l in header_lines):
        header_lines.insert(0, "#EXTM3U")

    final_lines = header_lines + [""] + kept_lines + [""]

    for extinf, url in new_entries:
        final_lines.append(extinf)
        final_lines.append(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines) + "\n")

    print("--------------------------------")
    print(f"[✓] Korunan eski satir: {len(kept_lines)}")
    print(f"[✓] Eklenen / Guncellenen: {len(new_entries)}")
    print(f"[✓] Dosya: {OUTPUT_FILE}")
    print("[✓] Diger gruplar silinmedi.")
    print("--------------------------------")

if __name__ == "__main__":
    generate_playlist()
