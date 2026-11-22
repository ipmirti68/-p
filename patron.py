
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import re
import requests

from pathlib import Path
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# ============================================================
# MIRTI68 - TARAFTARIUM OTOMATIK M3U GUNCELLEYICI
# BEIN SPORTS + DIGER KANALLAR
# AYNI LOGO - IKI AYRI GRUP
# ============================================================

# ==================== KULLANICI AYARLARI ====================

BASLANGIC_DOMAIN_NUM = 1082

CIKTI_DOSYASI = "mirti.m3u"

# GRUPLAR
GROUP = "🟩◆  beIN SPORTS 🖥"
DIGER_GROUP = "📺 DİĞER KANALLAR"

# IKI GRUPTA DA AYNI LOGO
LOGO_URL = "https://files.catbox.moe/1yu2j7.png"

SABIT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Kanal sayfasında yayın bağlantısı bekleme süresi
YAYIN_BEKLEME = 6

# ============================================================
# AKTIF DOMAIN BUL
# ============================================================

def get_active_taraftarium_url(
    start_num,
    max_attempts=15
):

    headers = {
        "User-Agent": SABIT_USER_AGENT
    }

    print("\n🌐 [ADIM 1] AKTIF DOMAIN ARANIYOR")

    for i in range(max_attempts):

        current_num = start_num + i

        test_url = (
            f"https://taraftarium{current_num}.xyz"
        )

        print(f"🔎 TEST: {test_url}")

        try:

            response = requests.get(
                test_url,
                headers=headers,
                timeout=4,
                allow_redirects=True
            )

            if response.status_code == 200:

                aktif_url = response.url.rstrip("/")

                print(
                    f"✅ AKTIF DOMAIN: {aktif_url}"
                )

                return aktif_url

        except requests.RequestException:
            continue

    print(
        "⚠️ Aktif domain bulunamadi. "
        "Baslangic adresi kullanilacak."
    )

    return (
        f"https://taraftarium{start_num}.xyz"
    )


# ============================================================
# KANAL ADI DUZENLE
# ============================================================

def kanal_adi_duzenle(kanal_adi):

    kanal_adi = kanal_adi.strip()

    if "⭕" not in kanal_adi:

        kanal_adi += " ᴴᴰ⭕"

    return kanal_adi


# ============================================================
# KANAL ADI NORMALIZE
# ============================================================

def kanal_adi_normalize(kanal_adi):

    kanal_adi = kanal_adi.replace("⭕", "")

    kanal_adi = kanal_adi.replace("ᴴᴰ", "")

    kanal_adi = re.sub(
        r"\s+",
        " ",
        kanal_adi
    )

    return kanal_adi.strip().casefold()


# ============================================================
# BEIN SPORTS TESPITI
# ============================================================

def bein_kanali_mi(
    kanal_adi,
    kanal_id
):

    metin = (
        str(kanal_adi)
        + " "
        + str(kanal_id)
    )

    return bool(
        re.search(
            r"bein[\s_-]*sports",
            metin,
            re.IGNORECASE
        )
    )


# ============================================================
# KANAL GRUBUNU BELIRLE
# ============================================================

def kanal_grubunu_bul(
    kanal_adi,
    kanal_id
):

    if bein_kanali_mi(
        kanal_adi,
        kanal_id
    ):

        return GROUP

    # beIN olmayan HER kanal buraya gelir.
    # ATV dahil hiçbir kanal filtrelenmez.

    return DIGER_GROUP


# ============================================================
# M3U KANAL BLOGU OLUSTUR
# ============================================================

