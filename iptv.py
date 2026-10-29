import os
import requests
import re

# Senin istediğin formatın bilgileri
channel_info = {
    "trt1": {"tvg_id": "TRT.1.hd", "tvg_name": "TRT 1.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "group": "📺 ULUSAL.", "name": "TRT 1"},
    "trtspor": {"tvg_id": "TRT.Spor.hd", "tvg_name": "TRT Spor.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trtspor.png", "group": "📺 SPOR.", "name": "TRT Spor"},
    "trthaber": {"tvg_id": "TRT.Haber.hd", "tvg_name": "TRT Haber.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trthaber.png", "group": "📺 HABER.", "name": "TRT Haber"},
    "trtsporyildiz": {"tvg_id": "TRT.Spor.Yildiz.hd", "tvg_name": "TRT Spor Yildiz.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trtsporyildiz.png", "group": "📺 SPOR.", "name": "TRT Spor Yildiz"},
    "atv": {"tvg_id": "ATV.hd", "tvg_name": "ATV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "group": "📺 ULUSAL.", "name": "ATV"},
    "showtv": {"tvg_id": "Show.TV.hd", "tvg_name": "Show TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png", "group": "📺 ULUSAL.", "name": "Show TV"},
    "startv": {"tvg_id": "Star.TV.hd", "tvg_name": "Star TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "group": "📺 ULUSAL.", "name": "Star TV"},
    "kanald": {"tvg_id": "Kanal.D.hd", "tvg_name": "Kanal D.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "group": "📺 ULUSAL.", "name": "Kanal D"},
    "nowtv": {"tvg_id": "NOW.TV.hd", "tvg_name": "NOW TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "group": "📺 ULUSAL.", "name": "NOW TV"},
    "tv8": {"tvg_id": "TV8.hd", "tvg_name": "TV8.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "group": "📺 ULUSAL.", "name": "TV8"},
    "tv8bucuk": {"tvg_id": "TV8.Bucuk.hd", "tvg_name": "TV8 Bucuk.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8bucuk.png", "group": "📺 ULUSAL.", "name": "TV8 Bucuk"},
    "teve2": {"tvg_id": "Teve2.hd", "tvg_name": "Teve2.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/teve2.png", "group": "📺 ULUSAL.", "name": "Teve2"},
    "dmax": {"tvg_id": "DMAX.hd", "tvg_name": "DMAX.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/dmax.png", "group": "📺 ULUSAL.", "name": "DMAX"},
    "a2tv": {"tvg_id": "A2.TV.hd", "tvg_name": "A2 TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/a2tv.png", "group": "📺 ULUSAL.", "name": "A2 TV"},
    "aspor": {"tvg_id": "A.Spor.hd", "tvg_name": "A Spor.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/aspor.png", "group": "📺 SPOR.", "name": "A Spor"},
    "beyaztv": {"tvg_id": "Beyaz.TV.hd", "tvg_name": "Beyaz TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/beyaztv.png", "group": "📺 ULUSAL.", "name": "Beyaz TV"},
    "cnnturk": {"tvg_id": "CNN.Turk.hd", "tvg_name": "CNN Turk.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/cnnturk.png", "group": "📺 HABER.", "name": "CNN Turk"},
    "halktv": {"tvg_id": "Halk.TV.hd", "tvg_name": "Halk TV.tr", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/halktv.png", "group": "📺 HABER.", "name": "Halk TV"},
}

source_urls = {
    "trt1": "https://www.tabii.com/tr/watch/live/trt1?trackId=150002",
    "trtspor": "https://www.tabii.com/watch/live/trtspor?trackId=150022",
    "trthaber": "https://www.tabii.com/watch/live/trthaber?trackId=150017",
    "trtsporyildiz": "https://www.tabii.com/tr/watch/live/trtsporyildiz?trackId=150028",
    "nowtv": "https://www.nowtv.com.tr/canli-yayin",
    "showtv": "https://www.showtv.com.tr/canli-yayin",
    "startv": "https://www.startv.com.tr/canli-yayin",
    "tv8": "https://www.tv8.com.tr/canli-yayin",
    "tv8bucuk": "https://www.tv8bucuk.com/tv8-5-canli-yayin",
    "atv": "https://www.atv.com.tr/canli-yayin",
    "kanald": "https://www.kanald.com.tr/canli-yayin",
    "teve2": "https://www.teve2.com.tr/canli-yayin",
    "dmax": "https://www.dmax.com.tr/canli-izle",
    "a2tv": "https://www.atv.com.tr/a2tv/canli-yayin",
    "aspor": "https://www.aspor.com.tr/webtv/canli-yayin",
    "beyaztv": "https://www.beyaztv.com.tr/canli-yayin",
    "cnnturk": "https://www.cnnturk.com/canli-yayin",
    "halktv": "https://halktv.com.tr/canli-yayin",
}

def extract_m3u8(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=10, headers=headers)
        m = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', r.text)
        if m:
            return m[0]
    except:
        pass
    return None

# ÇIKTI DOSYASI - SENİN İSTEDİĞİN FORMAT
output_file = "mirti68.m3u"

with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")

    for name, page_url in source_urls.items():
        print(f"[+] {name}...")
        m3u8_link = extract_m3u8(page_url)
        
        # TRT için fallback senin verdiğin link
        if not m3u8_link and name == "trt1":
            m3u8_link = "https://tv-trt1.medya.trt.com.tr/master.m3u8"
        
        if m3u8_link:
            info = channel_info.get(name, {"tvg_id": f"{name}.hd", "tvg_name": f"{name}.tr", "logo": "", "group": "📺 ULUSAL.", "name": name.upper()})
            
            # SENİN İSTEDİĞİN SATIR FORMATI BURASI
            extinf = f'#EXTINF:-1 tvg-id="{info["tvg_id"]}" tvg-name="{info["tvg_name"]}" tvg-logo="{info["logo"]}" group-title="{info["group"]}",{info["name"]}\n'
            out.write(extinf)
            out.write(m3u8_link + "\n\n")
            print(f"[✓] {info['name']}")
        else:
            print(f"[X] {name} bulunamadı")

print(f"\nHAZIR! {output_file} oluşturuldu.")
