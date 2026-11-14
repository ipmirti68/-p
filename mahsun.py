import requests
import re
import urllib3
import warnings
import concurrent.futures
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

OUTPUT_FILENAME = "mirti68.m3u"
BEIN_GROUP = "🟩◆  beIN SPORTS 🖥"
SPORTS_GROUP = "🟩◆ SPORTS ⭕"
LOGO = "https://i.imgur.com/OqdfQmw.png"
BASE_PATTERN = "https://mahsunsports{}.xyz"

channels = [
    ("androstreamlivebiraz1", "beIN SPORTS 1\u1D34\u1D30 Mahsun \u2B55"),
    ("androstreamlivebs1", "beIN SPORTS 1 Mahsun \u2B55"),
    ("androstreamlivebs2", "beIN SPORTS 2 Mahsun \u2B55"),
    ("androstreamlivebs3", "beIN SPORTS 3 Mahsun \u2B55"),
    ("androstreamlivebs4", "beIN SPORTS 4 Mahsun \u2B55"),
    ("androstreamlivebs5", "beIN SPORTS 5 Mahsun \u2B55"),
    ("androstreamlivebsm1", "beIN SPORTS Max 1 Mahsun \u2B55"),
    ("androstreamlivebsm2", "beIN SPORTS Max 2 Mahsun \u2B55"),
    ("androstreamlivess1", "S SPORTS 1 Mahsun \u2B55"),
    ("androstreamlivess2", "S SPORTS 2 Mahsun \u2B55"),
    ("androstreamlivets", "Tivibu SPOR Mahsun \u2B55"),
    ("androstreamlivets1", "Tivibu SPOR 1 Mahsun \u2B55"),
    ("androstreamlivets2", "Tivibu Sport 2 Mahsun \u2B55"),
    ("androstreamlivets3", "Tivibu Sport 3 Mahsun \u2B55"),
    ("androstreamlivets4", "Tivibu Sport 4 Mahsun \u2B55"),
    ("androstreamlivesm1", "Smart Sport 1 Mahsun \u2B55"),
    ("androstreamlivesm2", "Smart Sport 2 Mahsun \u2B55"),
    ("androstreamlivees1", "Euro Sport 1 Mahsun \u2B55"),
    ("androstreamlivees2", "Euro Sport 2 Mahsun \u2B55"),
    ("androstreamlivetb", "Tabii Mahsun \u2B55"),
    ("androstreamlivetb1", "Tabii 1 Mahsun \u2B55"),
    ("androstreamlivetb2", "Tabii 2 Mahsun \u2B55"),
    ("androstreamlivetb3", "Tabii 3 Mahsun \u2B55"),
    ("androstreamlivetb4", "Tabii 4 Mahsun \u2B55"),
    ("androstreamlivetb5", "Tabii 5 Mahsun \u2B55"),
    ("androstreamlivetb6", "Tabii 6 Mahsun \u2B55"),
    ("androstreamlivetb7", "Tabii 7 Mahsun \u2B55"),
    ("androstreamlivetb8", "Tabii 8 Mahsun \u2B55"),
    ("androstreamliveexn", "beIN SPORTS 1\u02E2\u1D30 Mahsun \u2B55"),
    ("androstreamliveexn1", "beIN SPORTS 1\u1D33\u1D34\u1D30 Mahsun \u2B55"),
    ("androstreamliveexn2", "DAZN 1 Mahsun \u2B55"),
    ("androstreamliveexn3", "S SPORT+ Mahsun \u2B55"),
    ("androstreamliveexn4", "S SPORT + Mahsun \u2B55"),
    ("androstreamliveexn5", "S SPORT + Mahsun \u2B55"),
    ("androstreamliveexn6", "S SPORT 2 Mahsun \u2B55"),
    ("androstreamliveexn7", "AZ TV Mahsun \u2B55"),
    ("androstreamliveexn8", "TRT TÜRK Mahsun \u2B55"),
]

def remove_duplicate_channels(channel_list):
    unique = []
    seen_names = set()
    for cid, cname in channel_list:
        name_key = cname.strip().lower()
        if name_key in seen_names:
            print(f"[DUPLICATE KANAL ATLANDI] {cname}")
            continue
        seen_names.add(name_key)
        unique.append((cid, cname))
    return unique

