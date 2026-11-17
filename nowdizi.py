
    records = []
    current = []
    for line in govde:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []
        current.append(line)
    if current:
        records.append(current)

    # NOW grubunun mevcut bilgilendirme kaydını koru.
    info = None
    for record in records:
        if (
            grup_bul(record) == NOW_GROUP
            and "BİLGİLENDİRME" in kanal_adi(record).upper()
        ):
            info = record
            break
    if info is None:
        info = info_kaydi()

    # Sadece eski NOW grubunu çıkar; diğer bütün kayıtlar olduğu gibi kalır.
    digerleri = [r for r in records if grup_bul(r) != NOW_GROUP]

    # Öncelikle ATV grubunun arkasına, yoksa SHOW DİZİ grubunun arkasına ekle.
    anchor = None
    for anchor_name in ANCHOR_GROUPS:
        matches = [
            i for i, record in enumerate(digerleri)
            if grup_bul(record) == anchor_name
        ]
        if matches:
            anchor = matches[-1]
            break

    if anchor is None:
        print("[HATA] Ekleme konumu bulunamadı.")
        print("ATV DİZİ veya SHOW DİZİ grubu listede yok.")
        print("Dosya değiştirilmedi.")
        return False

    yeni_kayitlar = [info]
    yeni_kayitlar.extend(dizi_kaydi(d) for d in yeni_diziler)

    son_records = (
        digerleri[:anchor + 1]
        + yeni_kayitlar
        + digerleri[anchor + 1:]
    )

    # Yedek al ve geçici dosya üzerinden güvenli yaz.
    shutil.copy2(M3U_FILE, M3U_FILE + ".bak")

    sonuc = list(baslik)
    for record in son_records:
        sonuc.extend(record)

    yeni_metin = newline.join(sonuc) + newline
    temp = M3U_FILE + ".tmp"
    encoding = "utf-8-sig" if bom else "utf-8"

    with open(temp, "wb") as f:
        f.write(yeni_metin.encode(encoding))

    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("NOW DİZİ GÜNCELLEMESİ TAMAMLANDI")
    print("===================================")
    print("Grup:", NOW_GROUP)
    print("Eklenen dizi:", len(yeni_diziler))
    print("Konum: ATV DİZİ grubunun hemen sonrası (varsa)")
    print("Logo / açıklama / tarih: Bulunabildiği ölçüde eklendi")
    print("EPG başlığı: KORUNDU")
    print("Diğer gruplar: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("===================================")
    return True


async def main():
    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yeni_diziler = []

        try:
            for dizi in DIZILER:
                sonuc = await dizi_bul(browser, dizi)
                if sonuc:
                    yeni_diziler.append(sonuc)
        finally:
            await browser.close()

    if not yeni_diziler:
        print("\nHiçbir dizide açık ve kullanılabilir M3U8 adresi bulunamadı.")
        print("Mevcut M3U dosyası değiştirilmedi.")
        return

    listeyi_guncelle(yeni_diziler)


if __name__ == "__main__":
    asyncio.run(main())
