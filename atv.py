def main():

    print("=" * 55)
    print("ATV - GÜNCEL DİZİLER SON 3 BÖLÜM")
    print("=" * 55)

    all_entries = []

    # Dosyayı en başta oluştur.
    with open(M3U_FILE, "a", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

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
            print("  BÖLÜM BULUNAMADI")
            continue

        added = 0

        for number, episode_url in episodes:

            print(f"\n  {name} - {number}. BÖLÜM")
            print("  YAYIN ADRESİ ARANIYOR...")

            stream = get_m3u8(episode_url)

            if not stream:
                print("  M3U8 BULUNAMADI")
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

            print("  BAŞARILI!")
            time.sleep(1)

        print(f"\n{name}: {added} bölüm eklendi.")

    # Bulunan kayıtları dosyaya yaz.
    if all_entries:

        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

            for entry in all_entries:
                f.write(entry.strip() + "\n\n")

        print(f"\n{M3U_FILE}: {len(all_entries)} kayıt oluşturuldu.")

        update_mirti(all_entries)

    else:
        print("\nHİÇBİR YAYIN BULUNAMADI.")
        print(f"{M3U_FILE} başlık dosyası oluşturuldu.")
        print("MIRTI68.M3U değiştirilmedi.")

    print("\nİŞLEM TAMAMLANDI!")
    print("=" * 55)


if __name__ == "__main__":
    main()
