from playwright.sync_api import sync_playwright
import re, os

OUTPUT_FILE = "mirti68.m3u"
MARKER = "# MIRTI68_ATV_AUTO"
GROUP = "📺 ULUSAL"
NAME = "ATV"
LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"
PAGE_URL = "https://www.atv.com.tr/canli-yayin"
KEYWORD = "atv"

def get_atv_link():
    found=[]
    def on_dialog(dialog):
        # alert() icindeki m3u8'i yakala
        m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', dialog.message)
        if m:
            print(f"[DIALOG] {m[0][:100]}...")
            found.extend(m)
        try:
            dialog.accept()
        except:
            pass

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        print(f"[*] {PAGE_URL} aciliyor...")
        try:
            page.goto(PAGE_URL, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            # play butonlarini dene
            for sel in ["button", ".play-button", ".vjs-big-play-button", ".atv-player", "[class*=play]"]:
                try:
                    page.click(sel, timeout=1500)
                    print(f"[+] Click {sel}")
                    page.wait_for_timeout(2000)
                except:
                    pass
            page.wait_for_timeout(10000)
        except Exception as e:
            print(f"[!] goto hata: {e}")
        browser.close()
    
    # en iyi linki sec - trkvz.daioncdn.net olan ve atv iceren
    for u in found:
        if "atv" in u.lower() and "daioncdn.net" in u:
            return u
        if "daioncdn.net" in u:
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
        # bir sonraki MARKER'a kadar sil
        m=re.search(r'\n# MIRTI68_', after_part)
        after=after_part[m.start():] if m else ""
        final=before.rstrip()+"\n"+new_block+after.lstrip()
    else:
        # MARKER yoksa ULUSAL icine ekle veya sona ekle
        final=old.rstrip()+"\n\n"+new_block

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(final)
    print(f"[OK] {OUTPUT_FILE} guncellendi - boyut: {len(final)} - {NAME} korundu, digerleri silinmedi")

def main():
    print("ATV BASLADI")
    url=get_atv_link()
    if not url:
        print("[!] ATV ALINAMADI - dosya korunuyor")
        # fallback test icin senin verdigin ornek linki kullanma, bos birak
        return
    print(f"[+] ATV LINK: {url}")
    update_m3u(url)

if __name__=="__main__":
    main()
