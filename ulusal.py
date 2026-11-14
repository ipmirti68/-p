import os
import re
import requests
import urllib.parse

SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts")

M3U_FILE = "mirti68.m3u"
FILM_GROUP = "🟨◆ ULUSAL ᴴᴰ⁺ ⭕"
SOURCE_GROUP = "TR | ULUSAL"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Referer": "http://mekantv56.win/",
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
                    print("[!] 403 geldi, telefon başlığı ile tekrar deneniyor...")
                    s.headers.update({"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"})
                    continue
            except requests.RequestException as e:
                print(f"[!] Bağlantı hatası: {e}")
                continue
    # Direkt olmadıysa proxy ile dene
    enc = urllib.parse.quote(url, safe="")
    for plink in [f"https://api.allorigins.win/raw?url={enc}", f"https://api.codetabs.com/v1/proxy?quest={enc}"]:
        try:
            print(f"[PROXY] {plink[:60]}...")
            r = s.get(plink, timeout=60, allow_redirects=True)
            print(f"[PROXY STATUS] {r.status_code}")
            if r.status_code == 200 and "#EXTM3U" in r.text:
                r.encoding = "utf-8"
                return r.text
        except Exception as e:
            print(f"[!] Proxy hata: {e}")
    return None

def main():
    print("=" * 55)
    print("MIRTI68 - ÇARŞAMBA DİZİ GÜNCELLEME")
    print("=" * 55)
    if not SOURCE_M3U_URL:
        print("HATA: SOURCE_M3U_URL tanımlanmamış.")
        return
    text = kaynagi_oku(SOURCE_M3U_URL)
    if not text:
        print("Kaynak okunamadı: 403 / erişim engeli")
        print("Ana liste değiştirilmedi.")
        return
    source_entries = read_entries(text.splitlines())
    new_entries = []
    for entry in source_entries:
        extinf = entry[0]
        if get_group(extinf) != SOURCE_GROUP:
            continue
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if not stream.startswith(("http://", "https://")):
            continue
        new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{FILM_GROUP}"', extinf)
        if 'group-title=' not in new_extinf:
            new_extinf = new_extinf.replace("#EXTINF:", f'#EXTINF:-1 group-title="{FILM_GROUP}"', 1)
        yeni_entry = [new_extinf] + entry[1:]
        new_entries.append(yeni_entry)
    if not new_entries:
        print("ÇARŞAMBA grubunda yayın bulunamadı.")
        print("Ana liste değiştirilmedi.")
        return
    old_lines = []
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()
    old_entries = read_entries(old_lines)
    seen_urls = set()
    unique_entries = []
    for entry in new_entries:
        stream = next((x for x in entry[1:] if not x.startswith("#")), "")
        if stream not in seen_urls:
            seen_urls.add(stream)
            unique_entries.append(entry)
    # DUZELTME: Grubu en alta atma, eski yerinde tut
    final_entries = []
    eklendi = False
    korunan = 0
    for entry in old_entries:
        if get_group(entry[0]) == FILM_GROUP:
            if not eklendi:
                # Eski ULUSAL grubunun olduğu yere yeniyi koy
                final_entries.extend(unique_entries)
                eklendi = True
            # Eski ULUSAL kayıtlarını atla
            continue
        final_entries.append(entry)
        korunan += 1
    if not eklendi:
        # Eski dosyada ULUSAL grubu hiç yoksa en sona ekle
        final_entries.extend(unique_entries)
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")
    print("ulusal GÜNCELLENDİ")
    print("Yeni kayıt:", len(unique_entries))
    print("Korunan diğer kayıt:", korunan)
    print("Ana dosya:", M3U_FILE)

if __name__ == "__main__":
    main()
