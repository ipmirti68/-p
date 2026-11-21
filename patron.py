
import asyncio
import os
import re
import requests
from pathlib import Path
from playwright.async_api import async_playwright

# ==================== KULLANICI AYARLARI ====================
BASLANGIC_DOMAIN_NUM = 1082
CIKTI_DOSYASI = "mirti.m3u"
GROUP = "🟩◆  beIN SPORTS 🖥"

SABIT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
# ============================================================


def get_active_taraftarium_url(start_num, max_attempts=15):
    headers = {"User-Agent": SABIT_USER_AGENT}

    print("🌐 [ADIM 1] Aktif Taraftarium domaini aranıyor...")

    for i in range(max_attempts):
        current_num = start_num + i
        test_url = f"https://taraftarium{current_num}.xyz"

        print(f"🔎 {test_url} test ediliyor...")

        try:
            response = requests.get(
                test_url,
                headers=headers,
                timeout=4,
                allow_redirects=False
            )

            if response.status_code == 200:
                print(f"✅ AKTİF DOMAIN BULUNDU: {test_url}")
                return test_url

            elif response.status_code in [301, 302, 307, 308]:
                print(f"⏩ Yönlendirme bulundu, atlanıyor: {test_url}")

        except requests.RequestException:
            continue

    print("⚠️ Yeni domain bulunamadı. Başlangıç adresi kullanılacak.")
    return f"https://taraftarium{start_num}.xyz"


def kanal_adi_duzenle(kanal_adi):
    kanal_adi = kanal_adi.strip()

    if "⭕" not in kanal_adi:
        kanal_adi += " ᴴᴰ⭕"

    return kanal_adi


def kanal_adi_normalize(kanal_adi):
    """
    Karşılaştırma için kanal adını standart hale getirir.
    ⭕ işaretini ve gereksiz boşlukları dikkate almaz.
    """
    kanal_adi = kanal_adi.replace("⭕", "")
    kanal_adi = re.sub(r"\s+", " ", kanal_adi)
    return kanal_adi.strip().casefold()


def m3u_blok_olustur(url, kanal_adi, referer_url):
    if not referer_url.endswith("/"):
        referer_url += "/"

    if "/ex1/" in url:
        url = url.replace("/ex1/", "/taraftarium/")

    kanal_adi = kanal_adi_duzenle(kanal_adi)

    return (
        f'#EXTINF:-1 group-title="{GROUP}",{kanal_adi}\n'
        f'#EXTVLCOPT:http-referrer={referer_url}\n'
        f'#EXTVLCOPT:http-user-agent={SABIT_USER_AGENT}\n'
        f"{url}\n"
    )


def m3u_bloklara_ayir(lines):
    """
    M3U dosyasını başlık ve kanal bloklarına ayırır.
    Diğer grupların satırlarını değiştirmeden korur.
    """
    baslik = []
    bloklar = []
    mevcut_blok = []

    for line in lines:
        if line.startswith("#EXTINF:"):
            if mevcut_blok:
                bloklar.append("".join(mevcut_blok))

            mevcut_blok = [line]

        elif mevcut_blok:
            mevcut_blok.append(line)

        else:
            baslik.append(line)

    if mevcut_blok:
        bloklar.append("".join(mevcut_blok))

    return baslik, bloklar


def blok_grubunu_bul(blok):
    ilk_satir = blok.splitlines()[0] if blok.splitlines() else ""

    match = re.search(r'group-title="([^"]*)"', ilk_satir)

    if match:
        return match.group(1)

    return ""


def blok_kanal_adini_bul(blok):
    ilk_satir = blok.splitlines()[0] if blok.splitlines() else ""

    if "," in ilk_satir:
        return ilk_satir.split(",", 1)[1].strip()

    return ""


