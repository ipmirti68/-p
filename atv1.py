
import os
import re
import requests

# =====================================
# MIRTI68 - ULUSAL KANAL GUNCELLEYICI
# SADECE KENDI KAYITLARINI GUNCELLER
# =====================================

MASTER_FILE = "mirti68.m3u"

GROUP = "🇹🇷 ULUSAL 🔴"
MARKER = "# MIRTI68_ULUSAL_AUTO"

source_urls = {
    "TRT 1": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "Show TV": "https://www.showtv.com.tr/canli-yayin",
    "Star TV": "https://www.startv.com.tr/canli-yayin",
    "TV8": "https://www.tv8.com.tr/canli-yayin",
    "ATV": "https://www.atv.com.tr/canli-yayin",
    "Kanal D": "https://www.kanald.com.tr/canli-yayin",
    "teve2": "https://www.teve2.com.tr/canli-yayin",
    "DMAX": "https://www.dmax.com.tr/canli-izle",
    "a2": "https://www.atv.com.tr/a2tv/canli-yayin",
    "TV360": "https://www.tv360.com.tr/canli-yayin",
    
}

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


def remove_own_records(lines):
    """Yalnizca bu kodun isaretledigi kayitlari sil."""

    result = []
    i = 0

    while i < len(lines):

        if lines[i].strip() == MARKER:

            i += 1

            # Isaretli kanal kaydini ve URL satirini atla
            while i < len(lines):
                line = lines[i].strip()

                if line.startswith("#EXTINF:"):
                    i += 1

                    while i < len(lines):
                        current = lines[i].strip()

                        if current and not current.startswith("#"):
                            i += 1
                            break

                        if current.startswith("#EXTINF:"):
                            break

                        i += 1

                    break

                if line == MARKER:
                    break

                i += 1

            continue

        result.append(lines[i])
        i += 1

    return result


def main():

    print("====================================")
    print(" MIRTI68 ULUSAL GUNCELLEYICI")
    print("====================================")

    if not os.path.exists(MASTER_FILE):
        print("[HATA] mirti68.m3u bulunamadi!")
        return

    # Dosyayi oku: eski icerik korunur
    with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
        old_lines = f.readlines()

    # Sadece kendi onceki kayitlarini kaldir
    output = remove_own_records(old_lines)

    if not any(x.strip() == "#EXTM3U" for x in output):
        output.insert(0, "#EXTM3U\n")

    new_channels = []
    success = 0

    for name, page_url in source_urls.items():

        print(f"\n[+] {name} kontrol ediliyor...")

        stream_url = extract_m3u8(page_url)

        if not stream_url:
            print(f"[X] {name} eklenmedi.")
            continue

        new_channels.extend([
            MARKER + "\n",
            f'#EXTINF:-1 group-title="{GROUP}",{name}\n',
            stream_url + "\n"
        ])

        print(f"[OK] {name} bulundu.")
        success += 1

    # Yeni kanallari sona ekle
    if new_channels:

        if output and not output[-1].endswith("\n"):
            output[-1] += "\n"

        output.append("\n")
        output.extend(new_channels)

    # Guvenli kaydetme
    temp_file = MASTER_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        f.writelines(output)

    os.replace(temp_file, MASTER_FILE)

    print("\n====================================")
    print(f" Bulunan kanal : {success}")
    print(f" Eklenmeyen    : {len(source_urls) - success}")
    print(f" Ana liste     : {MASTER_FILE}")
    print(" Diger gruplar : KORUNDU")
    print(" Elle eklenenler: KORUNDU")
    print("====================================")


if __name__ == "__main__":
    main()
