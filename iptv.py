from playwright.sync_api import sync_playwright
import re, os

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆  ULUSAL 📺"

# İSTENEN SIRA: TRT1 - ATV - SHOW - KANAL D - STAR - NOW - KANAL 7 - TV8
CHANNELS = {
    "TRT 1 ⭕": {
        "page": "https://www.trt1.com.tr/canli-izle",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
        "keyword": "trt",
        "marker": "# MIRTI68_TRT1_AUTO",
        "fallback": "https://tv-trt1.medya.trt.com.tr/master.m3u8"
    },
    "ATV ⭕": {
        "page": "https://www.atv.com.tr/canli-yayin",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
        "keyword": "【entity-atv¦canonical_name=ATV】",
        "marker": "# MIRTI68_ATV_AUTO",
        "fallback": "https://rnttwmjcin.turknet.ercdn.net/lcpmvefbyo/atv/atv_720p.m3u8"
    },
    "SHOW ⭕": {"page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png", "keyword": "showtv", "marker": "# MIRTI68_SHOWTV_AUTO"},
    "KANAL D ⭕": {"page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald", "marker": "# MIRTI68_KANALD_AUTO"},
    "STAR  ⭕": {"page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv", "marker": "# MIRTI68_STARTV_AUTO"},
    "NOW ⭕": {"page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv", "marker": "# MIRTI68_NOWTV_AUTO"},
    "KANAL 7 ⭕": {"page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7", "marker": "# MIRTI68_KANAL7_AUTO"},
    "TV8 ⭕": {"page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8", "marker": "# MIRTI68_TV8_AUTO"},
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

def update_one_channel(marker, name, logo, new_url):
    new_block=f"""{marker}
#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{GROUP}",{name}
{new_url}
"""
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE,"w",encoding="utf-8").write(f"#EXTM3U\n\n{new_block}")
        return
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        old=f.read()
    if marker in old:
        before=old.split(marker)[0]
        after_part=old.split(marker,1)[1]
        m=re.search(r'\n# MIRTI68_', after_part)
        after=after_part[m.start():] if m else ""
        final=before.rstrip()+"\n"+new_block+after.lstrip()
    else:
        final=old.rstrip()+"\n\n"+new_block
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(final)

def reorder_file():
    """Dosyayı istenen sıraya sokar: Önce 8 ulusal, sonra mevcut listenin geri kalanı"""
    if not os.path.exists(OUTPUT_FILE):
        return
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        content=f.read()

    pattern = re.compile(r'(# MIRTI68_.*?)(?=\n# MIRTI68_|\Z)', re.DOTALL)
    blocks = {}
    order_in_file = []
    for m in pattern.finditer(content):
        block = m.group(1).strip()
        if not block:
            continue
        marker = block.splitlines()[0].strip()
        if marker not in blocks:
            blocks[marker] = block
            order_in_file.append(marker)

    temp = content
    for m in pattern.finditer(content):
        temp = temp.replace(m.group(1), "\n__MIRTI68_BLOCK__\n")
    other_blocks = []
    extinf_pattern = re.compile(r'(#EXTINF:.*?)(?=\n#EXTINF:|\Z)', re.DOTALL)
    for m in extinf_pattern.finditer(temp):
        b = m.group(1).strip()
        if b and "#EXTM3U" not in b and "__MIRTI68_BLOCK__" not in b and b not in other_blocks:
            if b.startswith("#EXTINF"):
                other_blocks.append(b)

    ordered_markers = [info["marker"] for info in CHANNELS.values()]

    new_content = "#EXTM3U\n\n"
    for marker in ordered_markers:
        if marker in blocks:
            new_content += blocks[marker] + "\n\n"
    for marker in order_in_file:
        if marker not in ordered_markers:
            new_content += blocks[marker] + "\n\n"
    for b in other_blocks:
        new_content += b + "\n\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(new_content.strip() + "\n")
    print("[SIRALAMA] TRT1-ATV-SHOW-KANAL D-STAR-NOW-KANAL7-TV8 en başa alındı, diğerleri sonra devam ediyor")

def main():
    print("MIRTI68 ULUSAL - 8 KANAL HEPSI atv1.py ICINDE")
    if not os.path.exists(OUTPUT_FILE):
        print(f"[!] {OUTPUT_FILE} yok, bos olusturuluyor")
        open(OUTPUT_FILE,"w",encoding="utf-8").write("#EXTM3U\n")
    
    ok=0
    for name,info in CHANNELS.items():
        url = None
        source = ""

        # 1. Önce her zaman siteden çekmeyi dene
        if info.get("page"):
            url = get_link(info["page"], info["keyword"])
            if url:
                source = "CEKILDI"

        # 2. Çekemediyse yedek link varsa onu kullan (TRT1 + ATV için)
        if not url and info.get("fallback"):
            url = info["fallback"]
            source = "YEDEK"
            print(f"[!] {name} CEKILEMEDI - yedek link kullaniliyor: {url[:100]}...")

        # 3. Hiçbiri yoksa eski linki koru
        if not url:
            print(f"[!] {name} ALINAMADI - eski link korunuyor")
            continue
        
        print(f"[+] {name} {source}: {url[:100]}...")
        update_one_channel(info["marker"], name, info["logo"], url)
        ok+=1
    
    reorder_file()
    
    print(f"[TAMAMLANDI] {ok}/8 kanal guncellendi - {OUTPUT_FILE} korundu - boyut: {os.path.getsize(OUTPUT_FILE)}")

if __name__=="__main__":
    main()
