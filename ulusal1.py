
import os
import re
import requests
import urllib.parse

# ==================================================
# KULLANICI AYARLARI
# ==================================================

SOURCE_M3U_URL = os.environ.get("SOURCE_M3U_URL", "http://4.438069.xyz:2086/get.php?username=%40SeZR.12.11.22&password=2022xSezER.12.11%40&type=m3u_plus&output=ts").strip()

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


# ==================================================
# GRUP ADINI OKU
# ==================================================

def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""


# ==================================================
# M3U BAŞLIK VE KANAL KAYITLARINI AYIR
# ==================================================

def parse_m3u(lines):
    header = []
    entries = []
    current = None

    for line in lines:
        if line.startswith("#EXTINF:"):
            if current:
                entries.append(current)
            current = [line]

        elif current is not None:
            if line.strip():
                current.append(line)

        else:
            # EPG VE DİĞER TÜM BAŞLIK SATIRLARI
            header.append(line)

    if current:
        entries.append(current)

    return header, entries


# ==================================================
# KAYNAK M3U LİSTESİNİ OKU
# ==================================================

def kaynagi_oku(url):

    if not url:
        return None

    session = requests.Session()
    session.headers.update(HEADERS)

    links = [
        url,
        url.replace("http://", "https://", 1)
    ]

    for link in links:
        for deneme in range(2):
            try:
                print(f"[DENEME] {link.split('?')[0]} - {deneme + 1}")

                r = session.get(
                    link,
                    timeout=40,
                    allow_redirects=True
                )

                print("[STATUS]", r.status_code)

                if r.status_code == 200:
                    content = r.content.decode(
                        "utf-8-sig",
                        errors="replace"
                    )

                    if "#EXTM3U" in content:
                        return content

                if r.status_code == 403:
                    session.headers.update({
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1"
                    })

            except requests.RequestException as e:
                print("[!] Bağlantı hatası:", e)

    # ALTERNATİF PROXY DENEMELERİ

    enc = urllib.parse.quote(url, safe="")

    proxies = [
        f"https://api.allorigins.win/raw?url={enc}",
        f"https://api.codetabs.com/v1/proxy?quest={enc}"
    ]

    for plink in proxies:
        try:
            print("[PROXY] Alternatif bağlantı deneniyor...")

            r = session.get(plink, timeout=60)

            if r.status_code == 200:
                content = r.content.decode(
                    "utf-8-sig",
                    errors="replace"
                )

                if "#EXTM3U" in content:
                    return content

        except Exception as e:
            print("[!] Proxy hata:", e)

    return None


# ==================================================
# YAYIN ADRESİNİ BUL
# ==================================================

def get_stream(entry):

    for line in entry[1:]:
        line = line.strip()

        if line and not line.startswith("#"):
            return line

    return ""


# ==================================================
# GRUP ADINI DEĞİŞTİR
# ==================================================

def grup_degistir(extinf):

    if re.search(r'group-title="[^"]*"', extinf):
        return re.sub(
            r'group-title="[^"]*"',
            f'group-title="{FILM_GROUP}"',
            extinf,
            count=1
        )

    # group-title yoksa süre bilgisinden sonra ekle
    return re.sub(
        r'^(#EXTINF:-?\d+)',
        rf'\1 group-title="{FILM_GROUP}"',
        extinf,
        count=1
    )


# ==================================================
# KANAL ADININ SONUNA ⭕ EKLE
# ==================================================

def kanal_adi_emoji_ekle(extinf):

    if "," not in extinf:
        return extinf

    # Son virgülden sonrası kanal görünen adıdır
    prefix, kanal_adi = extinf.rsplit(",", 1)

    kanal_adi = kanal_adi.rstrip()

    # Zaten varsa tekrar ekleme
    if not kanal_adi.endswith("⭕"):
        kanal_adi += " ⭕"

    return prefix + "," + kanal_adi


# ==================================================
# YENİ KAYNAK YAYINLARINI HAZIRLA
# ==================================================

