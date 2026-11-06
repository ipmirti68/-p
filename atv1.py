from playwright.sync_api import sync_playwright
import re, os, json

OUTPUT_FILE = "mirti68.m3u"
MARKER = "# MIRTI68_ATV_AUTO"
GROUP = "📺 ULUSAL"
NAME = "ATV 🔴"
LOGO = "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"
PAGE_URL = "https://www.atv.com.tr/canli-yayin"

def get_atv_link():
    found=[]
    def on_dialog(d):
        urls=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        if urls:
            print(f"  [DIALOG] {urls[0][:120]}...")
            found.extend(urls)
        try:
            d.accept()
        except:
            pass
    def on_response(resp):
        try:
            url=resp.url
            if ".m3u8" in url:
                if url not in found:
                    print(f"  [URL] {url[:150]}...")
                    found.append(url)
            if "atv" in url.lower() or "player" in url.lower() or "token" in url.lower() or "live" in url.lower() or "ercdn" in url.lower():
                try:
                    text=resp.text()
                    if ".m3u8" in text:
                        m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', text)
                        for u in m:
                            if u not in found:
                                print(f"  [BODY] {u[:150]}...")
                                found.append(u)
                except:
                    pass
        except:
            pass

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        page.on("response", on_response)
        print(f"[*] {PAGE_URL} aciliyor...")
        try:
            page.goto(PAGE_URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)
            try:
                html=page.content()
                m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', html)
                for u in m:
                    if u not in found:
                        print(f"  [HTML] {u[:150]}...")
                        found.append(u)
            except:
                pass
            for sel in ["button", ".play-button", ".vjs-big-play-button", ".atv-player", "[class*=play]", ".jwplayer", "#player"]:
                try:
                    page.click(sel, timeout=1000)
                    page.wait_for_timeout(2000)
                except:
                    pass
            page.wait_for_timeout(8000)
        except Exception as e:
            print(f"  [!] hata: {e}")
        browser.close()
    
    # DUZELTILMIS SECIM - ONCE 1080p LIVE.ERCDN.NET
    print(f"[*] Toplam {len(found)} link bulundu")
    for u in found:
        if "trkvz-live.ercdn.net" in u and "1080p" in u:
            print(f"  [SECILDI - 1080p] {u[:150]}...")
            return u
    for u in found:
        if "trkvz-live.ercdn.net" in u and "atvhd" in u:
            print(f"  [SECILDI - LIVE] {u[:150]}...")
            return u
    # sonra daioncdn
    best=None
    max_len=0
    for u in found:
        if "trkvz.daioncdn.net/atv" in u:
            if len(u) > max_len:
                max_len=len(u)
                best=u
    if best:
        print(f"  [SECILDI - DAION] {best[:150]}...")
        return best
    if found:
        print(f"  [SECILDI - ILK] {found[0][:150]}...")
        return found[0]
    return None

def update_m3u(new_url):
    # REFERER EKLI - YAYIN CEKMESI ICIN
    new_block=f"""{MARKER}
#EXTINF:-1 tvg-name="{NAME}" tvg-logo="{LOGO}" group-title="{GROUP}",{NAME}
#EXTVLCOPT:http-referrer=https://www.atv.com.tr/
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36
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
    print(f"[OK] {OUTPUT_FILE} - ATV guncellendi - boyut: {len(final)}")

def main():
    print("ATV BASLADI - FINAL FIX")
    url=get_atv_link()
    if not url:
        print("[!] ATV ALINAMADI")
        return
    print(f"[+] ATV LINK: {url}")
    update_m3u(url)

if __name__=="__main__":
    main()
