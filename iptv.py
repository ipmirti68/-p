from playwright.sync_api import sync_playwright
import re, os, shutil

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆ ULUSAL 📺"
EPG_URL = "https://raw.githubusercontent.com/iptv-org/epg/master/guides/turkey.epg.xml"
CDN1 = "daioncdn.net"
CDN2 = "ercdn.net"
ATV_FALLBACK = "https://rnttwmjcin.turknet.ercdn.net/lcpmvefbyo/atv/atv_720p.m3u8"

CHANNELS = {
    "TRT1": {"display": "TRT 1 ⭕", "epg": "TRT 1", "epg_id": "TRT1", "page": "https://www.trt1.com.tr/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt", "marker": "# MIRTI68_TRT1_AUTO", "fallback": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
    " ATV": {"display": "ATV ⭕", "epg": " ATV", "epg_id": " ATV", "page": "https://www.atv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": " 【entity-atv¦canonical_name=ATV】", "marker": "# MIRTI68_ATV_AUTO", "fallback": ATV_FALLBACK},
    "SHOW": {"display": "SHOW ⭕", "epg": "Show TV", "epg_id": "ShowTV", "page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png", "keyword": "showtv", "marker": "# MIRTI68_SHOWTV_AUTO"},
    "KANALD": {"display": "KANAL D ⭕", "epg": "Kanal D", "epg_id": "KanalD", "page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald", "marker": "# MIRTI68_KANALD_AUTO"},
    "STAR": {"display": "STAR ⭕", "epg": "Star TV", "epg_id": "StarTV", "page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv", "marker": "# MIRTI68_STARTV_AUTO"},
    "NOW": {"display": "NOW ⭕", "epg": "NOW", "epg_id": "NOW", "page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv", "marker": "# MIRTI68_NOWTV_AUTO"},
    "KANAL7": {"display": " KANAL 7 ⭕", "epg": " KANAL 7", "epg_id": "Kanal7", "page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7", "marker": "# MIRTI68_KANAL7_AUTO"},
    " TV8": {"display": " TV8 ⭕", "epg": " TV8", "epg_id": " TV8", "page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": " 【entity-tv8¦canonical_name=TV8】", "marker": "# MIRTI68_TV8_AUTO"},
}

def clean_keyword(kw, fallback_kw):
    return kw.strip().lower()

def is_bad_url(u):
    if not u:
        return True
    low = u.lower()
    if "avrupa" in low:
        return True
    if "securevideotoken" in low:
        return True
    if "secure?" in low:
        return True
    if ".m3u8" not in low:
        return True
    return False

def get_link(page_url, keyword, channel_key=""):
    keyword = clean_keyword(keyword, channel_key.lower())
    found = []
    def is_bad(u):
        low = u.lower()
        if "avrupa" in low or "securevideotoken" in low or "secure?" in low:
            return True
        return False
    def on_dialog(d):
        urls = re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        for u in urls:
            if not is_bad(u) and u not in found:
                found.append(u)
        try:
            d.accept()
        except:
            pass
    def on_response(resp):
        url = resp.url
        if ".m3u8" in url and not is_bad(url):
            if keyword in url.lower() or CDN1 in url or CDN2 in url:
                if url not in found:
                    print("  [NETWORK] " + url[:120] + "...")
                    found.append(url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        page.on("response", on_response)
        print("[*] " + keyword + " -> " + page_url + " aciliyor...")
        try:
            page.goto(page_url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(7000)
            try:
                content = page.content()
                m = re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', content)
                for u in m:
                    if is_bad(u):
                        continue
                    if keyword in u.lower() or CDN1 in u or CDN2 in u:
                        if u not in found:
                            print("  [SOURCE] " + u[:120] + "...")
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
            print("  [!] hata: " + str(e))
        browser.close()
    for u in found:
        low = u.lower()
        if "/atv/atv" in low and "avrupa" not in low:
            return u
    for u in found:
        if keyword in u.lower() and CDN1 in u:
            return u
    for u in found:
        if CDN1 in u or CDN2 in u:
            return u
    return found[0] if found else None

def parse_blocks(content):
    lines = content.splitlines()
    blocks = []
    i = 0
    if lines and lines[0].startswith("#EXTM3U"):
        i = 1
    cur_marker = None
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# MIRTI68_"):
            cur_marker = line
            i += 1
            continue
        if line.startswith("#EXTINF"):
            url = ""
            if i + 1 < len(lines):
                nxt = lines[i+1].strip()
                if nxt and not nxt.startswith("#"):
                    url = nxt
                    i += 1
            blocks.append({"marker": cur_marker, "extinf": line, "url": url})
            cur_marker = None
            i += 1
            continue
        i += 1
    return blocks

def build_block(info, url):
    extinf = '#EXTINF:-1 tvg-id="' + info["epg_id"].strip() + '" tvg-name="' + info["epg"].strip() + '" tvg-logo="' + info["logo"] + '" group-title="' + GROUP + '",' + info["display"].strip()
    return {"marker": info["marker"], "extinf": extinf, "url": url}

def get_tail(block):
    if "," in block["extinf"]:
        return block["extinf"].split(",", 1)[-1].strip().upper()
    return ""

def main():
    print("MIRTI68 ULUSAL - 8 KANAL - GUVENLI SURUM")
    if os.path.exists(OUTPUT_FILE):
        if not os.path.exists(OUTPUT_FILE + ".bak"):
            shutil.copy(OUTPUT_FILE, OUTPUT_FILE + ".bak")
            print("[YEDEK] ilk kez alindi")
        else:
            print("[YEDEK] eski .bak korundu, ezilmedi")
        with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            old_content = f.read()
        old_blocks = parse_blocks(old_content)
        print("[OKUNDU] Eski dosyada " + str(len(old_blocks)) + " kanal var")
    else:
        old_blocks = []
        print("[!] " + OUTPUT_FILE + " yok")

    old_by_marker = {}
    for b in old_blocks:
        if b["marker"]:
            old_by_marker[b["marker"]] = b

    old_atv_block = old_by_marker.get("# MIRTI68_ATV_AUTO")
    if not old_atv_block:
        for b in old_blocks:
            tail = get_tail(b)
            if tail.startswith("ATV"):
                old_atv_block = b
                break

    new_blocks_map = {}
    ok = 0
    for name, info in CHANNELS.items():
        m = info["marker"]
        if name == "ATV":
            old_block = old_atv_block
        else:
            old_block = old_by_marker.get(m)
        old_url = old_block["url"] if old_block else ""

        url = None
        source = ""
        if info.get("page"):
            url = get_link(info["page"], info["keyword"], channel_key=name)
            if url and is_bad_url(url):
                print("[!] " + name + " kotu link geldi, seninki korunuyor")
                url = None
            elif url:
                source = "CEKILDI"

        if name == "ATV" and old_url and not is_bad_url(old_url) and source != "CEKILDI":
            url = old_url
            source = "ESKI-SENINKI-KORUNDU"
            print("[+] ATV eski linkin korunuyor: " + url[:100] + "...")
        elif not url and old_url and not is_bad_url(old_url):
            url = old_url
            source = "ESKI-KORUNDU"

        if not url and info.get("fallback"):
            if not old_url:
                url = info["fallback"]
                source = "YEDEK"
                print("[!] " + name + " eski yok, yedek kullaniliyor")

        if not url:
            print("[!] " + name + " ALINAMADI")
            if old_block:
                new_blocks_map[m] = old_block
            continue

        print("[+] " + name + " " + source + ": " + url[:100] + "...")
        if source in ("ESKI-SENINKI-KORUNDU", "ESKI-KORUNDU") and old_block:
            new_blocks_map[m] = old_block
        else:
            new_blocks_map[m] = build_block(info, url)
        ok += 1

    final_blocks = []
    used_markers = set()

    for name, info in CHANNELS.items():
        m = info["marker"]
        if m in new_blocks_map:
            final_blocks.append(new_blocks_map[m])
            used_markers.add(m)
        else:
            for b in old_blocks:
                if b["marker"] == m:
                    final_blocks.append(b)
                    used_markers.add(m)
                    break

    for b in old_blocks:
        if b["marker"] in used_markers:
            continue
        tail = get_tail(b)
        if tail.startswith("ATV"):
            continue
        if not b["marker"] and (",ATV" in b["extinf"] or ", ATV" in b["extinf"]):
            if "# MIRTI68_ATV_AUTO" in [x["marker"] for x in final_blocks if x["marker"]]:
                continue
        final_blocks.append(b)
        if b["marker"]:
            used_markers.add(b["marker"])

    has_atv = False
    for b in final_blocks:
        if get_tail(b).startswith("ATV"):
            has_atv = True
            break
    if not has_atv:
        print("[GARANTI] Listede ATV yoktu, yedek ATV eklendi!")
        atv_info = CHANNELS["ATV"]
        if len(final_blocks) >= 1:
            final_blocks.insert(1, build_block(atv_info, ATV_FALLBACK))
        else:
            final_blocks.append(build_block(atv_info, ATV_FALLBACK))

    out = '#EXTM3U url-tvg="' + EPG_URL + '"\n\n'
    for b in final_blocks:
        if b["marker"]:
            out += b["marker"] + "\n"
        out += b["extinf"] + "\n"
        out += b["url"] + "\n\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out.strip() + "\n")

    print("[TAMAMLANDI] " + str(ok) + "/8 guncellendi - Toplam " + str(len(final_blocks)) + " kanal korundu")

if __name__ == "__main__":
    main()
