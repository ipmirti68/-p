import requests
import re
import urllib3
import warnings
import concurrent.futures
import os
import shutil
# ============================================================
# UYARILARI KAPAT
# ============================================================

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

warnings.filterwarnings("ignore")


# ============================================================
# AYARLAR
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

OUTPUT_FILENAME = "mirti68.m3u"
BEIN_GROUP = "🟩◆  beIN SPORTS 🖥"
SPORTS_GROUP = "🟩◆ SPORTS 🔴"
LOGO = "https://i.imgur.com/OqdfQmw.png"


BASE_PATTERN = "https://mahsunsports{}.xyz"


# ============================================================
# KANALLAR
# ============================================================

channels = [
    ("androstreamlivebiraz1", "beIN SPORTS 1 Mahsun 🔴"),
    ("androstreamlivebs1", "beIN SPORTS 1 Mahsun 🔴"),
    ("androstreamlivebs2", "beIN SPORTS 2 Mahsun 🔴"),
    ("androstreamlivebs3", "beIN SPORTS 3 Mahsun 🔴"),
    ("androstreamlivebs4", "beIN SPORTS 4 Mahsun 🔴"),
    ("androstreamlivebs5", "beIN SPORTS 5 Mahsun 🔴"),

    ("androstreamlivebsm1", "beIN SPORTS Max 1 Mahsun 🔴"),
    ("androstreamlivebsm2", "beIN SPORTS Max 2 Mahsun 🔴"),

    ("androstreamlivess1", "S SPORTS 1 Mahsun 🔴"),
    ("androstreamlivess2", "S SPORTS 2 Mahsun 🔴"),

    ("androstreamlivets", "Tivibu SPOR Mahsun 🔴"),
    ("androstreamlivets1", "Tivibu SPOR 1 Mahsun 🔴"),
    ("androstreamlivets2", "Tivibu Sport 2 Mahsun 🔴"),
    ("androstreamlivets3", "Tivibu Sport 3 Mahsun 🔴"),
    ("androstreamlivets4", "Tivibu Sport 4 Mahsun 🔴"),

    ("androstreamlivesm1", "Smart Sport 1 Mahsun 🔴"),
    ("androstreamlivesm2", "Smart Sport 2 Mahsun 🔴"),

    ("androstreamlivees1", "Euro Sport 1 Mahsun 🔴"),
    ("androstreamlivees2", "Euro Sport 2 Mahsun 🔴"),

    ("androstreamlivetb", "Tabii Mahsun 🔴"),
    ("androstreamlivetb1", "Tabii 1 Mahsun 🔴"),
    ("androstreamlivetb2", "Tabii 2 Mahsun 🔴"),
    ("androstreamlivetb3", "Tabii 3 Mahsun 🔴"),
    ("androstreamlivetb4", "Tabii 4 Mahsun 🔴"),
    ("androstreamlivetb5", "Tabii 5 Mahsun 🔴"),
    ("androstreamlivetb6", "Tabii 6 Mahsun 🔴"),
    ("androstreamlivetb7", "Tabii 7 Mahsun 🔴"),
    ("androstreamlivetb8", "Tabii 8 Mahsun 🔴"),

    ("androstreamliveexn", "beIN SPORTS * Mahsun 🔴"),
    ("androstreamliveexn1", "beIN SPORTS # Mahsun 🔴"),
    ("androstreamliveexn2", "DAZN 1-Mahsun 🔴"),
    ("androstreamliveexn3", "S SPORT+ -Mahsun 🔴"),
    ("androstreamliveexn4", "S SPORT + -Mahsun 🔴"),
    ("androstreamliveexn5", "S SPORT + -Mahsun 🔴"),
    ("androstreamliveexn6", "S SPORT 2 -Mahsun 🔴"),
    ("androstreamliveexn7", "AZ TV-Mahsun 🔴"),
    ("androstreamliveexn8", "TRT TÜRK HMahsun 🔴"),
]


# ============================================================
# KANAL LİSTESİNDEKİ AYNI İSİMLERİ TEMİZLE
# ============================================================

def remove_duplicate_channels(channel_list):

    unique = []
    seen_names = set()

    for cid, cname in channel_list:

        name_key = cname.strip().lower()

        if name_key in seen_names:
            print(
                f"[DUPLICATE KANAL ATLANDI] {cname}"
            )
            continue

        seen_names.add(name_key)

        unique.append(
            (cid, cname)
        )

    return unique


