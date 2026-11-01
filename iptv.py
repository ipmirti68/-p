import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

source_urls = {
    "ATV": "https://www.atv.com.tr/canli-yayin",
    "KANAL D": "https://www.kanald.com.tr/canli-yayin",
    "SHOW TV": "https://www.showtv.com.tr/canli-yayin",
    "STAR TV": "https://www.startv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "KANAL 7": "https://www.kanal7.com/canli-izle",
    "TV8": "https://www.tv8.com.tr/canli-yayin",
}

# senin bulduğun taze token - parçalı yazdım satır taşmasın diye
ATV_TAZE = (
    "https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app=d5eb593f-39d9-4b01-9cfd-4748e8332cf0"
    "&st=aHpY5uG0xx5ECKzVhbwyOA&e=1793560183&ppid=b906dadf20123957255ac543c4d7f20e"
    "&dfp_paln=[STRIPPED 67 bytes]"
    "[STRIPPED 1284 bytes]"
)

backup = {
    "ATV": ATV_TAZE,
    "KANAL D": "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3",
    "SHOW TV": "https://ciner.daioncdn.net/showtv/showtv.m3u8?ce=3",
    "STAR TV": "https://dogus.daioncdn.net/startv/startv.m3u8?ce=3",
    "NOW TV": "https://nowtv-live-ad.ercdn.net/nowtv/playlist.m3u8",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "TV8": "https://tv8.daioncdn.net/tv8/tv8.m3u8",
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "ATV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "STAR TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
    "TV8": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
}

def extract_m3u8(site_url):
    try:
        sess = requests.Session()
        h = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Referer": site_url,
            "Accept-Language": "tr-TR,tr;q=0.9",
        }
        r = sess.get(site_url, headers=h, timeout=20)
        txt = r.text
        extra = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', txt, re.I)
        extra += re.findall(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', txt, re.I)
        for u in extra[:8]:
            if u.startswith("//"): u = "https:" + u
            elif u.startswith("/"): u = "https://" + site_url.split("/")[2] + u
            elif not u.startswith("http"): continue
            try:
                r2 = sess.get(u, headers=h, timeout=10)
                txt += "\n" + r2.text
            except: pass
        cands = re.findall(r'https://[^\s\'"<>\\]+\.m3u8[^\s\'"<>\\]*', txt)
        for link in cands:
            if ".m3u8" in link:
                return link.replace("\\/", "/")
    except Exception as e:
        print(f"Hata {site_url}: {e}")
    return None

epg_header = "#EXTM3U"
old_blocks = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            first = content.splitlines()[0] if content else "#EXTM3U"
            if "#EXTM3U" in first: epg_header = first.strip()
            parts = content.split("#EXTINF")
            for p in parts[1:]:
                block = "#EXTINF" + p.strip()
                if YENI_GRUP in block: continue
                if "http" in block: old_blocks.append(block)
    except: pass

print(f"Eski korunan blok: {len(old_blocks)}")

new_ul = {"TRT 1": backup["TRT 1"]}

for name, url in source_urls.items():
    print(f"Deniyor {name}")
    fresh = extract_m3u8(url)
    if fresh and ".m3u8" in fresh:
        # ATV için token'lı mı kontrol et
        if name == "ATV" and "?ce=" in fresh:
            new_ul[name] = fresh
            print(f"  -> TAZE ATV")
        elif name != "ATV":
            new_ul[name] = fresh
            print(f"  -> TAZE {name}")
        else:
            new_ul[name] = backup[name]
            print(f"  -> YEDEK ATV")
    else:
        new_ul[name] = backup[name]
        print(f"  -> YEDEK {name}")

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        m3u8 = new_ul.get(name, backup.get(name))
        logo = logos.get(name, "")
        ref = f"https://www.{name.lower().replace(' ','')}.com.tr/"
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'#EXTVLCOPT:http-referrer={ref}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{m3u8}\n\n')
    for b in old_blocks:
        out.write(b + "\n\n")

print("Bitti - ULUSAL oluştu")
