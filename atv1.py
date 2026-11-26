# MIRTI68 - ATV Canli - atv1.py
# OUTPUT: mirti68.m3u
# GROUP: 🟨◆  ULUSALᴴᴰ ⭕
import requests
import time
import re
import os
import shutil

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
    print("PLAYER:", r.text[:500])
    ham = ""
    try:
        data = r.json()
        for k in ["VideoUrl", "videoUrl", "Url", "url", "Source", "source", "StreamUrl", "VideoURL"]:
            if k in data and data[k]:
                ham = str(data[k])
                break
        if not ham:
            ham = find_m3u8(str(data))
    except Exception as e:
        print("JSON hatasi:", e)
        ham = find_m3u8(r.text)
    if not ham:
        print("[HATA] Ham link bulunamadi")
        return ""
    print("HAM:", ham)
    ts = int(time.time())
    token_url = "https://securevideotoken.tmgrup.com.tr/webtv/secure?" + str(ts) + "&url=" + ham
    r2 = requests.get(token_url, headers=HEADERS, timeout=20)
    print("TOKEN:", r2.text[:500])
    tokenli = ""
    try:
        d2 = r2.json()
        tokenli = str(d2.get("Url") or d2.get("url") or d2.get("VideoUrl") or d2.get("VideoURL") or "")
        if not tokenli:
            tokenli = find_m3u8(r2.text)
    except Exception:
        tokenli = find_m3u8(r2.text)
        if not tokenli:
            tokenli = r2.text.strip()
    return tokenli.strip()

def main():
    if not os.path.exists(OUTPUT_FILE):
        print("[HATA] " + OUTPUT_FILE + " yok")
        return
    link = atv_link_al()
    if not link or ".m3u8" not in link:
        print("[HATA] Tokenli link alinamadi, dosya degistirilmedi")
        return
    print("[OK] Yeni ATV linki: " + link[:120])
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        satirlar = f.read().splitlines()
    yeni = []
    bulundu = False
    i = 0
    while i < len(satirlar):
        s = satirlar[i]
        is_atv = False
        if s.startswith("#EXTINF:"):
            if ",ATV" in s or 'tvg-name="ATV"' in s or s.strip().endswith(",ATV"):
                is_atv = True
        if is_atv:
            bulundu = True
            if 'group-title="' in s:
                s = re.sub(r'group-title="[^"]*"', 'group-title="' + GROUP + '"', s)
            else:
                s = s.replace("#EXTINF:", '#EXTINF: group-title="' + GROUP + '"', 1)
            yeni.append(s)
            if i + 1 < len(satirlar) and satirlar[i + 1].strip().startswith("http"):
                yeni.append(link)
                print("[DEGISTI] ATV linki yenilendi, grup: " + GROUP)
                i = i + 2
                continue
            i = i + 1
            continue
        yeni.append(s)
        i = i + 1
    if not bulundu:
        print("[BILGI] Listede ATV yok, ekleniyor: " + GROUP)
        ek1 = '#EXTINF:-1 tvg-name="ATV" tvg-logo="" group-title="' + GROUP + '",ATV'
        ek = [ek1, link]
        if yeni and yeni[0].startswith("#EXTM3U"):
            yeni = [yeni[0]] + ek + yeni[1:]
        else:
            yeni = ["#EXTM3U"] + ek + yeni
    try:
        shutil.copy2(OUTPUT_FILE, OUTPUT_FILE + ".bak")
    except Exception:
        pass
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(yeni) + "\n")
    print("[KAYDEDILDI] " + OUTPUT_FILE)

if __name__ == "__main__":
    main()
