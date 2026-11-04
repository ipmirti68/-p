
import os
import re
import html
import requests
from urllib.parse import urljoin
from m3u_manager import update_group
# ==================================================
# MIRTI68 - ULUSAL KANALLAR
# ==================================================

OUTPUT_FILE = "mirti68.m3u"
GROUP = "📺 ULUSAL 🔗"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )
}

CHANNELS = {
    "TRT 1": {
        "page": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
        "backup": "https://trt.daioncdn.net/trt-1/master.m3u8?app=web",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png"
    },
    "ATV": {
        "page": "https://www.atv.com.tr/canli-yayin",
        "backup": "https://trkvz.daioncdn.net/atv/atv_1080p.m3u8?",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"
    },
    "KANAL D": {
        "page": "https://www.kanald.com.tr/canli-yayin",
        "backup": "https://demiroren.daioncdn.net/kanald/kanald_1080p.m3u8?",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png"
    },
    "SHOW TV": {
        "page": "https://www.showtv.com.tr/canli-yayin",
        "backup": "https://ciner.daioncdn.net/showtv/showtv.m3u8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png"
    },
    "STAR TV": {
        "page": "https://www.startv.com.tr/canli-yayin",
        "backup": "https://dogus.daioncdn.net/startv/startv_720p.m3u8?",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png"
    },
    "NOW TV": {
        "page": "https://www.nowtv.com.tr/canli-yayin",
        "backup": "https://nowtv-live-ad.ercdn.net/nowtv/nowtv_720p.m3u8?",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png"
    },
    "KANAL 7": {
        "page": "https://www.kanal7.com/canli-izle",
        "backup": "https://kanal7.daioncdn.net/kanal7/kanal7.m3u8?",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png"
    },
    "TV8": {
        "page": "https://www.tv8.com.tr/canli-yayin",
        "backup": "https://tv8.daioncdn.net/tv8/tv8_1080p.m3u8?",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png"
    }
}

# Yalnızca bu kanallarda yt-dlp denenir.
YTDLP_CHANNELS = {
    "ATV",
    "KANAL D",
    "SHOW TV",
    "STAR TV"
}


# ==================================================
# HTTP OTURUMU
# ==================================================

session = requests.Session()
session.headers.update(HEADERS)


# ==================================================
# M3U8 ADRES KONTROLÜ
# ==================================================

def valid_m3u8(url):
    if not url or not isinstance(url, str):
        return False

    url = html.unescape(url.strip())

    if not url.startswith(("http://", "https://")):
        return False

    if ".m3u8" not in url.lower():
        return False

    if "[STRIPPED" in url or " " in url:
        return False

    return True


# ==================================================
# YT-DLP İLE YAYIN BUL
# ==================================================

def extract_with_ytdlp(page_url):
    try:
        import yt_dlp

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "format": "best"
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                page_url,
                download=False
            )

        direct_url = info.get("url", "")

        if valid_m3u8(direct_url):
            return direct_url

        formats = info.get("formats", [])

        for item in reversed(formats):
            direct_url = item.get("url", "")

            if valid_m3u8(direct_url):
                return direct_url

    except Exception as error:
        print("YT-DLP HATASI:", error)

    return None


# ==================================================
# SAYFADAN M3U8 BUL
# ==================================================

def extract_m3u8(page_url):
    try:
        response = session.get(
            page_url,
            headers={"Referer": page_url},
            timeout=25
        )

        response.raise_for_status()

        source = html.unescape(response.text)
        source = source.replace("\\/", "/")

        patterns = [
            r'https?://[^\s\'"<>\\]+?\.m3u8(?:\?[^\s\'"<>\\]*)?',
            r'//[^\s\'"<>\\]+?\.m3u8(?:\?[^\s\'"<>\\]*)?'
        ]

        for pattern in patterns:
            matches = re.findall(
                pattern,
                source,
                re.IGNORECASE
            )

            for url in matches:
                url = url.rstrip("\\),;")

                if url.startswith("//"):
                    url = "https:" + url

                if valid_m3u8(url):
                    return url

    except Exception as error:
        print("SAYFA TARAMA HATASI:", error)

    return None


# ==================================================
# ESKİ M3U DOSYASINI OKU
# ==================================================