# ============================================================
# AKTİF DOMAIN BUL
# ============================================================

def find_active_domain():

    print("Aktif domain aranıyor (10-99)...")

    def check_domain(index):

        url = BASE_PATTERN.format(index)

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=5,
                verify=False,
                allow_redirects=True
            )

            if response.status_code == 200:

                return url

        except Exception:

            pass

        return None

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=20
    ) as executor:

        futures = [
            executor.submit(
                check_domain,
                i
            )
            for i in range(10, 100)
        ]

        for future in concurrent.futures.as_completed(
            futures
        ):

            result = future.result()

            if result:

                return result

    return None


# ============================================================
# EVENT SAYFASINDAN SERVERLARI AL
# ============================================================

def get_servers(active_site):

    event_url = (
        f"{active_site}"
        f"/event.html?id=androstreamlivebs1"
    )

    print(
        f"Event sayfası alınıyor: "
        f"{event_url}"
    )

    try:

        response = requests.get(
            event_url,
            headers=HEADERS,
            verify=False,
            timeout=10
        )

        response.raise_for_status()

        html = response.text

    except Exception as e:

        print(
            f"Event sayfası hatası: {e}"
        )

        return []

    # --------------------------------------------------------
    # baseurls = [...]
    # --------------------------------------------------------

    match = re.search(
        r"baseurls\s*=\s*\[(.*?)\]",
        html,
        re.DOTALL | re.IGNORECASE
    )

    if not match:

        print(
            "Sunucu adresleri bulunamadı."
        )

        return []

    urls_text = match.group(1)

    # Tırnakları temizle
    urls_text = (
        urls_text
        .replace('"', "")
        .replace("'", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace(" ", "")
    )

    raw_servers = urls_text.split(",")

    servers = []

    for server in raw_servers:

        server = server.strip()

        if not server:
            continue

        if not server.startswith("http"):
            continue

        server = server.rstrip("/")

        if server not in servers:

            servers.append(server)

    return servers


# ============================================================
# SERVER'IN ÇALIŞIP ÇALIŞMADIĞINI KONTROL ET
# ============================================================

def build_stream_url(server, channel_id):

    server = server.rstrip("/")

    if "checklist" in server.lower():

        url = (
            f"{server}/"
            f"{channel_id}.m3u8"
        )

    else:

        url = (
            f"{server}/checklist/"
            f"{channel_id}.m3u8"
        )

    url = url.replace(
        "checklist//",
        "checklist/"
    )

    return url


# ============================================================
# SERVER TEST
# ============================================================

def test_server(server, active_site):

    test_id = "androstreamlivebs1"

    test_url = build_stream_url(
        server,
        test_id
    )

    test_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": active_site + "/",
        "Accept": "*/*",
    }

    try:

        response = requests.get(
            test_url,
            headers=test_headers,
            verify=False,
            timeout=7,
            allow_redirects=True
        )

        if response.status_code == 200:

            return server

    except Exception:

        pass

    return None


# ============================================================
# AKTİF SERVERLARI BUL
# ============================================================

def find_active_servers(
    servers,
    active_site
):

    active_servers = []

    print(
        f"Sunucu sayısı: "
        f"{len(servers)}"
    )

    # --------------------------------------------------------
    # Server kontrollerini paralel yap
    # --------------------------------------------------------

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        future_map = {
            executor.submit(
                test_server,
                server,
                active_site
            ): server
            for server in servers
        }

        for future in concurrent.futures.as_completed(
            future_map
        ):

            server = future_map[future]

            try:

                result = future.result()

            except Exception:

                result = None

            if result:

                print(
                    f"[AKTİF] {result}"
                )

                active_servers.append(
                    result
                )

            else:

                print(
                    f"[PASİF] {server}"
                )

    # --------------------------------------------------------
    # Aynı server tekrarını kaldır
    # --------------------------------------------------------

    unique_active_servers = []

    for server in active_servers:

        if server not in unique_active_servers:

            unique_active_servers.append(
                server
            )

    return unique_active_servers


# ============================================================
# TEK KANAL İÇİN ÇALIŞAN SERVER BUL
# ============================================================

def find_working_channel_url(
    channel_id,
    active_servers,
    active_site
):

    for server in active_servers:

        stream_url = build_stream_url(
            server,
            channel_id
        )

        headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Referer": active_site + "/",
            "Accept": "*/*",
        }

        try:

            response = requests.get(
                stream_url,
                headers=headers,
                verify=False,
                timeout=6,
                allow_redirects=True
            )

            if response.status_code == 200:

                return stream_url

        except Exception:

            continue

    return None