def sadece_bein_grubunu_guncelle(yeni_bloklar, dosya_yolu):
    """
    Yalnızca hedef GROUP grubunu günceller.

    - Diğer grupları korur.
    - Aynı isimli beIN kanalının bağlantısını yeniler.
    - Tarama sırasında bulunamayan eski beIN kanallarını korur.
    - Hiç yeni kanal bulunmadıysa dosyaya dokunmaz.
    """

    if not yeni_bloklar:
        print("⚠️ Yeni kanal bulunmadı. Mevcut M3U listesi korunuyor.")
        return

    dosya = Path(dosya_yolu)

    if dosya.exists():
        eski_metin = dosya.read_text(encoding="utf-8-sig")
        lines = eski_metin.splitlines(keepends=True)
    else:
        lines = []

    baslik, eski_bloklar = m3u_bloklara_ayir(lines)

    if not any(line.strip() == "#EXTM3U" for line in baslik):
        baslik.insert(0, "#EXTM3U\n")

    diger_gruplar = []
    eski_bein_bloklari = []

    for blok in eski_bloklar:
        grup = blok_grubunu_bul(blok)

        if grup == GROUP:
            eski_bein_bloklari.append(blok)
        else:
            diger_gruplar.append(blok)

    # Yeni kanalları isimlerine göre hazırla.
    yeni_kanal_haritasi = {}

    for blok in yeni_bloklar:
        kanal_adi = blok_kanal_adini_bul(blok)
        anahtar = kanal_adi_normalize(kanal_adi)

        if anahtar:
            yeni_kanal_haritasi[anahtar] = blok

    birlesmis_bein = []
    kullanilanlar = set()

    # Eski beIN kanallarını koru.
    # Yeni bağlantısı bulunanların bağlantısını güncelle.
    for eski_blok in eski_bein_bloklari:
        eski_ad = blok_kanal_adini_bul(eski_blok)
        anahtar = kanal_adi_normalize(eski_ad)

        if anahtar in yeni_kanal_haritasi:
            if anahtar not in kullanilanlar:
                birlesmis_bein.append(yeni_kanal_haritasi[anahtar])
                kullanilanlar.add(anahtar)
        else:
            birlesmis_bein.append(eski_blok)

    # Daha önce listede olmayan yeni kanalları ekle.
    for anahtar, yeni_blok in yeni_kanal_haritasi.items():
        if anahtar not in kullanilanlar:
            birlesmis_bein.append(yeni_blok)
            kullanilanlar.add(anahtar)

    # Diğer gruplar aynen korunur.
    # Sadece beIN grubu güncellenmiş haliyle sona eklenir.
    son_metin = "".join(baslik)
    son_metin += "".join(diger_gruplar)
    son_metin += "".join(birlesmis_bein)

    # Önce geçici dosyaya yaz, ardından asıl dosyanın yerine koy.
    gecici_dosya = dosya.with_name(dosya.name + ".tmp")

    try:
        gecici_dosya.write_text(son_metin, encoding="utf-8")
        os.replace(gecici_dosya, dosya)

    except Exception:
        if gecici_dosya.exists():
            gecici_dosya.unlink()
        raise

    print("\n✅ M3U GÜNCELLEME TAMAMLANDI")
    print(f"📁 Dosya: {dosya_yolu}")
    print(f"🛡️ Korunan diğer grup sayısı: {len(diger_gruplar)}")
    print(f"📺 Eski beIN kayıt sayısı: {len(eski_bein_bloklari)}")
    print(f"🆕 Yeni taramada bulunan kanal: {len(yeni_kanal_haritasi)}")
    print(f"💾 Son beIN kayıt sayısı: {len(birlesmis_bein)}")


