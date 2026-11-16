
import requests
import re
import unicodedata
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/umitm0d/-mittube/refs/heads/main/Umittube/umittube.m3u"

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟪◆ 7/24 DİZİ ⭕"

KANALLAR = [
   
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

    print("Güncel kaynak indiriliyor...")

    r = requests.get(
        SOURCE_URL,
        timeout=40,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    r.raise_for_status()

    lines = r.text.splitlines()

    hedefler = {
        normalize(x): x.upper()
        for x in KANALLAR
    }

    sonuc = []
    bulunan = set()
    kanal_sayisi = 0

    i = 0

    while i < len(lines):

        line = lines[i]

        if line.startswith("#EXTINF:"):

            kanal_sayisi += 1

            isim = line.split(",", 1)[-1].strip()
            key = normalize(isim)

            if key in hedefler:

                # Sonraki satır yayın adresi
                url = (
                    lines[i + 1].strip()
                    if i + 1 < len(lines)
                    else ""
                )

                # YouTube video kimliği
                match = re.search(
                    r"/id/([^/?]+)",
                    url
                )

                logo = None

                if match:
                    video_id = match.group(1).split(".")[0]

                    if re.fullmatch(
                        r"[A-Za-z0-9_-]{11}",
                        video_id
                    ):
                        logo = (
                            "https://i.ytimg.com/vi/"
                            + video_id
                            + "/hqdefault.jpg"
                        )

                # Mevcut EXTINF satırını koruyarak değiştir
                new_line = line

                if logo:
                    if re.search(r'tvg-logo="[^"]*"', new_line):
                        new_line = re.sub(
                            r'tvg-logo="[^"]*"',
                            f'tvg-logo="{logo}"',
                            new_line,
                            count=1
                        )
                    else:
                        new_line = new_line.replace(
                            "#EXTINF:",
                            f'#EXTINF:-1 tvg-logo="{logo}"',
                            1
                        )

                new_line = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{GROUP}"',
                    new_line,
                    count=1
                )

                new_line = re.sub(
                    r',(.*)$',
                    f',{hedefler[key]} ⭕',
                    new_line
                )

                sonuc.append(new_line)
                bulunan.add(key)

            else:
                # Diğer kanallar aynen korunur
                sonuc.append(line)

        else:
            # Başlıklar, yorumlar ve yayın URL'leri korunur
            sonuc.append(line)

        i += 1

    # Kaynak boş veya eksik geldiyse mevcut çıktıyı ezme
    if kanal_sayisi == 0:
        raise Exception("Kaynak listede kanal bulunamadı!")

    temp_file = OUTPUT_FILE + ".tmp"

    Path(temp_file).write_text(
        "\n".join(sonuc) + "\n",
        encoding="utf-8"
    )

    Path(temp_file).replace(OUTPUT_FILE)

    print("--------------------------------")
    print("GÜNCELLEME TAMAMLANDI")
    print("Toplam kaynak kanalı:", kanal_sayisi)
    print("Düzenlenen dizi:", len(bulunan))
    print("Bulunamayan dizi:", len(hedefler) - len(bulunan))
    print("Korunan diğer kanallar:", kanal_sayisi - len(bulunan))
    print("Çıktı:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
