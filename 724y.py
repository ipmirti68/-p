
import requests
import re
import unicodedata

SOURCE_URL = "https://raw.githubusercontent.com/umitm0d/-mittube/refs/heads/main/Umittube/umittube.m3u"

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟪◆ 7/24 DİZİ ⭕"

KANALLAR = [
    "cicek-taksi",
    "bizimkiler",
    "Kemal-sunal-1",
    "Kemal-sunal-2",
    "Trfilmler",
    "Emret-komutanim",
    "Gulsah-film",
    "cennet-mahallesi",
    "seksenler",
    "aski-memnu",
    "zengin-kiz",
    "yedi-numara",
    "soz-dizi",
    "kurtlar-vadisi-pusu",
    "sakarya-firat",
    "leyla-ile-mecnun",
    "behzatc",
    "yesil-deniz",
    "gonul-dagi",
    "sokagin-cocuklari",
    "sifir-bir",
    "guldur-guldur"
]

def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]", "", text.lower())

def main():

    print("GitHub listesinden güncel yayınlar alınıyor...")

    response = requests.get(
        SOURCE_URL,
        timeout=40,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()

    lines = response.text.splitlines()

    hedefler = {
        normalize(x): x for x in KANALLAR
    }

    bulunan = set()
    sonuc = ["#EXTM3U"]

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        if line.startswith("#EXTINF:"):

            if i + 1 < len(lines):

                url = lines[i + 1].strip()

                if url and not url.startswith("#"):

                    isim = line.split(",", 1)[-1].strip()
                    key = normalize(isim)

                    if key in hedefler:

                        # YouTube video ID bul
                        match = re.search(
                            r"/id/([^./?]+)",
                            url
                        )

                        if match:
                            video_id = match.group(1)

                            # YouTube kapak resmi
                            logo = (
                                f"https://i.ytimg.com/vi/"
                                f"{video_id}/hqdefault.jpg"
                            )
                        else:
                            logo = ""

                        yeni_isim = hedefler[key].upper()

                        sonuc.append(
                            f'#EXTINF:-1 tvg-logo="{logo}" '
                            f'group-title="{GROUP}",'
                            f'{yeni_isim} ⭕'
                        )

                        # Güncel yayın adresini koru
                        sonuc.append(url)

                        bulunan.add(key)

        i += 1

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(sonuc) + "\n")

    eksik = set(hedefler) - bulunan

    print("--------------------------------")
    print("GÜNCELLEME TAMAMLANDI")
    print("Bulunan kanal:", len(bulunan))
    print("Eksik kanal:", len(eksik))
    print("Afişler otomatik eklendi.")
    print("Dosya:", OUTPUT_FILE)

    if eksik:
        print("Bulunamayanlar:")
        for kanal in sorted(eksik):
            print("-", hedefler[kanal])

if __name__ == "__main__":
    main()
