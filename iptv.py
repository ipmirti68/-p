import os, requests, re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

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

# TRT1 SABIT
final_links = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
}

def get_atv():
    try:
        # ATV kendi sitesi - webtv API
        r = requests.get("https://www.atv.com.tr/canli-yayin", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.atv.com.tr/"}, timeout=15)
        # icinde cdnvideo var
        m = re.findall(r'https://[^"\']+atv[^"\']+\.m3u8[^"\']*', r.text)
        if m:
            return m[0].replace("\\/", "/")
        # yedek api
        r2 = requests.get("https://www.atv.com.tr/webtv/live", headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        m2 = re.findall(r'https://[^"\']+\.m3u8[^"\']*', r2.text)
        if m2:
            return m2[0].replace("\\/", "/")
    except Exception as e:
        print(f"ATV hata: {e}")
    return "https://atv-live.cdnvideo.com.tr/atv/atv.m3u8"

def get_star():
    try:
        # STAR TV Dogus Grubu
        r = requests.get("https://www.startv.com.tr/canli-yayin", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.startv.com.tr/"}, timeout=15)
        m = re.findall(r'https://[^"\']+startv[^"\']+\.m3u8[^"\']*', r.text, re.IGNORECASE)
        if m:
            return m[0].replace("\\/", "/")
        # Dogus Live api
        r2 = requests.get("https://dogus-live.ercdn.net/startv/startv.m3u8", headers={"User-Agent":"Mozilla/5.0"}, timeout=10, allow_redirects=True)
        if r2.status_code == 200 and "#EXTM3U" in r2.text:
            return "https://dogus-live.ercdn.net/startv/startv.m3u8"
    except Exception as e:
        print(f"STAR hata: {e}")
    return "https://dogus-live.daioncdn.net/startv/startv.m3u8"

def get_tv8():
    try:
        # TV8 kendi sitesi
        r = requests.get("https://www.tv8.com.tr/canli-yayin", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.tv8.com.tr/"}, timeout=15)
        m = re.findall(r'https://[^"\']+tv8[^"\']+\.m3u8[^"\']*', r.text, re.IGNORECASE)
        if m:
            return m[0].replace("\\/", "/")
    except Exception as e:
        print(f"TV8 hata: {e}")
    return "https://tv8-live.ercdn.net/tv8/tv8.m3u8"

def get_others(name, url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0","Referer":url}, timeout=15)
        m = re.findall(r'https://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', r.text)
        if m:
            # o kanala ait olani sec
            for link in m:
                if name.lower().replace(" ","") in link.lower() or "ciner" in link.lower() or "daion" in link.lower():
                    return link.replace("\\/", "/")
            return m[0].replace("\\/", "/")
    except:
        pass
    backups = {
        "KANAL D": "https://ciner-live.ercdn.net/kanald/kanald.m3u8",
        "SHOW TV": "https://ciner-live.ercdn.net/showtv/showtv.m3u8",
        "NOW TV": "https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8",
        "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    }
    return backups.get(name)

print("ATV cekiliyor kendi sitesinden...")
final_links["ATV"] = get_atv()
print(f"ATV: {final_links['ATV']}")

print("STAR TV cekiliyor kendi sitesinden...")
final_links["STAR TV"] = get_star()
print(f"STAR: {final_links['STAR TV']}")

print("TV8 cekiliyor kendi sitesinden...")
final_links["TV8"] = get_tv8()
print(f"TV8: {final_links['TV8']}")

print("Digerleri cekiliyor...")
final_links["KANAL D"] = get_others("KANAL D", "https://www.kanald.com.tr/canli-yayin")
final_links["SHOW TV"] = get_others("SHOW TV", "https://www.showtv.com.tr/canli-yayin")
final_links["NOW TV"] = get_others("NOW TV", "https://www.nowtv.com.tr/canli-yayin")
final_links["KANAL 7"] = get_others("KANAL 7", "https://www.kanal7.com/canli-izle")

print(f"Yeni ULUSAL toplam: {len(final_links)}")

# Eski diger kategorileri koru
old_blocks = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
            for part in data.split("#EXTINF")[1:]:
                if "ULUSAL" not in part and "📺" not in part:
                    if "http" in part:
                        old_blocks.append("#EXTINF" + part.strip())
    except:
        pass

# Yaz - GARANTI OLUSUR
with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = final_links.get(name)
        if not url:
            continue
        logo = logos.get(name,"")
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        # Referer sart
        refs = {
            "ATV":"https://www.atv.com.tr/",
            "KANAL D":"https://www.kanald.com.tr/",
            "SHOW TV":"https://www.showtv.com.tr/",
            "STAR TV":"https://www.startv.com.tr/",
            "NOW TV":"https://www.nowtv.com.tr/",
            "KANAL 7":"https://www.kanal7.com/",
            "TV8":"https://www.tv8.com.tr/",
            "TRT 1":"https://www.trt1.com.tr/",
        }
        out.write(f'#EXTVLCOPT:http-referrer={refs.get(name,"https://www.google.com/")}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{url}\n\n')
    for b in old_blocks:
        out.write(b + "\n\n")

print("Bitti mirti68.m3u olustu")
print(f"Boyut