def m3u_blok_olustur(
    url,
    kanal_adi,
    referer_url,
    kanal_id
):

    if not referer_url.endswith("/"):

        referer_url += "/"

    if "/ex1/" in url:

        url = url.replace(
            "/ex1/",
            "/taraftarium/"
        )

    kanal_adi = kanal_adi_duzenle(
        kanal_adi
    )

    grup = kanal_grubunu_bul(
        kanal_adi,
        kanal_id
    )

    return (
        f'#EXTINF:-1 tvg-logo="{LOGO_URL}" '
        f'group-title="{grup}",{kanal_adi}\n'
        f'#EXTVLCOPT:http-referrer={referer_url}\n'
        f'#EXTVLCOPT:http-user-agent={SABIT_USER_AGENT}\n'
        f'{url}\n'
    )


# ============================================================
# M3U DOSYASINI BLOKLARA AYIR
# ============================================================

def m3u_bloklara_ayir(lines):

    baslik = []

    bloklar = []

    mevcut_blok = []

    for line in lines:

        if line.startswith("#EXTINF:"):

            if mevcut_blok:

                bloklar.append(
                    "".join(mevcut_blok)
                )

            mevcut_blok = [line]

        elif mevcut_blok:

            mevcut_blok.append(line)

        else:

            baslik.append(line)

    if mevcut_blok:

        bloklar.append(
            "".join(mevcut_blok)
        )

    return baslik, bloklar


# ============================================================
# BLOK GRUBUNU BUL
# ============================================================

def blok_grubunu_bul(blok):

    satirlar = blok.splitlines()

    ilk_satir = (
        satirlar[0]
        if satirlar
        else ""
    )

    match = re.search(
        r'group-title="([^"]*)"',
        ilk_satir
    )

    if match:

        return match.group(1)

    return ""


# ============================================================
# BLOK KANAL ADINI BUL
# ============================================================

def blok_kanal_adini_bul(blok):

    satirlar = blok.splitlines()

    ilk_satir = (
        satirlar[0]
        if satirlar
        else ""
    )

    if "," in ilk_satir:

        return ilk_satir.split(
            ",",
            1
        )[1].strip()

    return ""


# ============================================================
# IKI GRUBU GUVENLI GUNCELLE
# ============================================================

