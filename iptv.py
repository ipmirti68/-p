from playwright.sync_api import sync_playwright
import re, os

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆  ULUSALᴴᴰ ⭕"

# İSTEDİĞİN SIRALAMA: TRT1 - ATV - SHOW - KANAL D - STAR - NOW - KANAL7 - TV8 - 360 - TV4 - TV2
CHANNELS = {
    "TRT 1 ⭕": {"page": "", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt-1", "marker": "# MIRTI68_TRT1_AUTO", "direct": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
    "ATV ⭕": {"page": "", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": "atv", "marker": "# MIRTI68_ATV_AUTO", "direct": "http://80.253.255.35:8000/play/a00g"},
    "SHOW ⭕": {"page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png", "keyword": "showtv", "marker": "# MIRTI68_SHOWTV_AUTO"},
    "KANAL D ⭕": {"page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald", "marker": "# MIRTI68_KANALD_AUTO"},
    "STAR  ⭕": {"page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv", "marker": "# MIRTI68_STARTV_AUTO"},
    "NOW ⭕": {"page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv", "marker": "# MIRTI68_NOWTV_AUTO"},
    "KANAL 7 ⭕": {"page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7", "marker": "# MIRTI68_KANAL7_AUTO"},
    "TV8 ⭕": {"page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8", "marker": "# MIRTI68_TV8_AUTO"},
    "360 ⭕": {"page": "https://www.tv360.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/360.png", "keyword": "360 tv", "marker": "# MIRTI68_360_AUTO"},
    "TV 4 ⭕": {"page": "https://www.tv4.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv4.png", "keyword": "tv 4", "marker": "# MIRTI68_TV4_AUTO"},
    "TV 2 ⭕": {"page": "https://www.tv2.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv2.png", "keyword": "tv2", "marker": "# MIRTI68_TV2_AUTO"},
    "BEYAZ ⭕": {"page": "https://m.beyaztv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/beyaz.png", "keyword": "beyax tv", "marker": "# MIRTI68_BEYAZ_AUTO"},
}

def get_link(page_url, keyword):
    found=[]
    def on_dialog(d):
        urls=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        if urls:
            print(f"  [DIALOG] {urls[0][:100]}...")
            found.extend(urls)
        try:
            d.accept()
        except:
            pass
    def on_response(resp):
        url=resp.url
        if ".m3u8" in url and keyword in url.lower():
            if url not in found:
                print(f"  [NETWORK] {url[:120]}...")
                found.append(url)
        elif ".m3u8" in url and "daioncdn.net" in url:
            if url not in found:
                print(f"  [NETWORK] {url[:120]}...")
                found.append(url)
        elif ".m3u8" in url and "ercdn.net" in url:
            if url not in found:
                print(f"  [NETWORK] {url[:120]}...")
                found.append(url)

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        page.on("response", on_response)
        print(f"[*] {keyword} -> {page_url} aciliyor...")
        try:
            page.goto(page_url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(7000)
            try:
                content=page.content()
                m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', content)
                for u in m:
                    if keyword in u.lower() or "daioncdn.net" in u or "ercdn.net" in u:
                        if u not in found:
                            print(f"  [SOURCE] {u[:120]}...")
                            found.append(u)
            except:
                pass
            for sel in ["button", ".play-button", ".vjs-big-play-button", "[class*=play]", ".atv-player", ".ciner-player"]:
                try:
                    page.click(sel, timeout=1200)
                    page.wait_for_timeout(1500)
                except:
                    pass
            page.wait_for_timeout(8000)
        except Exception as e:
            print(f"  [!] hata: {e}")
        browser.close()
    
    for u in found:
        if keyword in u.lower() and "daioncdn.net" in u:
            return u
    for u in found:
        if "daioncdn.net" in u or "ercdn.net" in u:
            return u
    return found[0] if found else None

def get_old_url(marker):
    """Eski dosyadan bu kanalın linkini al - çekilemezse eski link korunsun"""
    if not os.path.exists(OUTPUT_FILE):
        return None
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        old=f.read()
    if marker not in old:
        return None
    after = old.split(marker,1)[1]
    m = re.search(r'\n(https?://[^\s]+)', after)
    return m.group(1).strip() if m else None

def main():
    print("MIRTI68 ULUSAL - SIRALI LISTE")
    
    # 1. Önce tüm linkleri topla (sıra bozulmasın diye)
    results = {}
    for name, info in CHANNELS.items():
        if info.get("direct"):
            url = info["direct"]
            print(f"[+] {name} SABIT/DIRECT: {url}")
        else:
            url = get_link(info["page"], info["keyword"])
            if not url:
                url = get_old_url(info["marker"])
                if url:
                    print(f"[!] {name} ALINAMADI - eski link korundu: {url[:80]}")
                else:
                    print(f"[!] {name} ALINAMADI - atlaniyor")
                    continue
            else:
                print(f"[+] {name} OK: {url[:100]}...")
        results[name] = url

    # 2. Dosyayı SIRALI olarak baştan yaz - grup içi sıra her zaman korunur
    lines = ["#EXTM3U", ""]
    for name, info in CHANNELS.items():
        if name not in results:
            continue
        url = results[name]
        lines.append(info["marker"])
        lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{info["logo"]}" group-title="{GROUP}",{name}')
        lines.append(url)
        lines.append("")

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"[TAMAMLANDI] {len(results)}/{len(CHANNELS)} kanal guncellendi - SIRA: TRT1 > ATV > SHOW > KANAL D > STAR > NOW > KANAL7 > TV8 > 360 > TV4 > TV2 > BEYAZ - {OUTPUT_FILE} boyut: {os.path.getsize(OUTPUT_FILE)}")

if __name__=="__main__":
    main()
