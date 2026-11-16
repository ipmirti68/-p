
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.kanald.com.tr"
BOLUM_URL = BASE_URL + "/esref-ruya/bolumler"

CIKTI = "esref_ruya.m3u"
GRUP = "🟪◆ EŞREF RÜYA ⭕"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

def bolum_numarasi(text):
    text = text.lower()

    if "ilk bölüm" in text:
        return 1

    m = re.search(r"(\d+)\s*\.?\s*bölüm", text)
    return int(m.group(1)) if m else None


def bolumleri_topla():
    bulunan = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    # Sayfaları sırayla tara
    for sayfa in range(1, 21):
        url = f"{BOLUM_URL}?page={sayfa}"

        print(f"Taranıyor: {url}")

        try:
            cevap = session.get(url, timeout=25)
            cevap.raise_for_status()

            soup = BeautifulSoup(cevap.text, "html.parser")

            sayfada_bolum = 0

            for a in soup.select("a[href]"):
                baslik = " ".join(a.get_text(" ", strip=True).split())
                href = a.get("href", "")

                numara = bolum_numarasi(baslik)

                if numara is None:
                    continue

                if "esref-ruya" not in href.lower():
                    continue

                tam_url = urljoin(BASE_URL, href)
                parsed = urlparse(tam_url)

                if parsed.netloc not in (
                    "www.kanald.com.tr",
                    "kanald.com.tr"
                ):
                    continue

                # Aynı bölümün farklı bağlantılarını tekrarlama
                if numara not in bulunan:
                    bulunan[numara] = {
                        "baslik": f"Eşref Rüya {numara}. Bölüm",
                        "url": tam_url
                    }
                    sayfada_bolum += 1

            print(f"Bu sayfada yeni bölüm: {sayfada_bolum}")

            time.sleep(1)

        except requests.RequestException as e:
            print("Sayfa alınamadı:", e)

    return bulunan


def m3u_olustur(bolumler):
    with open(CIKTI, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for numara in sorted(bolumler):
            bolum = bolumler[numara]

            f.write(
                f'#EXTINF:-1 group-title="{GRUP}",'
                f'{bolum["baslik"]}\n'
            )

            f.write(bolum["url"] + "\n")

    print("\nM3U dosyası oluşturuldu:", CIKTI)


def main():
    print("EŞREF RÜYA BÖLÜMLERİ TARANIYOR...")

    bolumler = bolumleri_topla()

    if not bolumler:
        print("Bölüm bulunamadı. Site yapısı değişmiş olabilir.")
        return

    print(f"\nToplam bulunan bölüm: {len(bolumler)}")

    m3u_olustur(bolumler)


if __name__ == "__main__":
    main()