def yeni_yayinlari_hazirla(text):

    source_lines = text.splitlines()
    _, source_entries = parse_m3u(source_lines)

    new_entries = []
    seen_urls = set()

    for entry in source_entries:

        extinf = entry[0]

        # SADECE İSTENEN KAYNAK GRUBU
        if get_group(extinf) != SOURCE_GROUP:
            continue

        stream = get_stream(entry)

        if not stream.startswith(("http://", "https://")):
            continue

        # TEKRAR EDEN YAYINLARI ATLA
        if stream in seen_urls:
            continue

        seen_urls.add(stream)

        # HEDEF GRUP ADINI DEĞİŞTİR
        new_extinf = grup_degistir(extinf)

        # KANAL ADININ SONUNA ⭕ EKLE
        new_extinf = kanal_adi_emoji_ekle(new_extinf)

        # DİĞER KANAL BİLGİLERİNİ KORU
        new_entry = [new_extinf] + entry[1:]

        new_entries.append(new_entry)

    return new_entries


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    print("=" * 55)
    print("       MIRTI68 - ULUSAL GÜNCELLEME")
    print("=" * 55)

    if not SOURCE_M3U_URL:
        print("[HATA] SOURCE_M3U_URL tanımlanmamış.")
        return

    if not os.path.exists(M3U_FILE):
        print("[HATA] Ana liste bulunamadı:", M3U_FILE)
        return

    # ESKİ ANA LİSTEYİ OKU
    try:
        with open(
            M3U_FILE,
            "r",
            encoding="utf-8-sig"
        ) as f:
            old_lines = f.read().splitlines()

    except Exception as e:
        print("[HATA] Ana liste okunamadı:", e)
        return

    if not old_lines:
        print("[HATA] Ana liste boş.")
        return

    if not old_lines[0].startswith("#EXTM3U"):
        print("[HATA] M3U başlığı bulunamadı.")
        return

    # EPG VE BAŞLIK SATIRLARINI AYIR
    old_header, old_entries = parse_m3u(old_lines)

    print("[OK] M3U başlığı bulundu.")
    print("[OK] EPG başlık satırı:", len(old_header))

    # KAYNAĞI OKU
    text = kaynagi_oku(SOURCE_M3U_URL)

    if not text:
        print("[HATA] Kaynak okunamadı.")
        print("[KORUMA] Ana liste değiştirilmedi.")
        return

    # YENİ YAYINLARI HAZIRLA
    new_entries = yeni_yayinlari_hazirla(text)

    if not new_entries:
        print("[HATA] Kaynak grubunda yayın bulunamadı.")
        print("[KORUMA] Ana liste değiştirilmedi.")
        return

    print("[OK] Yeni yayın sayısı:", len(new_entries))

    # SADECE HEDEF GRUBU DEĞİŞTİR
    final_entries = []

    eklendi = False
    korunan = 0
    silinen = 0

    for entry in old_entries:

        group = get_group(entry[0])

        if group == FILM_GROUP:

            if not eklendi:
                final_entries.extend(new_entries)
                eklendi = True

            silinen += 1
            continue

        # DİĞER GRUPLARA DOKUNMA
        final_entries.append(entry)
        korunan += 1

    # HEDEF GRUP YOKSA EN SONA EKLE
    if not eklendi:
        print("[BİLGİ] Hedef grup bulunamadı, sona ekleniyor.")
        final_entries.extend(new_entries)

    # GEÇİCİ DOSYAYA YAZ
    temp_file = M3U_FILE + ".tmp"

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f:

            # ESKİ EPG VE BAŞLIK SATIRLARI AYNEN YAZILIR
            for line in old_header:
                f.write(line + "\n")

            # KANALLARI YAZ
            for entry in final_entries:
                for line in entry:
                    f.write(line + "\n")

        # DOSYA KONTROLÜ
        if not os.path.exists(temp_file):
            print("[HATA] Geçici dosya oluşturulamadı.")
            return

        if os.path.getsize(temp_file) == 0:
            print("[HATA] Geçici dosya boş.")
            os.remove(temp_file)
            return

        with open(
            temp_file,
            "r",
            encoding="utf-8"
        ) as check:

            first_line = check.readline().strip()

            if not first_line.startswith("#EXTM3U"):
                print("[HATA] Başlık kontrolü başarısız.")
                os.remove(temp_file)
                return

        # ANA DOSYAYI GÜVENLİ DEĞİŞTİR
        os.replace(temp_file, M3U_FILE)

    except Exception as e:

        print("[HATA] Dosya yazılamadı:", e)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        print("[KORUMA] Ana liste değiştirilmedi.")
        return

    # SONUÇ
    print()
    print("=" * 55)
    print("       ULUSAL GRUBU GÜNCELLENDİ")
    print("=" * 55)

    print("[OK] Yeni yayın:", len(new_entries))
    print("[OK] Eski hedef grup kaydı:", silinen)
    print("[OK] Korunan diğer kayıt:", korunan)
    print("[OK] EPG başlıkları: KORUNDU")
    print("[OK] Diğer gruplar: KORUNDU")
    print("[OK] Kanal adlarının sonuna ⭕ eklendi")
    print("[OK] Ana dosya:", M3U_FILE)

    print("=" * 55)


# ==================================================
# ÇALIŞTIR
# ==================================================

if __name__ == "__main__":
    main()