def find_active_domain():
    print("Aktif domain araniyor (10-99)...")
    def check_domain(index):
        url = BASE_PATTERN.format(index)
        try:
            response = requests.get(url, headers=HEADERS, timeout=5, verify=False, allow_redirects=True)
            if response.status_code == 200:
                return url
        except Exception:
            pass
        return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_domain, i) for i in range(10, 100)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                return result
    return None

def get_servers(active_site):
    event_url = f"{active_site}/event.html?id=androstreamlivebs1"
    print(f"Event sayfasi aliniyor: {event_url}")
    try:
        response = requests.get(event_url, headers=HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"Event sayfasi hatasi: {e}")
        return []
    match = re.search(r"baseurls\s*=\s*\[(.*?)\]", html, re.DOTALL | re.IGNORECASE)
    if not match:
        print("Sunucu adresleri bulunamadi.")
        return []
    urls_text = match.group(1)
    urls_text = urls_text.replace('"', "").replace("'", "").replace("\n", "").replace("\r", "").replace(" ", "")
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

def build_stream_url(server, channel_id):
    server = server.rstrip("/")
    if "checklist" in server.lower():
        url = f"{server}/{channel_id}.m3u8"
    else:
        url = f"{server}/checklist/{channel_id}.m3u8"
    url = url.replace("checklist//", "checklist/")
    return url

def test_server(server, active_site):
    test_id = "androstreamlivebs1"
    test_url = build_stream_url(server, test_id)
    test_headers = {"User-Agent": HEADERS["User-Agent"], "Referer": active_site + "/", "Accept": "*/*"}
    try:
        response = requests.get(test_url, headers=test_headers, verify=False, timeout=7, allow_redirects=True)
        if response.status_code == 200:
            return server
    except Exception:
        pass
    return None

