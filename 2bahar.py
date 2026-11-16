
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from yt_dlp import YoutubeDL

VIDEO_URL = "https://www.youtube.com/watch?v=3o_K_m9IXCg"
OUTPUT_FILE = "ikinci_bahar_test.m3u"

print("=" * 45)
print("MIRTI68 - İKİNCİ BAHAR HLS TESTİ")
print("=" * 45)

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}

try:
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(VIDEO_URL, download=False)

    formats = info.get("formats", [])
    hls_urls = []

    for fmt in formats:
        url = fmt.get("url", "")
        protocol = fmt.get("protocol", "")

        if (
            url.startswith("http")
            and (
                "m3u8" in protocol.lower()
                or ".m3u8" in url.lower()
            )
        ):
            hls_urls.append(url)

    if not hls_urls:
        print("HLS / M3U8 adresi bulunamadı.")
        print("YouTube bu video için doğrudan HLS sunmuyor olabilir.")
    else:
        # En son bulunan HLS adresini test listesine yaz.
        stream_url = hls_urls[-1]

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(
                '#EXTINF:-1 group-title="🎬 İKİNCİ BAHAR",'
                'İkinci Bahar 36. Bölüm\n'
            )
            f.write(stream_url + "\n")

        print("M3U8 bulundu!")
        print("Bulunan HLS adresi:", len(hls_urls))
        print("Dosya oluşturuldu:", OUTPUT_FILE)
        print("Not: Bağlantı geçici olabilir.")

except Exception as e:
    print("TEST HATASI:", str(e))
    
