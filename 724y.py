
import requests
import re
import unicodedata
from pathlib import Path

# ==========================================
# MIRTI68 - 7/24 DIZI EKLEME BOTU
# MEVCUT LISTEYI KORUR
# ==========================================

SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "umitm0d/-mittube/refs/heads/main/"
    "Umittube/umittube.m3u"
)

OUTPUT_FILE = Path("mirti68.m3u")

GROUP = "🟪◆ DİZİ - 7/24  ⭕▶️"

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

    return re.sub(
        r"[^a-z0-9]",
        "",
        text.lower()
    )


def get_title(line):
    return line.split(",", 1)[-1].strip()


def read_entries(text):
    """M3U içindeki kanal bloklarını ayırır."""

    lines = text.splitlines()

    entries = []
    current = []

    for line in lines:

        if line.startswith("#EXTINF:"):

            if current:
                entries.append(current)

            current = [line]

        elif current:
            current.append(line)

    if current:
        entries.append(current)

    return entries


def set_group(line):

    if re.search(r'group-title="[^"]*"', line):

        return re.sub(
            r'group-title="[^"]*"',
            f'group-title="{GROUP}"',
            line,
            count=1
        )

    return line.replace(
        "#EXTINF:",
        f'#EXTINF: group-title="{GROUP}"',
        1
    )


def set_logo(line, url):

    match = re.search(
        r"/id/([^/?]+)",
        url
    )

    if not match:
        return line

    video_id = match.group(1).split(".")[0]

    if not re.fullmatch(
        r"[A-Za-z0-9_-]{11}",
        video_id
    ):
        return line

    logo = (
        "https://i.ytimg.com/vi/"
        + video_id
        + "/hqdefault.jpg"
    )

    if re.search(r'tvg-logo="[^"]*"', line):

        line = re.sub(
            r'tvg-logo="[^"]*"',
            f'tvg-logo="{logo}"',
            line,
            count=1
        )

    else:

        line = line.replace(
            "#EXTINF:",
            f'#EXTINF:-1 tvg-logo="{logo}"',
            1
        )

    return line


def main():

    print("=" * 45)
    print("MIRTI68 - 7/24 DIZI BOTU")
    print("=" * 45)

    # 1. MEVCUT LISTEYI KONTROL ET

    if not OUTPUT_FILE.exists():
        raise Exception(
            "mirti.m3u bulunamadı! "
            "Mevcut listen korunması için işlem durduruldu."
        )

    mevcut_text = OUTPUT_FILE.read_text(
        encoding="utf-8-sig"
    )

    if "#EXTINF:" not in mevcut_text:
        raise Exception(
            "Mevcut M3U listesinde kanal bulunamadı!"
        )

    mevcut_entries = read_entries(mevcut_text)

    print("Mevcut kanal sayısı:", len(mevcut_entries))

    # 2. KAYNAK LISTEYI INDIR

    print("Kaynak liste indiriliyor...")

    response = requests.get(
        SOURCE_URL,
        timeout=40,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    kaynak_entries = read_entries(response.text)

    if not kaynak_entries:
        raise Exception(
            "Kaynak listede kanal bulunamadı!"
        )

    print("Kaynak kanal sayısı:", len(kaynak_entries))

    # 3. HEDEFLERI HAZIRLA

    hedefler = {
        normalize(x): x.upper()
        for x in KANALLAR
    }

    bulunan = set()
    mevcut_isimler = set()
    mevcut_urller = set()

    # Mevcut listedeki isim ve adresleri kaydet

    for entry in mevcut_entries:

        extinf = entry[0]
        isim = normalize(get_title(extinf))

        mevcut_isimler.add(isim)

        for line in entry[1:]:

            if line.startswith("http://") or line.startswith("https://"):
                mevcut_urller.add(line.strip())

    # 4. SADECE ISTENEN DIZILERI BUL

    eklenecek = []

    for entry in kaynak_entries:

        extinf = entry[0]

        isim = get_title(extinf)
        key = normalize(isim)

        hedef = None

        for kanal_key, kanal_adi in hedefler.items():

            if kanal_key in key:
                hedef = kanal_adi
                bulunan.add(kanal_key)
                break

        if not hedef:
            continue

        # Yayın adresini bul

        url = ""

        for item in entry[1:]:

            item = item.strip()

            if item.startswith("http://") or item.startswith("https://"):
                url = item
                break

        if not url:
            print("Yayın adresi bulunamadı:", hedef)
            continue

        # Aynı kanal zaten mevcut mu?

        if normalize(hedef) in mevcut_isimler:
            print("Zaten mevcut:", hedef)
            continue

        # Aynı yayın adresi zaten mevcut mu?

        if url in mevcut_urller:
            print("Yayın adresi zaten mevcut:", hedef)
            continue

        # 5. YENI KANALIN EXTINF SATIRINI DUZENLE

        new_entry = list(entry)

        new_line = new_entry[0]

        new_line = set_logo(
            new_line,
            url
        )

        new_line = set_group(new_line)

        new_line = re.sub(
            r",(.*)$",
            f",{hedef} ⭕▶️",
            new_line
        )

        new_entry[0] = new_line

        eklenecek.append(new_entry)

        mevcut_isimler.add(normalize(hedef))
        mevcut_urller.add(url)

        print("EKLENECEK:", hedef)

    # 6. MEVCUT LISTENIN SONUNA EKLE

    if not eklenecek:

        print("--------------------------------")
        print("Yeni dizi bulunamadı veya hepsi mevcut.")
        print("Mevcut listeye dokunulmadı.")
        return

    yeni_icerik = mevcut_text.rstrip("\r\n")

    for entry in eklenecek:

        yeni_icerik += "\n" + "\n".join(entry)

    yeni_icerik += "\n"

    # 7. GUVENLI KAYDET

    temp_file = Path(str(OUTPUT_FILE) + ".tmp")

    temp_file.write_text(
        yeni_icerik,
        encoding="utf-8"
    )

    temp_file.replace(OUTPUT_FILE)

    # 8. RAPOR

    print("=" * 45)
    print("MIRTI68 GUNCELLEME TAMAMLANDI")
    print("=" * 45)

    print("Eski kanal:", len(mevcut_entries))
    print("Yeni eklenen:", len(eklenecek))
    print("Hedef dizi:", len(KANALLAR))
    print("Bulunan:", len(bulunan))
    print("Bulunamayan:", len(hedefler) - len(bulunan))
    print("Toplam kanal:", len(read_entries(yeni_icerik)))

    print("Mevcut liste korundu.")
    print("Çıktı:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
   