async def main():
    hedef_url = get_active_taraftarium_url(BASLANGIC_DOMAIN_NUM)

    yeni_bloklar = []

    async with async_playwright() as p:
        print("🚀 [ADIM 2] Playwright başlatılıyor...")

        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent=SABIT_USER_AGENT,
            viewport={"width": 1280, "height": 720}
        )

        page = await context.new_page()

        async def trafik_filtresi(route, request):
            if (
                request.resource_type in ["stylesheet", "font", "image"]
                or any(
                    x in request.url
                    for x in [
                        "google",
                        "analytics",
                        "doubleclick",
                        "adnxs"
                    ]
                )
            ):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", trafik_filtresi)

        print(f"🛰️ [ADIM 3] Ana menü taranıyor: {hedef_url}")

        try:
            await page.goto(
                hedef_url,
                wait_until="domcontentloaded",
                timeout=15000
            )
            await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Ana sayfaya erişilemedi: {e}")
            await browser.close()
            return

        kanal_elementleri = await page.query_selector_all("a.channel-item")

        kesfedilen_kanallar = []

        for kutu in kanal_elementleri:
            href = await kutu.get_attribute("href")

            id_match = re.search(r"id=([^&]+)", href) if href else None

            if not id_match:
                continue

            kanal_id = id_match.group(1)

            kanal_adi_element = await kutu.query_selector(".channel-name")

            if kanal_adi_element:
                kanal_adi = (await kanal_adi_element.inner_text()).strip()
            else:
                kanal_adi = f"Kanal {kanal_id.upper()}"

            if "atv" in kanal_adi.lower() or "atv" in kanal_id.lower():
                print(f"⏭️ [ATLANTI] {kanal_adi} (ATV listeden çıkarıldı)")
                continue

            kesfedilen_kanallar.append({
                "id": kanal_id,
                "name": kanal_adi
            })

        total_kanal = len(kesfedilen_kanallar)

        print(f"📺 Toplam {total_kanal} kanal tespit edildi.")

        if total_kanal == 0:
            print("❌ Kanal bulunamadı. Eski liste korunuyor.")
            await browser.close()
            return

        for index, kanal in enumerate(kesfedilen_kanallar):
            kanal_id = kanal["id"]
            kanal_adi = kanal["name"]

            kanal_sayfa_url = f"{hedef_url}/channel.html?id={kanal_id}"

            print(
                f"\n⚡ [{index + 1}/{total_kanal}] "
                f"Tarama: {kanal_adi} (ID: {kanal_id})"
            )

            yakalanan_url = None
            link_yakalandi_olayi = asyncio.Event()

            async def istek_dinle(request):
                nonlocal yakalanan_url

                url = request.url

                if re.search(r"\.m3u8(\?|$)", url):
                    yakalanan_url = url
                    link_yakalandi_olayi.set()

            page.on("request", istek_dinle)

            try:
                await page.goto(
                    kanal_sayfa_url,
                    wait_until="domcontentloaded",
                    timeout=10000
                )

                try:
                    await asyncio.wait_for(
                        link_yakalandi_olayi.wait(),
                        timeout=6.0
                    )
                except asyncio.TimeoutError:
                    pass

                if yakalanan_url:
                    print(f"🎯 LINK BULUNDU: {yakalanan_url}")

                    yeni_blok = m3u_blok_olustur(
                        yakalanan_url,
                        kanal_adi,
                        hedef_url
                    )

                    yeni_bloklar.append(yeni_blok)

                    print(f"💾 Yeni kayıt hazırlandı: {kanal_adi}")

                else:
                    print("⚠️ Yayın linki bulunamadı. Eski kayıt korunacak.")

            except Exception as ex:
                print(f"❌ Sayfa hatası: {str(ex)[:100]}")

            finally:
                page.remove_listener("request", istek_dinle)

        await browser.close()

    # Tarama bittikten sonra sadece beIN grubu güncellenir.
    print("\n🔧 [ADIM 4] Sadece beIN SPORTS grubu güncelleniyor...")

    sadece_bein_grubunu_guncelle(
        yeni_bloklar,
        CIKTI_DOSYASI
    )

    print("\n🏁 İŞLEM TAMAMLANDI!")


if __name__ == "__main__":
    asyncio.run(main())
