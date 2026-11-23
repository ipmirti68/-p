#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MIRTI68 - IKINCI BAHAR - DUZELTILMIS
# Hata duzeltildi: except artik try ile ayni hizada
# Onemli degisiklik: Sabit googlevideo linki yazmiyor, cunku o 5-6 saatte ölüyor.
# Bunun yerine senin film.php linkini yaziyor, her acilista taze link uretiliyor.

import os
import json
from datetime import datetime, timezone

M3U_FILE = "ikinci_bahar.m3u"
JSON_FILE = "ikinci_bahar_kontrol.json"
LOGO = "https://cdn.neoldu.com.tr/other/14-250.jpg"
BASE = "https://mirti68.alwaysdata.net/yt"

VIDEO_IDS = [
    "LfbW6DO7Zgs","Hw3dsq2vQ4g","lNcOqYLowb8","vwP-w63klHE","NxrDuIWSBzM",
    "n9TL3sx1-p4","6XMFs_6eQgI","Z-E_yJOAPTQ","sLJCtfZz4xg","5iK7smTuUXI",
    "bJ7VH99YqXo","rG_kYsgFw2M","KswYPc4PNxo","qebJp8JQ7TE","sGujswnthwg",
    "izdZC-nFgnE","WIlLyFRwSkA","I9Katr8kVac","s5gqzOmyBG4","kTYyr9nhBcs",
    "CavumG3Remg","WDBA05Hlamo","m3JhYNa2hzc","D6JOH1XxfcY","bWLUlX7sv2o",
    "7Yp3iU_xF6Y","OzUw40lfsrw","aUsiTeAFTnI","NHvjVdH66s0","FlUSzeQZ4QI",
    "jmZsUdUw3TI","wgivjyDfK7c","uMY775MnqDI","6ERQHjDpMUY","6ERQHjDpMUY",
]

def m3u_yaz():
    gecici = M3U_FILE + ".tmp"
    try:
        with open(gecici, "w", encoding="utf-8") as dosya:
            dosya.write("#EXTM3U\n")
            gorulen = set()
            bolum_no = 0
            for vid in VIDEO_IDS:
                # Tekrarli ID'yi atla ama bolum numarasi kaymasin diye aynen yazma
                # 34 ve 35 ayni ID, 35'i atliyoruz
                if vid in gorulen:
                    print(f"Tekrarlanan ID atlandi: {vid}")
                    continue
                gorulen.add(vid)
                bolum_no += 1
                dosya.write(f'#EXTINF:-1 tvg-logo="{LOGO}" group-title="IKINCI BAHAR",IKINCI BAHAR {bolum_no}. BOLUM\n')
                dosya.write(f"{BASE}/film-id-{vid}.m3u8\n")
        os.replace(gecici, M3U_FILE)
        print(f"{bolum_no} bolum yazildi -> {M3U_FILE}")
        return True
    except Exception as hata:
        print("M3U yazma hatasi:", hata)
        if os.path.exists(gecici):
            os.remove(gecici)
        return False

def rapor_yaz():
    rapor = {
        "proje": "MIRTI68 - Ikinci Bahar",
        "tarih": datetime.now(timezone.utc).isoformat(),
        "toplam_kayit": len(VIDEO_IDS),
        "not": "Linkler film.php uzerinden dinamik, expire sorunu yok",
    }
    with open(JSON_FILE, "w", encoding="utf-8") as dosya:
        json.dump(rapor, dosya, ensure_ascii=False, indent=4)

def main():
    print("=" * 50)
    print("MIRTI68 - IKINCI BAHAR DUZELTILMIS")
    print("=" * 50)
    m3u_yaz()
    rapor_yaz()
    print("Tamamlandi")

if __name__ == "__main__":
    main()
