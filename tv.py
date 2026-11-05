from playwright.sync_api import sync_playwright
import re, os

OUTPUT_FILE = "mirti68.m3u"
MARKER = "# MIRTI68_ULUSAL_AUTO"
GROUP = "📺 ULUSAL"
EPG_URL = ""

CHANNELS = {
    "ATVp": {"page": "https://www.atv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": "atv"},
    "KANAL Dp": {"page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald"},
    "STAR TVp": {"page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv"},
    "SHOW TVp": {"page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "keyword": "showtv"},
    "TV8p": {"page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8"},
    "KANAL 7p": {"page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7"},
    "NOW TVp": {"page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv"},
    "TRT 1p": {"page": "https://www.trt1.com.tr/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt-1", "direct": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
}

def get_link(page_url, keyword):
    found = []
    def on_dialog(d):
        urls = re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        found.extend(urls)
        d.accept()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        pg.on("dialog", on_dialog)
        try:
            pg.goto(page_url, timeout=40000, wait_until="domcontentloaded")
            pg.wait_for_timeout(15000)
        except: pass
        b.close()
    for u in found:
        if keyword == "kanal7" and "kanal7.daioncdn.net" in u:
            return u
        if keyword in u.lower() and "daioncdn.net" in u:
            return u
    return found[0] if found else None

def main():
    print("MIRTI68 ULUSAL BASLADI")
    new_lines = [MARKER]
    for name, info in CHANNELS.items():
        url = info.get("direct") or get_link(info["page"], info["keyword"])
        if not url:
            print(f"[!] {name} alinamadi")
            continue
        print(f"[+] {name} OK")
        new_lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{info["logo"]}" group-title="{GROUP}",{name}')
        new_lines.append(url)
    new_block = "\n".join(new_lines) + "\n"

    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE,"w",encoding="utf-8").write(f"#EXTM3U\n\n{new_block}")
        return

    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        old = f.read()

    if MARKER in old:
        before = old.split(MARKER)[0]
        after_part = old.split(MARKER,1)[1]
        m = re.search(r'\n# MIRTI68_', after_part)
        after = after_part[m.start():] if m else ""
        final = before.rstrip() + "\n" + new_block + after.lstrip()
    else:
        final = old.rstrip() + "\n\n" + new_block

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(final)
    print(f"BITTI - {len(new_lines)//2} kanal guncellendi, diger kategoriler korundu")

if __name__ == "__main__":
    main()
