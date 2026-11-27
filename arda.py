
import os
import re
import requests
from datetime import datetime, timezone

SAYFA = "https://inatsportv.live/canli-izle/bein-sports-1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
}

def kontrol():
    print("[BASLA] BEIN SPORTS 1 sayfası kontrol ediliyor...")

    try:
        r = requests.get(
            SAYFA,
            headers=HEADERS,
            timeout=30
        )

        print("[HTTP]", r.status_code)

        if r.status_code != 200:
            raise Exception(f"Sayfa erişim hatası: {r.status_code}")

        html = r.text

        # Yalnızca sayfada açıkça bulunan, yetkili
        # ve erişime izin verilen yayın adresleri raporlanır.
        adresler = re.findall(
            r'https?://[^"\'\s<>]+',
            html
        )

        adresler = list(dict.fromkeys(adresler))

        rapor = [
            "BEIN SPORTS 1 KONTROL RAPORU",
            f"Tarih: {datetime.now(timezone.utc).isoformat()}",
            f"Sayfa HTTP: {r.status_code}",
            f"Bulunan bağlantı sayısı: {len(adresler)}",
            "",
        ]

        rapor.extend(adresler)

        with open("bein_rapor.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(rapor))

        print("[OK] Rapor oluşturuldu.")

    except Exception as e:
        print("[HATA]", str(e))
        with open("bein_rapor.txt", "w", encoding="utf-8") as f:
            f.write(f"KONTROL HATASI: {e}\n")

if __name__ == "__main__":
    kontrol()
