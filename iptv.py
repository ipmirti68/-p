from playwright.sync_api import sync_playwright
import re, os, json

OUTPUT_FILE = "mirti68.m3u"

CHANNELS = {
    "ATV": {
        "page": "https://www.atv.com.tr/canli-yayin",
        "marker": "# MIRTI68_ATV_AUTO",
        "name": "ATV",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "atv"
    },
    "KANAL D": {
        "page": "https://www.kanald.com.tr/canli",
        "marker": "# MIRTI68_KANALD_AUTO",
        "name": "KANAL D",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "kanald"
    },
    "SHOW TV": {
        "page": "https://www.showtv.com.tr/canli-yayin",
        "marker": "# MIRTI68_SHOWTV_AUTO",
        "name": "SHOW TV",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "showtv"
    },
    "STAR TV": {
        "page": "https://www.startv.com.tr/canli-yayin",
        "marker": "# MIRTI68_STARTV_AUTO",
        "name": "STAR TV",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/startv.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "startv"
    },
    "TV8": {
        "page": "https://www.tv8.com.tr/canli",
        "marker": "# MIRTI68_TV8_AUTO",
        "name": "TV8",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "tv8"
    },
    "KANAL 7": {
        "page": "https://www.kanal7.com/canli-yayin",
        "marker": "# MIRTI68_KANAL7_AUTO",
        "name": "KANAL 7",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "kanal7"
    },
    "NOW TV": {
        "page": "https://www.nowtv.com.tr/canli-yayin",
        "marker": "# MIRTI68_NOWTV_AUTO",
        "name": "NOW TV",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/now.png",
        "group": "📺 ULUSAL",
        "direct": None,
        "keyword": "nowtv"
    },
    "TRT 1": {
        "page": None,
        "marker": "# MIRTI68_TRT1_AUTO",
        "name": "TRT 1",
        "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
        "group": "📺 ULUSAL",
        "direct": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
        "keyword": "trt1"
    },
}

def get_link(page_url, keyword):
    if not page_url:
        return None
    found=[]
    def on_dialog(d):
        urls=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        if urls:
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
                    found.append(url)
            # body icinde m3u8 ara
            if keyword.lower() in url.lower() or "player" in url.lower() or "live" in url.lower() or "token" in url.lower():
                try:
                    text=resp.text()
                    if ".m3u8" in text:
                        m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', text)
                        for u in m:
                            if u not in found:
                                found.append(u)
                except:
                    pass
        except:
            pass
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
            page.on("dialog", on_dialog)
            page.on("response", on_response)
            print(f"[*] {page_url} aciliyor...")
            page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            try:
                html=page.content()
                m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', html)
                for u in m:
                    if u not in found:
                        found.append(u)
            except:
                pass
            for sel in ["button", ".play-button", ".vjs-big-play-button", "[class*=play]"]:
                try:
                    page.click(sel, timeout=1000)
                    page.wait_for_timeout(2000)
                except:
                    pass
            page.wait_for_timeout(5000)
            browser.close()
    except Exception as e:
        print(f"  [!] {page_url} hata: {e}")
    
    # en iyi secim
    best=None
    for u in found:
        if "live.ercdn.net" in u and "1080p" in u and keyword.lower() in u.lower():
            return u
    for u in found:
        if "live.ercdn.net" in u and keyword.lower() in u.lower():
            return u
    for u in found:
        if "daioncdn.net" in u and keyword.lower() in u.lower() and len(u)>100:
            if best is None or len(u)>len(best):
                best=u
    if best:
        return best
    for u in found:
        if keyword.lower() in u.lower() and ".m3u8" in u:
            return u
    return found[0] if found else None

def update_one_channel(old_content, ch_data, new_url):
    marker=ch_data["marker"]
    name=ch_data["name"]
    logo=ch_data["logo"]
    group=ch_data["group"]
    new_block=f"""{marker}
#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}
{new_url}
"""
    if marker in old_content:
        before=old_content.split(marker)[0]
        after_part=old_content.split(marker,1)[1]
        m=re.search(r'\n# MIRTI68_', after_part)
        after=after_part[m.start():] if m else ""
        return before.rstrip()+"\n"+new_block+after.lstrip()
    else:
        return old_content.rstrip()+"\n\n"+new_block

def main():
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE,"w",encoding="utf-8").write("#EXTM3U\n")
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as f:
        content=f.read()
    print(f"BASLANGIC boyut: {len(content)} - {OUTPUT_FILE}")
    updated=0
    for key, data in CHANNELS.items():
        print(f"\n--- {key} ---")
        url=None
        if data["direct"]:
            url=data["direct"]
            print(f"[+] {key} DIRECT: {url}")
        else:
            url=get_link(data["page"], data["keyword"])
            if url:
                print(f"[+] {key} OK: {url[:150]}...")
            else:
                print(f"[!] {key} ALINAMADI - eski korunuyor")
                continue
        new_content=update_one_channel(content, data, url)
        if len(new_content) > len(content) * 0.5:
            content=new_content
            updated+=1
            print(f"[OK] {key} guncellendi")
        else:
            print(f"[!] {key} boyut kuculecek, atlandi")
    # sadece boyut kuculmediyse yaz
    if len(content) > 80000:
        with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
            f.write(content)
        print(f"\n[TAMAMLANDI] {updated}/{len(CHANNELS)} kanal - Final: {len(content)} byte")
    else:
        print(f"[!] Final boyut cok kucuk {len(content)}, yazilmadi - dosya korunuyor")

if __name__=="__main__":
    main()
