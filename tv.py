from playwright.async_api import async_playwright
import asyncio
import os
import re

MASTER_FILE = "mirti68.m3u"
CIKIS_DOSYASI = "mirti68.m3u"
MARKER = "# MIRTI68_ULUSAL_AUTO"
GROUP = "📺 ULUSAL"
EPG_URL = ""

async def get_links(page):
    links = {}
    # Star
    print("[*] Star TVtest canlı yayın linki aranıyor...")
    try:
        await page.goto("https://www.startv.com.tr/canli-yayin", timeout=20000, wait_until="domcontentloaded")
        # senin mevcut yakalama kodun buradaydı - örnek:
        content = await page.content()
        m = re.search(r'https://dogus\.daioncdn\.net/startv/[^"\']+\.m3u8[^"\']*', content)
        if m:
            links["Star TV"] = m.group(0)
            print(f"[+] Star TVtest Linki Yakalandı: {links['Star TV TEST'][:70]}...")
    except Exception as e:
        print(f"[!] Star hata: {e}")

    # Show - aynı mantık
    print("[*] Show TVtset canlı yayın linki aranıyor...")
    try:
        await page.goto("https://www.showtv.com.tr/canli-yayin", timeout=20000, wait_until="domcontentloaded")
        content = await page.content()
        m = re.search(r'https://ciner\.daioncdn\.net/showtv/[^"\']+\.m3u8[^"\']*', content)
        if m:
            links["Show TV"] = m.group(0)
            print(f"[+] Show TVtset Linki Yakalandı: {links['Show TV TEST'][:70]}...")
    except Exception as e:
        print(f"[!] Show hata: {e}")

    # ATV
    print("[*] ATVtset canlı yayın linki aranıyor...")
    try:
        await page.goto("https://www.atv.com.tr/canli-yayin", timeout=30000, wait_until="domcontentloaded")
        content = await page.content()
        m = re.search(r'https://securevideotoken\.tmgrup\.com\.tr/webtv/secure\?[^"\']+', content)
        if m:
            links["ATV"] = m.group(0)
            print(f"[+] ATVtset Linki Yakalandı: {links['ATV TEST'][:70]}...")
    except Exception as e:
        print(f"[!] ATVtset sayfası tam yüklenemedi (Yine de devam ediliyor): {e}")
        # sayfa kaynağından yine dene
        try:
            content = await page.content()
            m = re.search(r'https://securevideotoken[^"\']+', content)
            if m:
                links["ATV"] = m.group(0)
        except: pass

    return links

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        kanallar = await get_links(page)
        await browser.close()

    if not kanallar:
        print("[!] Hiç link yakalanamadı, dosya yazılmayacak!")
        return

    # Yeni blok oluştur
    yeni_blok_lines = [MARKER]
    for isim, url in kanallar.items():
        yeni_blok_lines.append(f'#EXTINF:-1 tvg-name="{isim}" group-title="{GROUP}",{isim}')
        yeni_blok_lines.append(url)
    
    yeni_blok = "\n".join(yeni_blok_lines) + "\n"

    # Ana dosyayı oku
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8", errors="ignore") as f:
            icerik = f.read()
    else:
        icerik = f'#EXTM3U x-tvg-url="{EPG_URL}"\n'

    # ESKİ BLOĞU DÜZGÜN SİL - MARKER'dan sonraki bir sonraki # MIRTI68_ marker'ına kadar sil
    if MARKER in icerik:
        # MARKER öncesi
        oncesi = icerik.split(MARKER)[0]
        # MARKER sonrası içinde bir sonraki bölüm var mı? # MIRTI68_
        sonrasi_kisim = icerik.split(MARKER, 1)[1]
        # sonrasi_kisim içinde \n# MIRTI68_ ile başlayan bir yer ara
        match_next = re.search(r'\n# MIRTI68_', sonrasi_kisim)
        if match_next:
            sonrasi = sonrasi_kisim[match_next.start():]
        else:
            sonrasi = "" # yoksa dosya bitiyor
        final_icerik = oncesi.rstrip() + "\n" + yeni_blok + sonrasi.lstrip()
    else:
        # MARKER hiç yoksa sona ekle
        final_icerik = icerik.rstrip() + "\n\n" + yeni_blok

    # Header düzelt
    if not final_icerik.startswith("#EXTM3U"):
        final_icerik = f'#EXTM3U x-tvg-url="{EPG_URL}"\n' + final_icerik

    with open(CIKIS_DOSYASI, "w", encoding="utf-8") as f:
        f.write(final_icerik)

    print(f"\n[+] M3U Dosyası Oluşturuluyor -> {CIKIS_DOSYASI}")
    print(f"[+] Yazılan kanal sayısı: {len(kanallar)}")
    print(f"[+] Dosya boyutu: {os.path.getsize(CIKIS_DOSYASI)} byte")
    print("[+] İşlem tamamlandı")

if __name__ == "__main__":
    asyncio.run(main())
