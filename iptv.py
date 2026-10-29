import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

backup = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
    "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
    "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
}

def get_m3u8(site_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": site_url}
        r = requests.get(site_url, headers=headers, timeout=10)
        links = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        if links:
            return links[0].replace("\\/", "/")
    except:
        return None
    return None

epg_header = "#EXTM3U"
old_blocks = []
atv_star_tv8_blocks = []

if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first_line = content.splitlines()[0] if content else "#EXTM3U"
        if "url-tvg" in first_line.lower() or "tvg-url" in first_line.lower():
            epg_header = first_line.strip()
        parts = content.split("#EXTINF")
        for p in parts[1:]:
            block = "#EXTINF" + p.strip()
            if "ULUSAL" in block or "📺" in block:
                continue
            upper = block.upper()
            if ",ATV" in upper or upper.endswith(",ATV"):
                atv_star_tv8_blocks.append(block)
                continue
            if "STAR TV" in upper:
                atv_star_tv8_blocks.append(block)
                continue
            if ",TV8" in upper or upper.endswith(",TV8"):
                atv_star_tv8_blocks.append(block)
                continue
            if "http" in block:
                old_blocks.append(block)

final_new = {}
for name, site in [
    ("TRT 1", "https://tv-trt1.medya.trt.com.tr/master.m3u8"),
    ("KANAL D", "https://www.kanald.com.tr/canli-yayin"),
    ("SHOW TV", "https://www.showtv.com.tr/canli-yayin"),
    ("NOW TV", "https://www.nowtv.com.tr/canli-yayin"),
    ("KANAL 7", "https://www.kanal7.com/canli-izle")
]:
    if site.endswith(".m3u8"):
        final_new[name] = site
    else:
        link = get_m3u8(site)
        if link:
            final_new[name] = link
        else:
            final_new[name] = backup[name]

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for name in ["TRT 1", "KANAL D", "SHOW TV", "NOW TV", "KANAL 7"]:
        url = final_new.get(name)
        logo = logos.get(name, "")
        out.write('#EXTINF:-1 tvg-logo="' + logo + '" group-title="' + YENI_GRUP + '",' + name + '\n')
        out.write(url + '\n\n')
    for b in atv_star_tv8_blocks:
        out.write(b + '\n\n')
    for b in old_blocks:
        out.write(b + '\n\n')

print("Bitti")
