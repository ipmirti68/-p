description = await meta(page, 'meta[name="description"]') or description
        date = (await meta(page, 'meta[property="article:published_time"]')
                or await meta(page, 'meta[property="og:updated_time"]') or date)
        if date:
            date = date[:10]

        # Sayfanın HTML kaynağında açıkça bulunan HLS adreslerini de kontrol et.
        html = (await page.content()).replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&")
        for url in re.findall(r'https://[^\s"\'<>]+?\.m3u8(?:\?[^\s"\'<>]*)?', html, re.I):
            yakala(url)

        if not hls_urls:
            print("[HLS BULUNAMADI] Sayfa açık bir M3U8 adresi sunmadı; bu kayıt atlandı.")
            return None

        # İlk yakalanan yayın adresi kullanılır. Süreli token'lar zamanla sona erebilir.
        stream_url = hls_urls[0]
        print("[HLS BULUNDU]", stream_url)
        print("[LOGO]", logo or "Bulunamadı")
        print("[TARİH]", date or "Bulunamadı")
        return {
            "name": dizi["name"], "episode": episode, "date": date,
            "logo": logo or (BASE + "/favicon.ico"),
            "description": description, "url": stream_url,
        }
    except Exception as exc:
        print("[HATA]", dizi["name"], str(exc))
        return None
    finally:
        await page.close()


def listeyi_guncelle(yeni_diziler):
    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
        return False

    raw = open(M3U_FILE, "rb").read()
    bom = raw.startswith(codecs.BOM_UTF8)
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()

    # İlk EXTINF öncesindeki M3U/EPG başlığı aynen korunur.
    first_extinf = next((i for i, line in enumerate(lines) if line.startswith("#EXTINF:")), len(lines))
    header, body = lines[:first_extinf], lines[first_extinf:]

    records, current = [], []
    for line in body:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []
        current.append(line)
    if current:
        records.append(current)

    # Eski STAR bilgilendirme kaydı varsa koru.
    info = None
    for record in records:
        if grup_bul(record) == STAR_GROUP and "BİLGİLENDİRME" in kanal_adi(record).upper():
            info = record
            break
    if info is None:
        info = info_kaydi()

    # Yalnızca STAR grubunun eski kayıtları çıkarılır.
    others = [record for record in records if grup_bul(record) != STAR_GROUP]

    anchor = None
    for anchor_name in ANCHOR_GROUPS:
        matches = [i for i, record in enumerate(others) if grup_bul(record) == anchor_name]
        if matches:
            anchor = matches[-1]
            break
    if anchor is None:
        print("[HATA] Ekleme konumu bulunamadı. NOW / ATV / SHOW gruplarından biri listede olmalı.")
        print("Dosya değiştirilmedi.")
        return False

    new_records = [info] + [dizi_kaydi(d) for d in yeni_diziler]
    final_records = others[:anchor + 1] + new_records + others[anchor + 1:]

    shutil.copy2(M3U_FILE, M3U_FILE + ".bak")
    output = list(header)
    for record in final_records:
        output.extend(record)

    temp = M3U_FILE + ".tmp"
    encoding = "utf-8-sig" if bom else "utf-8"
    with open(temp, "wb") as file:
        file.write((newline.join(output) + newline).encode(encoding))
    os.replace(temp, M3U_FILE)

    print("\n===================================")
    print("STAR DİZİ GÜNCELLEMESİ TAMAMLANDI")
    print("Grup:", STAR_GROUP)
    print("Eklenen dizi:", len(yeni_diziler))
    print("Konum: bulunan ilk anchor grubunun hemen sonrası")
    print("Afiş / açıklama / tarih: sayfada bulunabildiği ölçüde eklendi")
    print("EPG başlığı ve diğer gruplar: KORUNDU")
    print("Yedek:", M3U_FILE + ".bak")
    print("===================================")
    return True


async def main():
    if not os.path.exists(M3U_FILE):
        print("[HATA] mirti68.m3u bulunamadı!")
        return
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        results = []
        try:
            for series in DIZILER:
                result = await dizi_bul(browser, series)
                if result:
                    results.append(result)
        finally:
            await browser.close()

    if not results:
        print("Hiçbir dizide açık HLS adresi bulunamadı. M3U değiştirilmedi.")
        return
    listeyi_guncelle(results)


if __name__ == "__main__":
    asyncio.run(main())