def read_old_playlist():
    header = "#EXTM3U"
    old_blocks = []
    old_channels = {}

    if not os.path.exists(OUTPUT_FILE):
        return header, old_blocks, old_channels

    try:
        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8-sig",
            errors="ignore"
        ) as file:
            lines = file.read().splitlines()

        if lines and lines[0].startswith("#EXTM3U"):
            header = lines[0]

        current = []

        for line in lines:
            if line.startswith("#EXTM3U"):
                continue

            if line.startswith("#EXTINF:"):
                if current:
                    old_blocks.append(current)

                current = [line]

            elif current:
                current.append(line)

        if current:
            old_blocks.append(current)

        for block in old_blocks:
            first = block[0]

            if GROUP not in first:
                continue

            if "," not in first:
                continue

            name = first.split(",", 1)[1].strip()

            for line in block[1:]:
                if line.startswith("http"):
                    if valid_m3u8(line):
                        old_channels[name] = line.strip()
                        break

    except Exception as error:
        print("ESKİ LİSTE OKUMA HATASI:", error)

    return header, old_blocks, old_channels


# ==================================================
# KANALLARI TARA
# ==================================================

def scan_channel(name, info, old_channels):
    page_url = info.get("page")
    backup_url = info.get("backup")

    print("\n" + "=" * 45)
    print("KANAL:", name)
    print("=" * 45)

    fresh = None

    # 1. Önce yt-dlp
    if page_url and name in YTDLP_CHANNELS:
        print("YT-DLP deneniyor...")

        fresh = extract_with_ytdlp(page_url)

        if valid_m3u8(fresh):
            print("YT-DLP YAYINI BULUNDU!")

    # 2. Normal sayfa taraması
    if not valid_m3u8(fresh) and page_url:
        print("Sayfa taraması deneniyor...")

        fresh = extract_m3u8(page_url)

        if valid_m3u8(fresh):
            print("YENİ YAYIN BULUNDU!")

    # 3. Yedek adres
    if not valid_m3u8(fresh):
        if valid_m3u8(backup_url):
            fresh = backup_url
            print("YEDEK YAYIN KULLANILIYOR!")

    # 4. Önceki çalışan adresi koru
    if not valid_m3u8(fresh):
        previous = old_channels.get(name)

        if valid_m3u8(previous):
            fresh = previous
            print("ÖNCEKİ LİSTEDEKİ ADRES KORUNUYOR!")

    if valid_m3u8(fresh):
        return fresh

    print("YAYIN BULUNAMADI:", name)
    return None


# ==================================================
# MIRTI68 M3U GÜNCELLE
# ==================================================

def main():
    print("\nMIRTI68 ULUSAL KANAL TARAMASI BAŞLADI")

    header, old_blocks, old_channels = read_old_playlist()

    print("Eski korunan kanal:", len(old_channels))

    new_channels = {}

    for name, info in CHANNELS.items():
        stream = scan_channel(
            name,
            info,
            old_channels
        )

        if stream:
            new_channels[name] = stream

    # Diğer kategorileri koru.
    preserved = []

    for block in old_blocks:
        first = block[0]

        if GROUP in first:
            continue

        preserved.append("\n".join(block).strip())

    # Dosyayı yeniden oluştur.
    try:
        with open(
            OUTPUT_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(header + "\n")

            # Yeni ulusal kanallar
            for name, stream in new_channels.items():
                logo = CHANNELS[name].get("logo", "")
                page = CHANNELS[name].get("page")

                referrer = page or "https://www.trt1.com.tr/"

                file.write(
                    f'#EXTINF:-1 tvg-name="{name}" '
                    f'tvg-logo="{logo}" '
                    f'group-title="{GROUP}",{name}\n'
                )

                file.write(
                    f'#EXTVLCOPT:http-referrer={referrer}\n'
                )

                file.write(
                    '#EXTVLCOPT:http-user-agent='
                    'Mozilla/5.0\n'
                )

                file.write(stream + "\n\n")

            # Diğer gruplar
            for block in preserved:
                file.write(block + "\n\n")

        print("\n" + "=" * 45)
        print("ULUSAL TARAMA TAMAMLANDI")
        print("Bulunan ulusal kanal:", len(new_channels))
        print("Korunan eski kayıt:", len(preserved))
        print("Dosya:", OUTPUT_FILE)
        print("=" * 45)

    except Exception as error:
        print("M3U YAZMA HATASI:", error)


# ==================================================
# BASLAT
# ==================================================

if __name__ == "__main__":
    main()
