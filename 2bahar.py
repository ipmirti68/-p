
import re
import subprocess
import json
import os

# ==========================================
# AYARLAR
# ==========================================

KANAL_URL = "https://www.youtube.com/@%C4%B0kincibahardizi/videos"
CIKTI_DOSYASI = "ikinci_bahar.m3u"

GRUP = "🎬 İKİNCİ BAHAR"
KANAL_ADI = "İKİNCİ BAHAR"

# ==========================================
# YOUTUBE VİDEOLARINI TARA
# ==========================================

def videolari_getir():
    print("YouTube videoları taranıyor...")

    komut = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
        KANAL_URL
    ]

    sonuc = subprocess.run(
        komut,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if sonuc.returncode != 0:
        print("Hata:", sonuc.stderr)
        return []

    try:
        veri = json.loads(sonuc.stdout)
        return veri.get("entries", [])
    except Exception as hata:
        print("JSON okuma hatası:", hata)
        return []

# ==========================================
# BÖLÜM NUMARASINI BUL
# ==========================================

def bolum_numarasi(baslik):
    kaliplar = [
        r'(\d+)\s*\.?\s*bölüm',
        r'bölüm\s*(\d+)',
        r'episode\s*(\d+)',
        r'ep\s*(\d+)'
    ]

    for kalip in kaliplar:
        eslesme = re.search(kalip, baslik, re.IGNORECASE)
        if eslesme:
            return int(eslesme.group(1))

    return None

# ==========================================
# M3U OLUŞTUR
# ==========================================

def m3u_olustur(videolar):
    liste = []

    for video in videolar:
        video_id = video.get("id")
        baslik = video.get("title", "")

        if not video_id:
            continue

        numara = bolum_numarasi(baslik)

        if numara is None:
            continue

        url = "https://www.youtube.com/watch?v=" + video_id

        liste.append({
            "numara": numara,
            "url": url
        })

    # Bölüm numarasına göre sırala
    liste.sort(key=lambda x: x["numara"])

    # Aynı bölüm numaralarını tekrarlama
    benzersiz = {}
    for video in liste:
        benzersiz[video["numara"]] = video["url"]

    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as dosya:
        dosya.write("#EXTM3U\n")

        for numara in sorted(benzersiz):
            isim = f"{KANAL_ADI} S01 E{numara:02d}"

            dosya.write(
                f'#EXTINF:-1 group-title="{GRUP}",{isim}\n'
            )
            dosya.write(benzersiz[numara] + "\n")

    print("--------------------------------")
    print("M3U DOSYASI OLUŞTURULDU")
    print("Dosya:", CIKTI_DOSYASI)
    print("Bulunan bölüm:", len(benzersiz))
    print("--------------------------------")

# ==========================================
# PROGRAM
# ==========================================

if __name__ == "__main__":
    videolar = videolari_getir()

    if videolar:
        m3u_olustur(videolar)
    else:
        print("Video bulunamadı veya kanal taranamadı.")
