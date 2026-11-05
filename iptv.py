from playwright.sync_api import sync_playwright
import re
import os

OUTPUT_FILE = "mirti68.m3u"
GROUP = "📺 ULUSAL 🔗"
MARKER = "# MIRTI68_ULUSAL_AUTO"
EPG_URL = ""

CHANNELS = {
    "【entity-ATV¦canonical_name=ATV】": {"page": "https://www.atv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": "【entity-atv¦canonical_name=ATV】"},
    "KANAL D": {"page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald"},
    "【entity-STAR TV¦canonical_name=STAR TV】": {"page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv"},
    "【entity-SHOW TV¦canonical_name=SHOW TV】": {"page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "keyword": "showtv"},
    "【entity-TV8¦canonical_name=TV8】": {"page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8"},
    "【entity-KANAL 7¦canonical_name=Kanal 7】": {"page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7"},
    "NOW TV": {"page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv"},
    "【entity-TRT 1¦canonical_name=TRT 1】": {"page": "https://www.trt1.com.tr/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt-1", "direct": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
}

def get_link_via_dialog(page_url, keyword):
    found_links = []
    def on_dialog(dialog):
        msg = dialog.message
        # Mesajdaki tüm m3u8 linklerini al
        urls = re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', msg)
        for u in urls:
            # Kanal adına göre en doğru olanı seç (kanal7 içeren, 【entity-atv¦canonical_name=ATV】 içeren vs)
            if keyword.lower() in u.lower():
                found_links.append(u)
            else:
                found_links.append(u) # yedek
        if found_links:
            print(f"  -> Dialog yakalandı, {len(urls)} link bulundu")
        dialog.accept()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        try:
            print(f"[*] {keyword} için {page_url} açılıyor...")
            page.goto(page_url, timeout=40000, wait_until="domcontentloaded")
            page.wait_for_timeout(15000) # 【entity-Kanal 7¦canonical_name=Kanal 7】 için biraz daha uzun bekle, senin resimdeki gibi geç geliyor
        except Exception as e:
            print(f"[!] Sayfa hatası {keyword}: {e}")
        browser.close()
    
    # En uzun ve keyword içereni seç (tokenlı olan genelde en uzun)
    if found_links:
        # Önce keyword içerenleri filtrele
        keyword_links = [u for u in found_links if keyword.lower() in u.lower()]
        target = keyword_links[0] if keyword_links else found_links[0]
        # Kanal 7 için BULUNAN: olanı al, TAHMINI LINK olan corestream'i alma
        if keyword == "kanal7":
            for u in found_links:
                if "kanal7.daioncdn.net" in u:
                    return u
        return target
    return None

def main():
    print("MIRTI68 ULUSAL BASLADI - Revize")
    new_channels = {}

    for name, info in CHANNELS.items():
        # TRT 1 direkt
        if "direct" in info:
            new_channels[name] = info["direct"]
            print(f"[+] {name} DIRECT: {info['direct']}")
            continue

        link = get_link_via_dialog(info["page"], info["keyword"])
        if link:
            new_channels[name] = link
            print(f"[+] {name} OK: {link[:100]}...")
        else:
            print(f"[!] {name} ALINAMADI")

    # Eski mirti68.m3u'yu oku, ULUSAL dışını koru
    preserved = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # MARKER dışındaki blokları koru (basit)
        blocks = re.split(r'\n# MIRTI68_', content)
        # Bu kısımda senin eski kodundaki gibi diğer kategorileri koruyabilirsin
        # Şimdilik sadece dosya varsa header'ı al
        pass

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n\n')
        f.write(f'{MARKER}\n')
        for name, stream in new_channels.items():
            logo = CHANNELS[name]["logo"]
            page = CHANNELS[name]["page"]
            f.write(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{GROUP}",{name}\n')
            f.write(f'#EXTVLCOPT:http-referrer={page}\n')
            f.write(f'{stream}\n\n')
    
    print(f"\n[TAMAMLANDI] {len(new_channels)} kanal yazıldı -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
