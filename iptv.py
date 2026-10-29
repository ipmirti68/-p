import os
output_file = "mirti68.m3u"

# YENI GRUP ADI
YENI_GRUP = "📺 ULUSAL 🔗"

guncellenecek = {
    "TRT 1": ("https://tv-trt1.medya.trt.com.tr/master.m3u8","https://www.trt1.com.tr/","TRT.1.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png"),
    "ATV": ("https://atv-live.cdnvideo.com.tr/atv/atv.m3u8","https://www.atv.com.tr/","ATV.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png"),
    "KANAL D": ("https://ciner-live.ercdn.net/kanald/kanald.m3u8","https://www.kanald.com.tr/","Kanal.D.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png"),
    "SHOW TV": ("https://ciner-live.ercdn.net/showtv/showtv.m3u8","https://www.showtv.com.tr/","Show.TV.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png"),
    "STAR TV": ("https://dogus-live.ercdn.net/startv/startv.m3u8","https://www.startv.com.tr/","Star.TV.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png"),
    "NOW TV": ("https://nowtv-live.ercdn.net/nowtv/nowtv.m3u8","https://www.nowtv.com.tr/","NOW.TV.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png"),
    "KANAL 7": ("https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8","https://www.kanal7.com/","Kanal.7.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png"),
    "TV8": ("https://tv8-live.ercdn.net/tv8/tv8.m3u8","https://www.tv8.com.tr/","TV8.hd","https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png"),
}

lines=[]
if os.path.exists(output_file):
    with open(output_file,"r",encoding="utf-8",errors="ignore") as f:
        lines=f.readlines()

old={}
i=0
while i < len(lines):
    if lines[i].startswith("#EXTINF"):
        ext=lines[i].strip()
        j=i+1
        while j < len(lines) and lines[j].startswith("#EXTVLCOPT"):
            j+=1
        url = lines[j].strip() if j < len(lines) else ""
        name = ext.split(",")[-1].strip().upper()
        if name not in [k.upper() for k in guncellenecek.keys()]:
            old[name]=[ext,url]
        i=j+1
    else:
        i+=1

with open(output_file,"w",encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    # YENI KANALLAR - ISTEDIGIN GRUP ADIYLA
    for name,(url,ref,tvgid,logo) in guncellenecek.items():
        out.write(f'#EXTINF:-1 tvg-id="{tvgid}" tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'#EXTVLCOPT:http-referrer={ref}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{url}\n\n')
    # ESKI LISTE
    for ext,url in old.values():
        out.write(ext+"\n"+url+"\n\n")

print(f"Bitti. Yeni grup: {YENI_GRUP} - Toplam {len(old)+len(guncellenecek)} kanal")
