
import os
import re
import requests
import urllib.parse

SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "http://4.438069.xyz:2086/get.php?username=%40SeZR.12.11.22&password=2022xSezER.12.11%40&type=m3u_plus&output=ts")

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟨◆ ULUSAL ᴴᴰ⁺ ⭕"
SOURCE_GROUP = "► Ulusal"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Referer": "http://4.438069.xyz/",
}


def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""


def read_entries(lines):
    entries = []
    current = []

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF:"):
            if current:
                entries.append(current)
            current = [line]

        elif current and line:
            current.append(line)

    if current:
        entries.append(current)

    return entries


def kaynagi_oku(url):
    s = requests.Session()
    s.headers.update(HEADERS)

    for link in [url, url.replace("http://", "https://", 1)]:
        for deneme in range(2):
            try:
                print(f"[DENEME] {link} - {deneme+1}")

                r = s.get(link, timeout=40, allow_redirects=True)
                print(f"[STATUS] {r.status_code}")

                if r.status_code == 200 and "#EXTM3U" in r.text:
                    r.encoding = "utf-8"
                    return r.text

                if r.status_code == 403:
                    s.headers.update({
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1"
                    })

            except requests.RequestException as e:
                print(f"[!] Bağlantı hatası: {e}")

    enc = urllib.parse.quote(url, safe="")

    for plink in [
        f"https://api.allorigins.win/raw?url={enc}",
        f"https://api.codetabs.com/v1/proxy?quest={enc}"
    ]:
        try:
            print(f"[PROXY] {plink[:60]}...")

            r = s.get(plink, timeout=60)

            if r.status_code == 200 and "#EXTM3U" in r.text:
                r.encoding = "utf-8"
                return r.text

        except Exception as e:
            print(f"[!] Proxy hata: {e}")

    return None


def main():

    print("=" * 55)
    print("MIRTI68 - ULUSAL GÜNCELLEME")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL tanımlanmamış.")
        return

    if not os.path.exists(M3U_FILE):
        print("HATA: Ana liste bulunamadı.")
        return

    # ÖNCE MEVCUT LİSTEYİ OKU
    with open(M3U_FILE, "r", encoding="utf-8-sig") as f:
        old_lines = f.read().splitlines()

    if not old_lines or not old_lines[0].startswith("#EXTM3U"):
        print("HATA: Ana M3U başlığı bulunamadı.")
        print("Dosya değiştirilmedi.")
        return

    # EPG VE DİĞER BAŞLIK BİLGİLERİNİ AYNEN KORU
    m3u_header = old_lines[0]

    # KAYNAĞI OKU
    text = kaynagi_oku(SOURCE_M3U_URL)

    if not text:
        print("Kaynak okunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    source_entries = read_entries(text.splitlines())

    new_entries = []

    for entry in source_entries:

        extinf = entry[0]

        if get_group(extinf) != SOURCE_GROUP:
            continue

        stream = next(
            (x for x in entry[1:] if not x.startswith("#")),
            ""
        )

        if not stream.startswith(("http://", "https://")):
            continue

        new_extinf = re.sub(
            r'group-title="[^"]*"',
            f'group-title="{FILM_GROUP}"',
            extinf
        )

        if 'group-title=' not in new_extinf:
            new_extinf = new_extinf.replace(
                "#EXTINF:",
                f'#EXTINF:-1 group-title="{FILM_GROUP}"',
                1
            )

        new_entries.append([new_extinf] + entry[1:])

    if not new_entries:
        print("Kaynak grubunda yayın bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return

    # YENİ KAYITLARDA TEKRARLARI TEMİZLE
    seen_urls = set()
    unique_entries = []

    for entry in new_entries:

        stream = next(
            (x for x in entry[1:] if not x.startswith("#")),
            ""
        )

        if stream and stream not in seen_urls:
            seen_urls.add(stream)
            unique_entries.append(entry)

    old_entries = read_entries(old_lines)

    # SADECE ULUSAL GRUBUNU DEĞİŞTİR
    final_entries = []
    eklendi = False
    korunan = 0

    for entry in old_entries:

        if get_group(entry[0]) == FILM_GROUP:

            if not eklendi:
                final_entries.extend(unique_entries)
                eklendi = True

            continue

        final_entries.append(entry)
        korunan += 1

    if not eklendi:
        final_entries.extend(unique_entries)

    # ÖNCE GEÇİCİ DOSYAYA YAZ
    temp_file = M3U_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8", newline="\n") as f:

            # ESKİ EPG BAŞLIĞI AYNEN KORUNUR
            f.write(m3u_header + "\n")

            for entry in final_entries:
                for line in entry:
                    f.write(line + "\n")

        # BAŞARILI YAZIMDAN SONRA ANA DOSYAYI DEĞİŞTİR
        os.replace(temp_file, M3U_FILE)

    except Exception as e:

        print("[HATA] Dosya yazılamadı:", e)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        print("Ana liste korunmaya çalışıldı.")
        return

    print("=" * 55)
    print("ULUSAL GRUBU GÜNCELLENDİ")
    print("Yeni kayıt:", len(unique_entries))
    print("Korunan diğer kayıt:", korunan)
    print("EPG başlığı:", "KORUNDU")
    print("Ana dosya:", M3U_FILE)
    print("=" * 55)


if __name__ == "__main__":
    main()
