from playwright.sync_api import sync_playwright
import re, os

OUTPUT_FILE = "mirti68.m3u"
GROUP = "ULUSAL"
EPG_URL = "https://raw.githubusercontent.com/iptv-org/epg/master/guides/turkey.epg.xml"

CHANNELS =
    "TRT1": {"display": "TRT 1 ⭕", "epg": "TRT 1", "epg_id": "TRT1", "page": "https://www.trt1.com.tr/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt", "marker": "# MIRTI68_TRT1_AUTO", "fallback": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
    "ATV": {"display": "ATV ⭕", "epg": "ATV", "epg_id": "ATV", "page": "https://www.atv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": "atv", "marker": "# MIRTI68_ATV_AUTO", "fallback": "https://rnttwmjcin.turknet.ercdn.net/lcpmvefbyo/atv/atv_720p.m3u8"},
    "SHOW": {"display": "SHOW ⭕", "epg": "Show TV", "epg_id": "ShowTV", "page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png", "keyword": "showtv", "marker": "# MIRTI68_SHOWTV_AUTO"},
    "KANALD": {"display": "KANAL D ⭕", "epg": "Kanal D", "epg_id": "KanalD", "page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald", "marker": "# MIRTI68_KANALD_AUTO"},
    "STAR": {"display": "STAR ⭕", "epg": "Star TV", "epg_id": "StarTV", "page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv", "marker": "# MIRTI68_STARTV_AUTO"},
    "NOW": {"display": "NOW ⭕", "epg": "NOW", "epg_id": "NOW", "page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv", "marker": "# MIRTI68_NOWTV_AUTO"},
    "KANAL7": {"display": "KANAL 7 ⭕", "epg": "Kanal 7", "epg_id": "Kanal7", "page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7", "marker": "# MIRTI68_KANAL7_AUTO"},
    "TV8": {"display": "TV8 ⭕", "epg": "TV8", "epg_id": "TV8", "page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8", "marker": "# MIRTI68_TV8_AUTO"},
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

def update_one_channel(info, new_url):
    marker = info["marker"]
    new_block=f"""{marker}
#EXTINF:-1 tvg-id="{info['epg_id']}" tvg-name="{info['epg']}" tvg-logo="{info['logo']}" group-title="{GROUP}",{info['display']}
{new_url}
"""
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE,"w",encoding="utf-8").write(f'#EXTM3U url-tvg="{EPG_URL}"\n\n{new_block}')
        return
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        old=f.read()
    if "url-tvg" not in old.splitlines()[0] if old.splitlines() else True:
        old = old.replace("#EXTM3U", f'#EXTM3U url-tvg="{EPG_URL}"', 1) if old.startswith("#EXTM3U") else f'#EXTM3U url-tvg="{EPG_URL}"\n' + old
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
        marker = block.split
