import os
import re
import time
import html
import codecs
import shutil
import requests

from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ==========================================
# 【entity-KANAL D¦canonical_name=KANAL D】 - OTOMATIK SON 3 BOLUM
# cloudscraper YOK - sadece requests + yt-dlp
# ==========================================

BASE = "https://www.kanald.com.tr"
WORKER = "https://mak.sadecenjoy.workers.dev"

M3U = "mirti68.m3u"
MIRTI = M3U

GROUP = "KANALD Dizileri"
LIMIT = 3

DIZILER = {
    "daha-17": "Daha 17",
    "uzak-sehir": "【entity-Uzak Şehir¦canonical_name=Uzak Şehir】",
    "haysiyet": "Haysiyet",
    "guller-ve-gunahlar": "【entity-Güller ve Günahlar¦canonical_name=Güller ve Günahlar】",
    "susuz-yaz": "Susuz Yaz",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Safari/537.36"
    ),
    "Referer": BASE + "/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)

# ==========================================
# SAYFA OKU
# ==========================================

def get_page(url):
    for deneme in range(2):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception as e:
            print(f"  SAYFA HATA ({deneme+1}): {e}")
            time.sleep(2)
    return None

# ==========================================
# BOLUM NUMARASI
# ==========================================

def get_number(text):
    text = html.unescape(text or "")
    patterns = [
        r'(\d+)\s*\.?\s*bölüm',
        r'(\d+)\s*[-_]\s*bolum',
        r'bolum[-_ ](\d+)'
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return int(m.group(1))
    return None

# ==========================================
# POSTER BUL
# ==========================================

def get_poster(slug, series_url):
    source = get_page(series_url)
    if not source:
        return ""

    soup = BeautifulSoup(source, "html.parser")

    for prop in ["og:image", "twitter:image"]:
        tag = soup.find("meta", attrs={"property": prop})
        if not tag:
            tag = soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            poster = urljoin(BASE, html.unescape(tag["content"]))
            print("  POSTER:", poster)
            return poster

    for img in soup.find_all("img"):
        for attr in ["src", "data-src", "data-original"]:
            value = img.get(attr)
            if value and slug in value.lower():
                poster = urljoin(BASE, value)
                print("  POSTER:", poster)
                return poster

    print("  POSTER BULUNAMADI")
    return ""

# ==========================================
# GERCEK BOLUM LINKLERI
# ==========================================

def get_bolum_links(slug):
    url = f"{BASE}/{slug}/bolumler"
    print(f"\n  BÖLÜM SAYFASI: {url}")

    source = get_page(url)
    if not source:
        return []

    low = source.lower()
    if "fragmanlar" in low[:8000] and "/bolumler/" not in low[:15000]:
        print("  UYARI: Sayfa fragmanlara yönlenmiş, bölüm yok - ATLANIYOR")
        return []

    soup = BeautifulSoup(source, "html.parser")
    episodes = {}

    skip = [
        "fragman",
        "ön izleme",
        "on izleme",
        "on-izleme",
        "kamera arkası",
        "kamera-arkasi",
        "fotoğraf",
        "foto galeri",
        "sahne",
        "tanıtım",
        "tanitim"
    ]

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(BASE, href)
        title = a.get_text(" ", strip=True)
        combined = (title + " " + full).lower()

        if f"/{slug}/bolumler/" not in full.lower():
            continue
        if "fragman" in full.lower():
            continue
        if any(x in combined for x in skip):
            continue

        number = get_number(title)
        if number is None:
            number = get_number(full)
        if number is None:
            continue

        episodes[number] = full

    result = sorted(episodes.items(), key=lambda x: x[0], reverse=True)[:LIMIT]

    print(f"  {len(result)} BÖLÜM BULUNDU")
    for number, link in result:
        print(f"  {number}. Bölüm -> {link}")

    return result

# ==========================================
# M3U8 BUL
# ==========================================

def find_m3u8(text):
    if not text:
        return None
    text = html.unescape(text)
    text = text.replace("\\/", "/").replace("\\u0026", "&")
    matches = re.findall(r'https?://[^"\'\s<>]+\.m3u8(?:\?[^"\'\s<>]*)?', text, re.I)
    for url in matches:
        url = url.rstrip("),;")
        if url.startswith("https://"):
            return url
    return None

# ==========================================
# EMBED ADRESI BUL
# ==========================================

def get_embed(source):
    soup = BeautifulSoup(source, "html.parser")

    tag = soup.find(attrs={"itemprop": "embedURL"})
    if tag:
        value = tag.get("content") or tag.get("href") or tag.get("src")
        if value:
            return urljoin(BASE, value)

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if "dailymotion.com" in src.lower():
            return urljoin(BASE, src)
    return None

# ==========================================
# VIDEO ADRESI
# ==========================================

def get_m3u8(bolum_url):
    try:
        source = get_page(bolum_url)
        if not source:
            return None

        direct = find_m3u8(source)
        if direct:
            print("  DIREKT M3U8 BULUNDU")
            return direct

        embed = get_embed(source)
        if not embed:
            print("  EMBED BULUNAMADI")
            return None

        print("  EMBED:", embed)

        if "dailymotion.com" in embed.lower():
            try:
                response = session.get(WORKER, params={"url": embed}, timeout=25)
                response.raise_for_status()
                result = find_m3u8(response.text)
                if result:
                    print("  WORKER M3U8 BULDU")
                    return result
            except Exception as e:
                print("  WORKER HATA:", e)

        try:
            import yt_dlp
            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "socket_timeout": 25
            }
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(embed, download=False)
                if info:
                    formats = info.get("formats", [])
                    formats.sort(key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
                    for fmt in formats:
                        stream = fmt.get("url", "")
                        if stream.startswith("https://") and "m3u8" in stream.lower():
                            return stream
        except Exception as e:
            print("  YT-DLP:", e)

    except Exception as e:
        print("  M3U8 HATA:", e)
    return None

# ==========================================
# M3U KAYDI
# ==========================================

def make_entry(name, number, stream, poster):
    title = f"TR: {name} - {number}. Bölüm"
    title = title.replace('"', "'")
    poster = (poster or "").replace('"', "'")
    return (
        f'#EXTINF:-1 tvg-name="{title}" '
        f'tvg-logo="{poster}" '
        f'group-title="{GROUP}",{title}\n'
        f'#EXTVLCOPT:http-referrer={BASE}/\n'
        f'{stream}'
    )

# ==========================================
# YARDIMCI - GRUP BUL / KAYIT AYIR
# ==========================================

def grup_bul(record_lines):
    for line in record_lines:
        if line.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', line)
            return m.group(1) if m else ""
    return ""

def kanal_adi(record_lines):
    for line in record_lines:
        if line.startswith("#EXTINF:"):
            return line.split(",", 1)[-1].strip()
    return ""

# ==========================================
# MIRTI LISTESINI KORUYARAK GÜNCELLE
# ==========================================

def update_mirti(new_entries, basarisiz):
    if not os.path.exists(MIRTI):
        print(f"[HATA] {MIRTI} bulunamadı!")
        return False

    raw = open(MIRTI, "rb").read()
    bom = raw.startswith(codecs.BOM_UTF8)
    metin = raw.decode("utf-8-sig", errors="ignore")
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()

    ilk_extinf = next((i for i, s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik = satirlar[:ilk_extinf]
    govde = satirlar[ilk_extinf:]

    records = []
    current = []
    for line in govde:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []
        current.append(line)
    if current:
        records.append(current)

    # Eski KanalD kayitlari icinden basarisiz dizilerin eski kayitlarini koru
    korunan = []
    for r in records:
        if grup_bul(r) != GROUP:
            continue
        ad = kanal_adi(r)
        for isim in basarisiz:
            if isim in ad or isim.split(" ")[0] in ad:
                korunan.append(r)
                print(f"  KORUNDU (eski): {ad}")
                break

    digerleri = [r for r in records if grup_bul(r) != GROUP]

    yeni_records = []
    for entry in new_entries:
        lines = [l for l in entry.strip().splitlines() if l.strip() != ""]
        yeni_records.append(lines)

    # Yeni + korunan, en sona ekle - diger gruplarin sirasi bozulmaz
    son_records = digerleri + yeni_records + korunan

    shutil.copy2(MIRTI, MIRTI + ".bak")

    sonuc = list(baslik)
    for record in son_records:
        sonuc.extend(record)

    yeni_metin = newline.join(sonuc) + newline
    temp = MIRTI + ".tmp"
    encoding = "utf-8-sig" if bom else "utf-8"
    with open(temp, "wb") as f:
        f.write(yeni_metin.encode(encoding))
    os.replace(temp, MIRTI)

    print(f"\n{MIRTI} GÜNCELLENDİ")
    print(f"Grup: {GROUP}")
    print(f"Yeni kayıt: {len(new_entries)}")
    print(f"Korunan eski: {len(korunan)}")
    print("EPG başlığı: KORUNDU")
    print("Diğer gruplar: KORUNDU")
    print(f"Yedek: {MIRTI}.bak")
    return True

# ==========================================
# ANA PROGRAM
# ==========================================

def main():
    print("=" * 50)
    print("KANAL D - SON 3 BÖLÜM TARAMASI")
    print("=" * 50)

    entries = []
    basarili = []
    basarisiz = []

    for slug, name in DIZILER.items():
        print("\n" + "=" * 40)
        print(name.upper())
        print("=" * 40)

        try:
            series_url = f"{BASE}/{slug}"
            poster = get_poster(slug, series_url)
            episodes = get_bolum_links(slug)

            if not episodes:
                print("BÖLÜM BULUNAMADI - DİZİ ATLANIYOR, DİĞERLERİNE DEVAM")
                basarisiz.append(name)
                continue

            added = 0
            for number, link in episodes:
                print(f"\n{number}. BÖLÜM")
                print("YAYIN ADRESİ ARANIYOR...")
                try:
                    stream = get_m3u8(link)
                except Exception as e:
                    print(f"  BÖLÜM HATA, ATLANIYOR: {e}")
                    continue

                if not stream:
                    print("M3U8 BULUNAMADI - BU BÖLÜM ATLANIYOR")
                    time.sleep(1)
                    continue

                entries.append(make_entry(name, number, stream, poster))
                print("BAŞARILI!")
                added += 1
                time.sleep(1)

            if added > 0:
                basarili.append(f"{name} ({added})")
                print(f"\n{name}: {added} kayıt")
            else:
                print(f"\n{name}: Hiç yayın bulunamadı, atlandı")
                basarisiz.append(name)

        except Exception as e:
            print(f"\n{name} HATA VERDİ, ATLANIYOR: {e}")
            basarisiz.append(name)
            continue

    print("\n" + "=" * 50)
    print(f"BAŞARILI: {', '.join(basarili) if basarili else 'YOK'}")
    if basarisiz:
        print(f"ATLANAN: {', '.join(basarisiz)}")
    print("=" * 50)

    if not entries and not basarisiz:
        print("\nHİÇ YAYIN BULUNAMADI.")
        print("MEVCUT M3U DOSYASI KORUNDU.")
        return

    # Sadece korunan varsa bile dosyaya dokunma, zaten aynisi duruyor
    if not entries:
        print("\nYeni yayin bulunamadi, eski liste korunuyor.")
        print("Dosya degistirilmedi.")
        return

    update_mirti(entries, basarisiz)
    print("\nTARAMA TAMAMLANDI!")
    print("=" * 50)

if __name__ == "__main__":
    main()
