from playwright.sync_api import sync_playwright
import re, os

OUTPUT_FILE = "mirti68.m3u"
MARKER = "# MIRTI68_TV8_AUTO"
GROUP = "📺 ULUSAL"
NAME = "TV8"
LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png"
PAGE_URL = "https://www.tv8.com.tr/canli-yayin"
KEYWORD = "tv8"

def get_link():
    found=[]
    def on_dialog(dialog):
        m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', dialog.message)
        if m:
            print(f"[DIALOG] {m[0][:120]}...")
            found.extend(m)
        try:
            dialog.accept()
        except:
            pass
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        print(f"[*] {PAGE_URL} aciliyor...")
        try:
            page.goto(PAGE_URL, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            for sel in ["button", ".play-button", ".vjs-big-play-button", "[class*=play]"]:
                try:
                    page.click(sel, timeout=1500)
                    page.wait_for_timeout(2000)
                except:
                    pass
            page.wait_for_timeout(10000)
        except Exception as e:
            print(f"[!] goto hata: {e}")
        browser.close()
    for u in found:
        if "tv8" in u.lower() and "daioncdn.net" in u:
            return u
        if "tv8.daioncdn.net" in u:
            return u
    return found[0] if found else None

def update_m3u(new_url):
    new_block = f"""{MARKER}
#EXTINF:-1 tvg-name="{NAME}" tvg-logo="{LOGO}" group-title="{GROUP}",{NAME}
{new_url}
"""
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE,"w",encoding="utf-8").write(f"#EXTM3U\n\n{new_block}")
        return
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        old=f.read()
    if MARKER in old:
        before=old.split(MARKER)[0]
        after_part=old.split(MARKER,1)[1]
        m=re.search(r'\n# MIRTI68_', after_part)
        after=after_part[m.start():] if m else ""
        final=before.rstrip()+"\n"+new_block+after.lstrip()
    else:
        final=old.rstrip()+"\n\n"+new_block
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(final)
    print(f"[OK] {OUTPUT_FILE} guncellendi - TV8 - boyut: {len(final)}")

def main():
    print("TV8 BASLADI")
    url=get_link()
    if not url:
        print("[!] TV8 ALINAMADI")
        return
    print(f"[+] TV8 LINK: {url}")
    update_m3u(url)

if __name__=="__main__":
    main()
