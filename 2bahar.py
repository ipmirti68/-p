
import json
import os
import re

# ==========================================
# AYARLAR
# ==========================================

KAYNAK_DOSYASI = "ikinci_bahar_kaynaklar.json"
CIKTI_DOSYASI = "ikinci_bahar.m3u"

GROUP = "🎬 İKİNCİ BAHAR"

# ==========================================
# BÖLÜMLERİ OKU
# ==========================================

def bolumleri_oku():

    if not os.path.exists(KAYNAK_DOSYASI):
        print("Kaynak dosyası bulunamadı:", KAYNAK_DOSYASI)
        return []

    try:
        with open(KAYNAK_DOSYASI, "r", encoding="utf-8") as f:
            veriler = json.load(f)

        return veriler.get("episodes", [])

    except Exception as hata:
        print("JSON okuma hatası:", hata)
        return []


# ==========================================
# M3U OLUŞTUR
# ==========================================

def m3u_olustur(bolumler):

    liste = {}

    for bolum in bolumler:

        try:
            numara = int(bolum.get("episode", 0))
            adres = str(bolum.get("url", "")).strip()

            if numara < 1:
                continue

            if not adres.startswith(("https://", "http://")):
                print(f"{numara}. bölüm: Geçersiz adres")
                continue

            if not re.search(r"\.m3u8(?:$|[?#])", adres, re.I):
                print(f"{numara}. bölüm: Doğrudan M3U8 adresi değil")
                continue

            liste[numara] = adres

        except Exception as hata:
            print("Bölüm hatası:", hata)

    if not liste:
        print("Geçerli HLS yayını bulunamadı.")
        return False

    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for no, adres in sorted(liste.items()):

            isim = f"İKİNCİ BAHAR S01 E{no:02d}"

            f.write(
                f'#EXTINF:-1 group-title="{GROUP}",{isim}\n'
            )

            f.write(adres + "\n")

    print("\n================================")
    print("İKİNCİ BAHAR GÜNCELLENDİ")
    print("Dosya:", CIKTI_DOSYASI)
    print("Bölüm sayısı:", len(liste))
    print("Bölümler:", sorted(liste.keys()))
    print("================================")

    return True


# ==========================================
# ANA PROGRAM
# ==========================================

if __name__ == "__main__":

    bolumler = bolumleri_oku()

    if bolumler:
        m3u_olustur(bolumler)
    else:
        print("Bölüm kaynağı boş.")