def iki_grubu_guncelle(
    yeni_bloklar,
    dosya_yolu
):

    if not yeni_bloklar:

        print(
            "\n⚠️ YENI YAYIN BULUNAMADI"
        )

        print(
            "🛡️ ESKI M3U DOSYASI KORUNDU"
        )

        return False

    dosya = Path(dosya_yolu)

    # Eski dosyayı oku.

    if dosya.exists():

        eski_metin = dosya.read_text(
            encoding="utf-8-sig"
        )

        lines = eski_metin.splitlines(
            keepends=True
        )

    else:

        lines = []

    baslik, eski_bloklar = m3u_bloklara_ayir(
        lines
    )

    # M3U başlığını kontrol et.

    baslik = [
        line
        for line in baslik
        if line.strip() != "#EXTM3U"
    ]

    baslik.insert(
        0,
        "#EXTM3U\n"
    )

    yonetilen_gruplar = {
        GROUP,
        DIGER_GROUP
    }

    diger_gruplar = []

    eski_yonetilen = []

    # Eski grupları ayır.

    for blok in eski_bloklar:

        grup = blok_grubunu_bul(
            blok
        )

        if grup in yonetilen_gruplar:

            eski_yonetilen.append(
                blok
            )

        else:

            # Diğer gruplara dokunulmaz.
            diger_gruplar.append(
                blok
            )

    # Yeni kanalları hazırla.

    yeni_harita = {}

    for blok in yeni_bloklar:

        grup = blok_grubunu_bul(
            blok
        )

        kanal_adi = blok_kanal_adini_bul(
            blok
        )

        anahtar = (
            grup,
            kanal_adi_normalize(kanal_adi)
        )

        if anahtar[1]:

            yeni_harita[anahtar] = blok

    birlesmis = []

    kullanilanlar = set()

    # Eski beIN ve diğer kanal kayıtlarını kontrol et.

    for eski_blok in eski_yonetilen:

        eski_grup = blok_grubunu_bul(
            eski_blok
        )

        eski_ad = blok_kanal_adini_bul(
            eski_blok
        )

        anahtar = (
            eski_grup,
            kanal_adi_normalize(eski_ad)
        )

        # Aynı kanalı ikinci kez ekleme.

        if anahtar in kullanilanlar:

            continue

        if anahtar in yeni_harita:

            # Yeni bağlantı varsa güncelle.

            birlesmis.append(
                yeni_harita[anahtar]
            )

        else:

            # Tarama sırasında bulunamayan eski kanalı koru.

            birlesmis.append(
                eski_blok
            )

        kullanilanlar.add(
            anahtar
        )

    # Yeni bulunan kanalları ekle.

    for anahtar, yeni_blok in yeni_harita.items():

        if anahtar not in kullanilanlar:

            birlesmis.append(
                yeni_blok
            )

            kullanilanlar.add(
                anahtar
            )

    # Grupları say.

    bein_sayisi = sum(
        1
        for blok in birlesmis
        if blok_grubunu_bul(blok) == GROUP
    )

    diger_sayisi = sum(
        1
        for blok in birlesmis
        if blok_grubunu_bul(blok) == DIGER_GROUP
    )

    # Son dosyayı oluştur.

    son_metin = "".join(baslik)

    son_metin += "".join(diger_gruplar)

    son_metin += "".join(birlesmis)

    # Önce geçici dosyaya yaz.

    gecici_dosya = dosya.with_name(
        dosya.name + ".tmp"
    )

    try:

        gecici_dosya.write_text(
            son_metin,
            encoding="utf-8"
        )

        os.replace(
            gecici_dosya,
            dosya
        )

    except Exception as e:

        print(
            "❌ DOSYA KAYIT HATASI:",
            e
        )

        if gecici_dosya.exists():

            gecici_dosya.unlink()

        return False

    # Sonuç.

    print("\n====================================")

    print(
        "✅ MIRTI68 GUNCELLEME TAMAMLANDI"
    )

    print("====================================")

    print(
        f"📁 DOSYA: {dosya_yolu}"
    )

    print(
        f"⚽ BEIN SPORTS: {bein_sayisi}"
    )

    print(
        f"📺 DIGER KANALLAR: {diger_sayisi}"
    )

    print(
        f"🛡️ KORUNAN DIGER KANAL: {len(diger_gruplar)}"
    )

    print(
        f"🖼️ ORTAK LOGO: {LOGO_URL}"
    )

    print("====================================")

    return True


# ============================================================
# ANA PROGRAM
# ============================================================

