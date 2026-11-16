
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from yt_dlp import YoutubeDL

VIDEO_URL = "https://www.youtube.com/watch?v=u5hnBZoO0Fk"

print("=" * 45)
print("MIRTI68 - İKİNCİ BAHAR RESMİ HLS TESTİ")
print("=" * 45)

opts = {
    "quiet": True,
    "no_warnings": False,
    "skip_download": True,
}

try:
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(VIDEO_URL, download=False)

    formats = info.get("formats", [])
    found = []

    for fmt in formats:
        protocol = fmt.get("protocol", "")
        url = fmt.get("url", "")

        if "m3u8" in protocol.lower():
            found.append((fmt.get("format_id"), protocol, url))

    if found:
        print("M3U8 ADRESLERİ BULUNDU:", len(found))

        for number, (fmt_id, protocol, url) in enumerate(found, 1):
            print(f"\nADRES {number}")
            print("Format:", fmt_id)
            print("Protokol:", protocol)
            print("URL:", url)

    else:
        print("M3U8 formatı bulunamadı.")
        print("Video formatları:")
        for fmt in formats:
            print(
                fmt.get("format_id"),
                fmt.get("protocol"),
                fmt.get("ext")
            )

except Exception as e:
    print("HATA:", str(e))
    