def find_active_servers(servers, active_site):
    active_servers = []
    print(f"Sunucu sayisi: {len(servers)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {executor.submit(test_server, server, active_site): server for server in servers}
        for future in concurrent.futures.as_completed(future_map):
            server = future_map[future]
            try:
                result = future.result()
            except Exception:
                result = None
            if result:
                print(f"[AKTIF] {result}")
                active_servers.append(result)
            else:
                print(f"[PASIF] {server}")
    unique_active_servers = []
    for server in active_servers:
        if server not in unique_active_servers:
            unique_active_servers.append(server)
    return unique_active_servers

def find_working_channel_url(channel_id, active_servers, active_site):
    for server in active_servers:
        stream_url = build_stream_url(server, channel_id)
        headers = {"User-Agent": HEADERS["User-Agent"], "Referer": active_site + "/", "Accept": "*/*"}
        try:
            response = requests.get(stream_url, headers=headers, verify=False, timeout=6, allow_redirects=True)
            if response.status_code == 200:
                return stream_url
        except Exception:
            continue
    return None

def get_andro_content():
    print("\n--- Andro Panel Taramasi Baslatildi ---")
    results = []
    clean_channels = remove_duplicate_channels(channels)
    print(f"Tanimli kanal sayisi: {len(channels)}")
    print(f"Benzersiz kanal sayisi: {len(clean_channels)}")
    active_site = find_active_domain()
    if not active_site:
        print("\nAktif site bulunamadi.")
        return results
    print(f"\nBulunan Domain: {active_site}")
    servers = get_servers(active_site)
    if not servers:
        print("Hicbir sunucu bulunamadi.")
        return results
    print(f"Bulunan sunucu sayisi: {len(servers)}")
    active_servers = find_active_servers(servers, active_site)
    if not active_servers:
        print("\nCalisan sunucu bulunamadi.")
        return results
    print(f"\nToplam calisan sunucu: {len(active_servers)}")
    added_names = set()
    for channel_id, channel_name in clean_channels:
        name_key = channel_name.strip().lower()
        if name_key in added_names:
            print(f"[ATLANDI] Duplicate: {channel_name}")
            continue
        print(f"\nKontrol ediliyor: {channel_name}")
        final_url = find_working_channel_url(channel_id, active_servers, active_site)
        if not final_url:
            print(f"[YOK] {channel_name}")
            continue
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
        results.append(entry)
        added_names.add(name_key)
        print(f"[OK] {channel_name}")
        print(f"     {final_url}")
    return results

def main():
    print("========================================")
    print("        MAHSUN M3U GUNCELLEYICI")
    print("========================================")
    print("\nIslem Basladi...")
    channels_result = get_andro_content()
    if not channels_result:
        print("\nHic kanal bulunamadi, dosya degistirilmedi.")
        return
    bein_results = []
    sports_results = []
    for entry in channels_result:
        if BEIN_GROUP in entry:
            bein_results.append(entry)
        else:
            sports_results.append(entry)
    old_lines = []
    if os.path.exists(OUTPUT_FILENAME):
        with open(OUTPUT_FILENAME, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()
    final_lines = []
    bein_inserted = False
    sports_inserted = False
    skip_url = False
    skip_extvlcopt = False
    for line in old_lines:
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF:"):
            if BEIN_GROUP in line:
                if not bein_inserted:
                    final_lines.extend(bein_results)
                    bein_inserted = True
                skip_url = True
                skip_extvlcopt = True
                continue
            elif SPORTS_GROUP in line:
                if not sports_inserted:
                    final_lines.extend(sports_results)
                    sports_inserted = True
                skip_url = True
                skip_extvlcopt = True
                continue
            else:
                skip_url = False
                skip_extvlcopt = False
                final_lines.append(line)
        elif line.startswith("#EXTVLCOPT:"):
            if not skip_extvlcopt and line.strip() != "":
                final_lines.append(line)
        else:
            if not skip_url and line.strip() != "":
                final_lines.append(line)
    # --- GUVENLIK: Eski liste yoksa / cok kucukse ASLA uzerine yazma ---
    if not old_lines:
        print("\nDURDURULDU: mirti68.m3u bulunamadi / bos. Liste silinmesin diye yazilmadi.")
        return
    if len(old_lines) < 100:
        print(f"\nDURDURULDU: Eski liste cok kucuk ({len(old_lines)} satir). Yazilmadi.")
        return
    if len(final_lines) < len(old_lines) * 0.8:
        print(f"\nDURDURULDU: Yeni liste eski listenin %80inden kucuk ({len(final_lines)} < {len(old_lines)}). Liste silinmesin diye yazilmadi.")
        print("Eski liste korundu.")
        return
    # Yedek al
    try:
        import shutil
        shutil.copy(OUTPUT_FILENAME, OUTPUT_FILENAME + ".bak")
        print("Yedek alindi: mirti68.m3u.bak")
    except Exception as e:
        print(f"Yedek alinamadi: {e}")
    if not bein_inserted and bein_results:
        final_lines.extend(bein_results)
        print("\nNot: Eski beIN grubu bulunamadi, en sona eklendi.")
    if not sports_inserted and sports_results:
        final_lines.extend(sports_results)
        print("\nNot: Eski SPORTS grubu bulunamadi, en sona eklendi.")
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write("\n".join(final_lines))
            f.write("\n")
        print("\n========================================")
        print("BASARILI")
        print(f"Kanal sayisi: {len(channels_result)}")
        print(f"Dosya: {OUTPUT_FILENAME}")
        print("Gruplar kendi yerinde guncellendi.")
        print("========================================")
    except IOError as e:
        print(f"\nDosya yazma hatasi: {e}")

if __name__ == "__main__":
    main()

            if BEIN_GROUP in line:
                if not bein_inserted:
                    final_lines.extend(bein_results)
                    bein_inserted = True
                skip_url = True
                skip_extvlcopt = True
                continue
            elif SPORTS_GROUP in line:
                if not sports_inserted:
                    final_lines.extend(sports_results)
                    sports_inserted = True
                skip_url = True
                skip_extvlcopt = True
                continue
            else:
                skip_url = False
                skip_extvlcopt = False
                final_lines.append(line)
        elif line.startswith("#EXTVLCOPT:"):
            if not skip_extvlcopt and line.strip() != "":
                final_lines.append(line)
        else:
            if not skip_url and line.strip() != "":
                final_lines.append(line)
    if not bein_inserted and bein_results:
        final_lines.extend(bein_results)
        print("\nNot: Eski beIN grubu bulunamadi, en sona eklendi.")
    if not sports_inserted and sports_results:
        final_lines.extend(sports_results)
        print("\nNot: Eski SPORTS grubu bulunamadi, en sona eklendi.")
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write("\n".join(final_lines))
            f.write("\n")
        print("\n========================================")
        print("BASARILI")
        print(f"Kanal sayisi: {len(channels_result)}")
        print(f"Dosya: {OUTPUT_FILENAME}")
        print("Gruplar kendi yerinde guncellendi.")
        print("========================================")
    except IOError as e:
        print(f"\nDosya yazma hatasi: {e}")

if __name__ == "__main__":
    main()
