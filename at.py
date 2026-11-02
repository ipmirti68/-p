
import os
import re
import requests

# =====================================
# MIRTI68 - ULUSAL KANAL GUNCELLEYICI
# =====================================

MASTER_FILE = "mirti68.m3u"

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

GROUP = "🇹🇷 ULUSAL  🔴"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) "
        "AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def extract_m3u8(page_url):
    try:
        response = session.get(page_url, timeout=25)
        response.raise_for_status()

        html = response.text

        html = html.replace("\\/", "/")
        html = html.replace("\\u0026", "&")
        html = html.replace("&amp;", "&")

        matches = re.findall(
            r'https?://[^\s\'"<>]+?\.m3u8(?:\?[^\s\'"<>]*)?',
            html,
            re.IGNORECASE
        )

        for link in matches:
            link = link.rstrip("\\),;")

            if ".m3u8" in link.lower():
                return link

        print("   M3U8 bulunamadi.")
        return None

    except requests.RequestException as e:
        print(f"   Baglanti hatasi: {e}")
        return None


def remove_old_ulusal(lines):
    """Yalnizca eski ULUSAL kanal kayitlarini kaldir."""

    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        clean = line.strip()

        if clean.startswith("#EXTINF:"):
            match = re.search(
                r'group-title="([^"]*)"',
                clean,
                re.IGNORECASE
            )

            if match and "ULUSAL" in match.group(1).upper():
                # Kanalin URL satirina kadar atla.
                i += 1

                while i < len(lines):
                    current = lines[i].strip()

                    if current.startswith("#EXTINF:"):
                        break

                    if current and not current.startswith("#"):
                        i += 1
                        break

                    i += 1

                continue

        result.append(line)
        i += 1

    return result


def main():

    print("====================================")
    print(" MIRTI68 - ULUSAL KANAL GUNCELLEME")
    print("====================================")

    if not os.path.exists(MASTER_FILE):
        print("[HATA] mirti68.m3u bulunamadi!")
        return

    # Ana listeyi oku
    with open(MASTER_FILE, "a", encoding="utf-8-sig") as f:
        old_lines = f.readlines()

    # Eski ULUSAL grubunu temizle
    output = remove_old_ulusal(old_lines)

    # M3U basligini koru
    if not any(x.strip() == "#EXTM3U" for x in output):
        output.insert(0, "#EXTM3U\n")

    # Yeni ULUSAL kanallar
    new_channels = []
    success = 0

    for name, page_url in source_urls.items():

        print(f"\n[+] {name} kontrol ediliyor...")

        stream_url = extract_m3u8(page_url)

        if not stream_url:
            print(f"[X] {name} eklenmedi.")
            continue

        new_channels.append(
            f'#EXTINF:-1 group-title="{GROUP}",{name}\n'
        )

        new_channels.append(stream_url + "\n")

        print(f"[OK] {name} bulundu.")
        success += 1

    # Yeni grubu listenin sonuna ekle
    if new_channels:
        if output and not output[-1].endswith("\n"):
            output[-1] += "\n"

        output.append("\n")
        output.extend(new_channels)

    # Ana dosyayi kaydet
    temp_file = MASTER_FILE + ".tmp"

    with open(temp_file, "a", encoding="utf-8") as f:
        f.writelines(output)

    os.replace(temp_file, MASTER_FILE)

    print("\n====================================")
    print(f" Bulunan kanal : {success}")
    print(f" Eklenmeyen    : {len(source_urls) - success}")
    print(f" Ana liste     : {MASTER_FILE}")
    print(f" Grup          : {GROUP}")
    print(" Diger gruplar : KORUNDU")
    print("====================================")


if __name__ == "__main__":
    main()
