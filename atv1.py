# MIRTI68 - ATV Canli - atv1.py - ASLA SILMEZ
import requests
import time
import re
import os

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆  ULUSALᴴᴰ ⭕"
SITE_ID = "0fe2a405-8afa-4238-b429-e5f96aec3a5c"
LIVE_ID = "00000000-0000-0000-0000-000000000000"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.atv.com.tr/",
    "Origin": "https://www.atv.com.tr",
}

def find_m3u8(text):
    m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', text or "")
    if m:
        return m.group(0)
    return ""

def atv_link_al():
    url = "https://videojs.tmgrup.com.tr/getvideo/" + SITE_ID + "/" + LIVE_ID
    r = requests.get(url, headers=HEADERS, timeout=20)
    ham = ""
    try:
        data = r.json()
        for k in ["VideoUrl", "videoUrl", "Url", "url", "Source", "source", "StreamUrl", "VideoURL"]:
            if k in data and data[k]:
                ham = str(data[k])
                break
        if not ham:
            ham = find_m3u8(str(data))
    except Exception:
        ham = find_m3u8(r.text)
    if not ham:
        return ""
    ts = int(time.time())
    token_url = "https://securevideotoken.tmgrup.com.tr/webtv/secure?" + str(ts) + "&url=" + ham
    r2 = requests.get(token_url, headers=HEADERS, timeout=20)
    try:
        d2 = r2.json()
        tokenli = str(d2.get("Url") or d2.get("url") or d2.get("VideoUrl") or d2.get("VideoURL") or "")
        if not tokenli:
            tokenli = find_m3u8(r2.text)
    except Exception:
        tokenli = find_m3u8(r2.text)
    return tokenli.strip()

def main():
    if not os.path.exists(OUTPUT_FILE):
        print("[HATA] " + OUTPUT_FILE + " yok")
        return
    link = atv_link_al()
    if not link or ".m3u8" not in link:
        print("[HATA] Link alinamadi, dosyaya dokunulmedi")
        return
    print("[OK] Yeni link: " + link[:120])

    with open(OUTPUT_FILE, encoding="utf-8") as f:
        satirlar = f.read().splitlines()

    yeni = []
    hedef_bulundu = False

    for idx, s in enumerate(satirlar):
        # Sadece hedef grup + hedef ad ise linki degistir
        if s.startswith("#EXTINF:") and ('group-title="' + GROUP + '"') in s and s.strip().endswith(",ATV"):
            hedef_bulundu = True
            yeni.append(s)
            yeni.append('#EXTVLCOPT:http-referer=https://www.atv.com.tr/')
            yeni.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36')
            yeni.append(link)
            print("[GUNCELLENDI] Kendi grubundaki ATV")
            continue
        # Hedef ATV'nin eski link satiri ise atla, YENI link zaten yazildi
        # Ama bunu sadece bir onceki satir hedef ATV ise yap
        if idx > 0 and satirlar[idx-1].startswith("#EXTINF:") and ('group-title="' + GROUP + '"') in satirlar[idx-1] and satirlar[idx-1].strip().endswith(",ATV"):
            if s.strip().startswith("http") or s.strip().startswith("#EXTVLCOPT"):
                continue
        # Diger her sey: aynen koru, SILME YOK
        yeni.append(s)

    if not hedef_bulundu:
        print("[BILGI] Bu grupta ATV yok, sadece bu gruba 1 tane ekleniyor")
        ek1 = '#EXTINF:-1 tvg-name="ATV" tvg-logo="" group-title="' + GROUP + '",ATV'
        ek = [ek1, '#EXTVLCOPT:http-referer=https://www.atv.com.tr/', '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36', link]
        if yeni and yeni[0].startswith("#EXTM3U"):
            yeni = [yeni[0]] + ek + yeni[1:]
        else:
            yeni = ["#EXTM3U"] + ek + yeni

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(yeni) + "\n")
    print("[KAYDEDILDI] " + OUTPUT_FILE + " - hicbir satir silinmedi")

if __name__ == "__main__":
    main()