async def main():

    hedef_url = get_active_taraftarium_url(
        BASLANGIC_DOMAIN_NUM
    )

    yeni_bloklar = []

    async with async_playwright() as p:

        print(
            "\n🚀 [ADIM 2] PLAYWRIGHT BASLATILIYOR"
        )

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            user_agent=SABIT_USER_AGENT,
            viewport={
                "width": 1280,
                "height": 720
            }
        )

        page = await context.new_page()

        # Gereksiz kaynakları engelle.

        async def trafik_filtresi(
            route,
            request
        ):

            if (
                request.resource_type in [
                    "stylesheet",
                    "font",
                    "image"
                ]
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

        await page.route(
            "**/*",
            trafik_filtresi
        )

        print(
            f"\n🛰️ [ADIM 3] ANA MENU: {hedef_url}"
        )

        try:

            await page.goto(
                hedef_url,
                wait_until="domcontentloaded",
                timeout=15000
            )

            await page.wait_for_timeout(
                2000
            )

        except Exception as e:

            print(
                f"❌ ANA SAYFA HATASI: {e}"
            )

            await browser.close()

            return

        # Kanal kutularını bul.

        kanal_elementleri = await page.query_selector_all(
            "a.channel-item"
        )

        kesfedilen_kanallar = []

        gorulen_idler = set()

        for kutu in kanal_elementleri:

            href = await kutu.get_attribute(
                "href"
            )

            id_match = (
                re.search(
                    r"id=([^&]+)",
                    href
                )
                if href
                else None
            )

            if not id_match:

                continue

            kanal_id = id_match.group(1).strip()

            # Aynı ID tekrar eklenmesin.

            if kanal_id in gorulen_idler:

                continue

            gorulen_idler.add(
                kanal_id
            )

            kanal_adi_element = await kutu.query_selector(
                ".channel-name"
            )

            if kanal_adi_element:

                kanal_adi = (
                    await kanal_adi_element.inner_text()
                ).strip()

            else:

                kanal_adi = (
                    f"Kanal {kanal_id.upper()}"
                )

            # ATV dahil hiçbir kanal filtrelenmez.

            grup = kanal_grubunu_bul(
                kanal_adi,
                kanal_id
            )

            kesfedilen_kanallar.append({
                "id": kanal_id,
                "name": kanal_adi,
                "group": grup
            })

            print(
                f"📺 BULUNDU: {kanal_adi} | {grup}"
            )

        total_kanal = len(
            kesfedilen_kanallar
        )

        print(
            f"\n📺 TOPLAM {total_kanal} KANAL BULUNDU"
        )

        if total_kanal == 0:

            print(
                "❌ KANAL BULUNAMADI. ESKI DOSYA KORUNDU."
            )

            await browser.close()

            return

        # ====================================================
        # KANAL SAYFALARINI TARA
        # ====================================================

        for index, kanal in enumerate(
            kesfedilen_kanallar
        ):

            kanal_id = kanal["id"]

            kanal_adi = kanal["name"]

            grup = kanal["group"]

            kanal_sayfa_url = urljoin(
                hedef_url + "/",
                f"channel.html?id={kanal_id}"
            )

            print(
                f"\n⚡ [{index + 1}/{total_kanal}] "
                f"TARAMA: {kanal_adi}"
            )

            print(
                f"📂 GRUP: {grup}"
            )

            yakalanan_url = None

            link_yakalandi_olayi = asyncio.Event()

            async def istek_dinle(request):

                nonlocal yakalanan_url

                url = request.url

                if re.search(
                    r"\.m3u8(?:\?|$)",
                    url,
                    re.IGNORECASE
                ):

                    yakalanan_url = url

                    link_yakalandi_olayi.set()

            page.on(
                "request",
                istek_dinle
            )

            try:

                await page.goto(
                    kanal_sayfa_url,
                    wait_until="domcontentloaded",
                    timeout=10000
                )

                try:

                    await asyncio.wait_for(
                        link_yakalandi_olayi.wait(),
                        timeout=YAYIN_BEKLEME
                    )

                except asyncio.TimeoutError:

                    pass

                if yakalanan_url:

                    print(
                        f"🎯 LINK BULUNDU: {yakalanan_url}"
                    )

                    yeni_blok = m3u_blok_olustur(
                        yakalanan_url,
                        kanal_adi,
                        hedef_url,
                        kanal_id
                    )

                    yeni_bloklar.append(
                        yeni_blok
                    )

                    print(
                        f"💾 KAYIT HAZIR: {kanal_adi}"
                    )

                else:

                    print(
                        "⚠️ YAYIN LINKI BULUNAMADI"
                    )

                    print(
                        "🛡️ VARSA ESKI KAYIT KORUNACAK"
                    )

            except Exception as ex:

                print(
                    f"❌ SAYFA HATASI: {str(ex)[:150]}"
                )

            finally:

                page.remove_listener(
                    "request",
                    istek_dinle
                )

        await browser.close()

    # ====================================================
    # M3U GUNCELLE
    # ====================================================

    print(
        "\n🔧 [ADIM 4] IKI GRUP GUNCELLENIYOR"
    )

    iki_grubu_guncelle(
        yeni_bloklar,
        CIKTI_DOSYASI
    )

    print(
        "\n🏁 MIRTI68 ISLEMI TAMAMLANDI"
    )


# ============================================================
# PROGRAMI BASLAT
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
            