# ============================================================
# ANA KANAL TARAMASI
# ============================================================

def get_andro_content():

    print(
        "\n--- Andro Panel Taraması Başlatıldı ---"
    )

    results = []

    # --------------------------------------------------------
    # Kanal isimlerindeki duplicate kayıtları temizle
    # --------------------------------------------------------

    clean_channels = remove_duplicate_channels(
        channels
    )

    print(
        f"Tanımlı kanal sayısı: "
        f"{len(channels)}"
    )

    print(
        f"Benzersiz kanal sayısı: "
        f"{len(clean_channels)}"
    )

    # --------------------------------------------------------
    # Aktif domain
    # --------------------------------------------------------

    active_site = find_active_domain()

    if not active_site:

        print(
            "\nAktif site bulunamadı."
        )

        return results

    print(
        f"\nBulunan Domain: "
        f"{active_site}"
    )

    # --------------------------------------------------------
    # Server listesini al
    # --------------------------------------------------------

    servers = get_servers(
        active_site
    )

    if not servers:

        print(
            "Hiçbir sunucu bulunamadı."
        )

        return results

    print(
        f"Bulunan sunucu sayısı: "
        f"{len(servers)}"
    )

    # --------------------------------------------------------
    # Aktif serverları test et
    # --------------------------------------------------------

    active_servers = find_active_servers(
        servers,
        active_site
    )

    if not active_servers:

        print(
            "\nÇalışan sunucu bulunamadı."
        )

        return results

    print(
        f"\nToplam çalışan sunucu: "
        f"{len(active_servers)}"
    )

    # --------------------------------------------------------
    # HER KANALI SADECE 1 KEZ EKLE
    # --------------------------------------------------------

    added_names = set()

    for channel_id, channel_name in clean_channels:

        name_key = channel_name.strip().lower()

        # Ekstra güvenlik
        if name_key in added_names:

            print(
                f"[ATLANDI] Duplicate: "
                f"{channel_name}"
            )

            continue

        print(
            f"\nKontrol ediliyor: "
            f"{channel_name}"
        )

        # ----------------------------------------------------
        # Çalışan server bul
        # ----------------------------------------------------

        final_url = find_working_channel_url(
            channel_id,
            active_servers,
            active_site
        )

        if not final_url:

            print(
                f"[YOK] "
                f"{channel_name}"
            )

            continue

        # ----------------------------------------------------
        # LOGO YOK
        # tvg-logo YOK
        # ----------------------------------------------------

                # Kanal grubunu otomatik belirle
        if "bein sport" in channel_name.lower():
            group = BEIN_GROUP
        else:
            group = SPORTS_GROUP

        entry = (
            f'#EXTINF:-1 tvg-logo="{LOGO}" '
            f'group-title="{group}",'
            f'{channel_name}\n'
            f'#EXTVLCOPT:http-referrer='
            f'{active_site}/\n'
            f'{final_url}'
    )

        results.append(
            entry
        )

        added_names.add(
            name_key
        )

        print(
            f"[OK] {channel_name}"
        )

        print(
            f"     {final_url}"
        )

    return results


# ============================================================
# M3U OLUŞTUR
# ============================================================

def main():

    print(
        "========================================"
    )

    print(
        "        MAHSUN M3U GÜNCELLEYİCİ"
    )

    print(
        "========================================"
    )

    print(
        "\nİşlem Başladı..."
    )

    channels_result = get_andro_content()

    # --------------------------------------------------------
    # M3U başlığı
    # --------------------------------------------------------

    all_content = [
        
    ]

    all_content.extend(
        channels_result
    )

    # --------------------------------------------------------
    # Dosyaya yaz
    # --------------------------------------------------------

    try:

        with open(
            OUTPUT_FILENAME,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n".join(
                    all_content
                )
            )

        print(
            "\n========================================"
        )

        print(
            "BAŞARILI"
        )

        print(
            f"Kanal sayısı: "
            f"{len(channels_result)}"
        )

        print(
            f"Dosya: "
            f"{OUTPUT_FILENAME}"
        )

        print(
            "Logo: YOK"
        )

        print(
            "Duplicate: TEMİZLENDİ"
        )

        print(
            "========================================"
        )

    except IOError as e:

        print(
            f"\nDosya yazma hatası: {e}"
        )


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
