
import requests
import re
from datetime import datetime, timezone

SAYFA = "https://inatsportv.live/canli-izle/bein-sports-1"

LOGO = "https://upload.wikimedia.org/wikipedia/commons/4/4e/BeIN_Sports_logo.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
}


def m3u_olustur(yayinlar=None):

    if yayinlar is None:
        yayinlar = []

    satirlar = ["#EXTM3U"]

    for yayin in yayinlar:

        isim = yayin["isim"]
        url = yayin["url"]

        satirlar.append(
            f'#EXTINF:-1 tvg-name="{isim}" tvg-logo="{LOGO}" group-title="SPOR",{isim}'
        )

        satirlar.append(url)

    with open("bein.m3u", "w", encoding="utf-8") as dosya:
        dosya.write("\n".join(satirlar) + "\n")

    print("[OK] bein.m3u oluşturuldu.")
    print("[KANAL]", len(yayinlar))


def kontrol():

    print("=" * 45)
    print("MIRTI TV - BEIN SPORTS 1")
    print("=" * 45)

    yayinlar = []

    try:

        cevap = requests.get(
            SAYFA,
            headers=HEADERS,
            timeout=30
        )

        print("[HTTP]", cevap.status_code)
        cevap.raise_for_status()

        html = cevap.text

        adresler = re.findall(
            r'https?://[^"\'\s<>]+',
            html
        )

        adresler = list(dict.fromkeys(adresler))

        rapor = [
            "BEIN SPORTS 1 KONTROL RAPORU",
            "Tarih: " + datetime.now(timezone.utc).isoformat(),
            "HTTP: " + str(cevap.status_code),
            "Bulunan bağlantı: " + str(len(adresler)),
            "Doğrulanmış yetkili yayın: " + str(len(yayinlar)),
            "",
            *adresler
        ]

        with open("bein_rapor.txt", "w", encoding="utf-8") as dosya:
            dosya.write("\n".join(rapor))

        print("[OK] Rapor oluşturuldu.")

    except Exception as hata:

        print("[HATA]", hata)

        with open("bein_rapor.txt", "w", encoding="utf-8") as dosya:
            dosya.write("KONTROL HATASI: " + str(hata))

    finally:

        m3u_olustur(yayinlar)


if __name__ == "__main__":
    kontrol()
