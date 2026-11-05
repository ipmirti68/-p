from playwright.sync_api import sync_playwright
import re, os, json

OUTPUT_FILE = "mirti68.m3u"
MARKER = "# MIRTI68_ATV_AUTO"
GROUP = "📺 ULUSAL"
NAME = "ATV"
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
            # url'de m3u8 varsa direkt al
            if ".m3u8" in url:
                if url not in found:
                    print(f"  [URL] {url[:150]}...")
                    found.append(url)
            # body icinde m3u8 ara (JSON icinde)
            if "atv" in url.lower() or "player" in url.lower() or "token" in url.lower() or "live" in url.lower():
                try:
                    text=resp.text()
                    if ".m3u8" in text:
                        m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', text)
                        for u in m:
                            # trkvz.daioncdn.net icereni al
                            if "trkvz.daioncdn.net" in u or "daioncdn.net" in u:
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
            page.goto(PAGE_URL, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(10000)
            # sayfa iceriginde direkt ara
            try:
                html=page.content()
                m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', html)
                for u in m:
                    if "trkvz.daioncdn.net" in u and u not in found:
                        print(f"  [HTML] {u[:150]}...")
                        found.append(u)
            except:
                pass
            # JS degiskenlerinde ara
            try:
                # window icindeki player datasini dene
                for js in [
                    "document.documentElement.innerHTML",
                    "window.__INITIAL_DATA__",
                    "window.playerData",
                    "localStorage.getItem('player')",
                ]:
                    try:
                        txt=page.evaluate(f"() => {{ try {{ return JSON.stringify({js}) }} catch(e) {{ return {js} }} }}")
                        if txt and ".m3u8" in str(txt):
                            m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', str(txt))
                            for u in m:
                                if u not in found:
                                    print(f"  [JS] {u[:150]}...")
                                    found.append(u)
                    except:
                        pass
            except:
                pass
            # play butonlarini tikla
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
    
    # en iyi secim - trkvz.daioncdn.net ve atv iceren, en uzun tokenli olan
    best=None
    max_len=0
    for u in found:
        if "trkvz.daioncdn.net/atv" in u:
            if len(u) > max_len:
                max_len=len(u)
                best=u
    if best:
        return best
       # en iyi secim - once live.ercdn.net 1080p, sonra daioncdn
    for u in found:
        if "trkvz-live.ercdn.net" in u and "1080p" in u:
            return u
    for u in found:
        if "trkvz-live.ercdn.net" in u:
            return u
    return found[0] if found else None

def update_m3u(new_url):
    new_block=f"""{MARKER}
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
    print(f"[OK] {OUTPUT_FILE} - ATV guncellendi - boyut: {len(final)}")

def main():
    print("ATV BASLADI - FINAL")
    url=get_atv_link()
    if not url:
        print("[!] ATV ALINAMADI - senin verdigin ornek gibi link bulunamadi")
        print("[!] Ornek: https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app=...")
        return
    print(f"[+] ATV LINK: {url}")
    # token kontrolu
    if "e=" in url and "st=" in url:
        print("[+] Token'li link OK")
    update_m3u(url)

if __name__=="__main__":
    main()
