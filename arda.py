def main():
    print("--- 📡 GOLVAR SPOR TARANIYOR ---")

    session = make_session()

    try:
        # Ana sayfa ve cookie yenileme
        print("🌐 Siteye bağlanılıyor...")

        session.get(HOME_URL, timeout=25)
        response = session.get(HOME_URL, timeout=25)
        response.raise_for_status()

        response.encoding = response.apparent_encoding or "utf-8"

        # Kanal ve maçları bul
        channels = parse_items(response.text)

        if not channels:
            print("❌ Kanal veya maç bulunamadı!")
            sys.exit(1)

        print(f"🔎 Bulunan yayın: {len(channels)}")

        entries = []
        seen = set()

        for name, slug in channels:

            print(f"⏳ Kontrol ediliyor: {name}")

            title, stream = resolve_source(session, slug)

            if not stream:
                print(f"❌ Yayın bulunamadı: {name}")
                continue

            if stream in seen:
                continue

            # M3U8 doğrulaması
            valid = verify(session, stream)

            if not valid:
                print(f"❌ Çalışmayan yayın: {name}")
                continue

            seen.add(valid)

            channel_name = pretty(title or name)

            entries.append(
                f'#EXTINF:-1 tvg-logo="{STATIC_LOGO}" '
                f'group-title="{GROUP}",{channel_name}\n'
                f'#EXTVLCOPT:http-referrer={STREAM_REFERER}\n'
                f'{valid}'
            )

            print(f"✅ {channel_name}")

        # Hiç yayın yoksa eski dosyayı koru
        if not entries:
            print("❌ HİÇ ÇALIŞAN YAYIN BULUNAMADI!")
            print("Eski M3U dosyası korunuyor.")
            sys.exit(1)

        # Önce geçici dosyaya yaz
        temp_file = OUTPUT_FILENAME + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write("\n".join(entries))
            f.write("\n")

        # Başarılıysa eski dosyanın yerine geçir
        os.replace(temp_file, OUTPUT_FILENAME)

        print("\n✅ İŞLEM TAMAMLANDI")
        print(f"📺 Toplam yayın: {len(entries)}")
        print(f"💾 Dosya: {OUTPUT_FILENAME}")

    except Exception as e:
        print(f"❌ HATA: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
