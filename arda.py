TARGET_URL = "https://selcuksports180.top"
OUTPUT_FILE = "kanallar_arda.m3u8"

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

def generate_playlist():
    m3u_lines = [
        "#EXTM3U",
        "#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        f"#EXTVLCOPT:http-referrer={TARGET_URL}",
        ""
    ]
    
    valid_count = 0
    
    for idx, (name, code_or_path, path_type, logo) in enumerate(channels):
        if path_type == "hls":
            stream_url = f"{BASE_DOMAIN}/{code_or_path}"
        elif idx == 0:
            stream_url = f"{BASE_DOMAIN}//beyin1/tracks-v1a1/mono.m3u8"
        else:
            stream_url = f"{BASE_DOMAIN}//{code_or_path}/tracks-v1a1/mono.m3u8"
            
        extinf = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="BeinSports",{name}'
        
        m3u_lines.append(extinf)
        m3u_lines.append(stream_url)
        valid_count += 1
        print(f"[+] Eklendi: {name} -> {stream_url}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines) + "\n")
    
    print(f"[✓] Toplam {valid_count} kanal kusursuz şablonla '{OUTPUT_FILE}' dosyasına yazıldı.")

if __name__ == "__main__":
    generate_playlist()
