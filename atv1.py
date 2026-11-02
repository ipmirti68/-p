
import os
import re
import requests
import shutil
from urllib.parse import urljoin

# ==================================
# MIRTI68 ULUSAL KANALLAR
# ==================================

source_urls = {
    "TRT 1": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
    "TRT Spor": "https://www.tabii.com/watch/live/trtspor?trackId=150022",
    "TRT Haber": "https://www.tabii.com/watch/live/trthaber?trackId=150017",
    "TRT Spor Yildiz": "https://www.tabii.com/tr/watch/live/trtsporyildiz?trackId=150028",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "Show TV": "https://www.showtv.com.tr/canli-yayin",
    "Star TV": "https://www.startv.com.tr/canli-yayin",
    "TV8": "https://www.tv8.com.tr/canli-yayin",
    "TV8,5": "https://www.tv8bucuk.com/tv8-5-canli-yayin",
    "ATV": "https://www.atv.com.tr/canli-yayin",
    "Kanal D": "https://www.kanald.com.tr/canli-yayin",
    "teve2": "https://www.teve2.com.tr/canli-yayin",
    "DMAX": "https://www.dmax.com.tr/canli-izle",
    "a2": "https://www.atv.com.tr/a2tv/canli-yayin",
    "TV360": "https://www.tv360.com.tr/canli-yayin",
    "A Spor": "https://www.aspor.com.tr/webtv/canli-yayin",
    "Beyaz TV": "https://www.beyaztv.com.tr/canli-yayin",
    "CNN Türk": "https://www.cnnturk.com/canli-yayin",
    "SZC TV": "https://www.szctv.com.tr/canli-yayin-izle",
    "KRT TV": "https://www.krttv.com.tr/canli-yayin",
    "Halk TV": "https://halktv.com.tr/canli-yayin",
    "TV100": "https://www.tv100.com/canli-yayin"
}

STREAM_FOLDER = "stream"
MASTER_FILE = "mirti68.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"
}

session = requests.Session()
session.headers.update(HEADERS)


def extract_m3u8(url):
    try:
        response = session.get(url, timeout=25)
        response.raise_for_status()

        html = response.text

        patterns = [
            r'https?:\\?/\\?/[^\'"\s<>]+?\.m3u8[^\'"\s<>]*',
            r'https?://[^\'"\s<>]+?\.m3u8[^\'"\s<>]*'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)

            for link in matches:
                link = link.replace("\\/", "/")
                link = link.replace("\\u0026", "&")

                if link.startswith("http"):
                    return link

        print("   M3U8 bulunamadi.")
        return None

    except Exception as e:
        print(f"   HATA: {e}")
        return None


def save_stream(name, url):
    filename = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())
    path = os.path.join(STREAM_FOLDER, filename + ".m3u8")

    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(url + "\n")

    return path.replace("\\", "/")


def read_existing():
    if not os.path.exists(MASTER_FILE):
        return []

    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        return f.readlines()


def main():
    print("================================")
    print(" MIRTI68 - ULUSAL KANAL TARAMA")
    print("================================")

    os.makedirs(STREAM_FOLDER, exist_ok=True)

    # Mevcut listeyi koru
    old_lines = read_existing()

    # Eski ulusal grubu yenile, diğer gruplara dokunma
    output = []
    skip = False

    for line in old_lines:
        if line.startswith("#EXTINF:") and 'group-title="🇹🇷 ULUSAL"' in line:
            skip = True
            continue

        if skip:
            if not line.startswith("#"):
                skip = False
            continue

        output.append(line)

    # Yeni kanalları ekle
    output.append("\n")

    added = 0

    for name, page_url in source_urls.items():
        print(f"\n[+] {name} taraniyor...")

        stream_url = extract_m3u8(page_url)

        if not stream_url:
            print("[X] Atlandi.")
            continue

        path = save_stream(name, stream_url)

        output.append(
            f'#EXTINF:-1 group-title="🇹🇷 ULUSAL",{name}\n'
        )
        output.append(path + "\n")

        print(f"[OK] {name} eklendi.")
        added += 1

    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        f.writelines(output)

    print("\n================================")
    print(f" Eklenen kanal: {added}")
    print(f" Ana liste: {MASTER_FILE}")
    print(" Grup: 🇹🇷 ULUSAL")
    print("================================")


if __name__ == "__main__":
    main()
