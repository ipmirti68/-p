
import requests
import re
from datetime import datetime, timezone

SAYFA = "https://inatsportv.live/canli-izle/bein-sports-1"

LOGO = "https://upload.wikimedia.org/wikipedia/commons/4/4e/BeIN_Sports_logo.png"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
    )
}


def sayfa_kontrol():

    print("=" * 45)
    print("MIRTI TV - BEIN SPORTS 1 KONTROL")
    print("=" * 45)

    try:

        print("[BASLA] Sayfa açılıyor...")

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

        tarih = datetime.now(
            timezone.utc
        ).isoformat()

        print("[OK] Sayfa erişildi.")
        print("[BULUNAN]", len(adresler))

        rapor = []

        rapor.append(
            "BEIN SPORTS 1 KONTROL RAPORU"
        )

        rapor.append("Tarih: " + tarih)

        rapor.append(
            "Sayfa HTTP: " + str(cevap.status_code)
        )

        rapor.append(
            "Bulunan bağlantı sayısı: " + str(len(adresler))
        )

        rapor.append("")

        rapor.extend(adresler)

        with open(
            "bein_rapor.txt",
            "w",
            encoding="utf-8"
        ) as dosya:

            dosya.write("\n".join(rapor))

        print("[OK] bein_rapor.txt oluşturuldu.")

        m3u_olustur()

    except Exception as hata:

        print("[HATA]", hata)

        with open(
            "bein_rapor.txt",
            "w",
            encoding="utf-8"
        ) as dosya:

            dosya.write(
                "KONTROL HATASI\n" + str(hata)
            )

        m3u_olustur()


def m3u_olustur(yayin_url=None):

    icerik = "#EXTM3U\n"

    if yayin_url and yayin_url.startswith("https://"):

        icerik += (
            '#EXTINF:-1 '
            'tvg-name="BEIN SPORTS 1" '
            f'tvg-logo="{LOGO}" '
            'group-title="SPOR",BEIN SPORTS 1\n'
        )

        icerik += yayin_url + "\n"

    with open(
        "bein.m3u",
        "w",
        encoding="utf-8"
    ) as dosya:

        dosya.write(icerik)

    print("[OK] bein.m3u oluşturuldu.")

    if yayin_url is None:

        print("[BILGI] Doğrulanmış yayın adresi bulunmadığı için M3U boş.")


if __name__ == "__main__":

    sayfa_kontrol()

    print("=" * 45)
    print("KONTROL TAMAMLANDI")
    print("=" * 45)
