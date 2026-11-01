
def main():

    print("=" * 55)
    print("ATV - DİZİ BÖLÜMLERİ GÜNCELLENİYOR")
    print("=" * 55)

    M3U_FILE = "mirti68.m3u"
    ATV_GROUP = "📺 ATV DİZİLER"

    all_entries = []

    for slug, info in SERIES.items():

        name = info["name"]
        series_url = info["url"]

        print("\n" + "=" * 45)
        print(name.upper())
        print("=" * 45)

        poster = get_poster(
            series_url,
            slug,
            name
        )

        episodes = get_episode_links(
            series_url,
            slug,
            name
        )

        if not episodes:
            print("BÖLÜM BULUNAMADI")
            continue

        added = 0

        for number, episode_url in episodes:

            print(f"\n{name} - {number}. BÖLÜM")
            print("YAYIN ADRESİ ARANIYOR...")

            stream = get_m3u8(episode_url)

            if not stream:
                print("M3U8 BULUNAMADI")
                time.sleep(1)
                continue

            entry = make_entry(
                name,
                number,
                stream,
                poster
            )

            all_entries.append(entry)
            added += 1

            print("BAŞARILI!")
            time.sleep(1)

        print(f"{name}: {added} bölüm bulundu.")

    if not all_entries:
        print("\nYeni yayın bulunamadı.")
        print("Ana M3U listesi değiştirilmedi.")
        return

    # Yeni ATV kayıtlarını hazırla
    new_lines = []

    for entry in all_entries:
        new_lines.append(entry.strip())

    # Ana listeyi oku
    old_lines = []

    if os.path.exists(M3U_FILE):
        with open(
            M3U_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            old_lines = f.read().splitlines()

    # Eski ATV dizilerini ayıkla
    preserved = []
    skip_url = False

    for line in old_lines:

        if line.startswith("#EXTINF:"):
            skip_url = ATV_GROUP in line
            if not skip_url:
                preserved.append(line)

        elif line.startswith("#EXTM3U"):
            continue

        else:
            if not skip_url:
                preserved.append(line)

    # Yeni kayıtları ekle
    with open(
        M3U_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("#EXTM3U\n")

        for line in preserved:
            f.write(line + "\n")

        for entry in new_lines:
            f.write(entry + "\n")

    print("\nATV DİZİLERİ GÜNCELLENDİ!")
    print("Yeni kayıt:", len(all_entries))
    print("Ana dosya:", M3U_FILE)
    print("Diğer kategoriler korundu.")

    print("\nİŞLEM TAMAMLANDI!")
    print("=" * 55)


if __name__ == "__main__":
    main()
