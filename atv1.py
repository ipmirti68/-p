# MIRTI68 - ATV Canli - atv1.py - GRUP ALTINA EKLE, TEKRAR EKLEME
import requests
import time
import re
import os

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆  ULUSALᴴᴰ ⭕"
AD = "ATVᴴᴰ⭕"
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

def grup_al(s):
    m = re.search(r'group-title="([^"]*)"', s)
    if m:
        return m.group(1)
    return ""

def ad_al(s):
    if "," in s:
        return s.rsplit(",", 1)[-1].strip()
    return ""

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

    # 1. Zaten ATVᴴᴰ var mi? Varsa sadece onun linkini yenile, yeni ekleme
    hedef_idx = -1
    for idx, s in enumerate(satirlar):
        if s.startswith("#EXTINF:") and grup_al(s) == GROUP and ad_al(s) == AD:
            hedef_idx = idx
            break

    if hedef_idx != -1:
        print("[BULUNDU] ATVᴴᴰ zaten bu grupta, ayni yer guncelleniyor")
        yeni = []
        i = 0
        while i < len(satirlar):
            s = satirlar[i]
            if i == hedef_idx:
                yeni.append(s)
                yeni.append('#EXTVLCOPT:http-referer=https://www.atv.com.tr/')
                yeni.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36')
                yeni.append(link)
                # Eski link + eski VLCOPT satirlarini atla
                j = i + 1
                while j < len(satirlar) and (satirlar[j].strip().startswith("http") or satirlar[j].strip().startswith("#EXTVLCOPT")):
                    j = j + 1
                i = j
                continue
            yeni.append(s)
            i = i + 1
        with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(yeni) + "\n")
        print("[KAYDEDILDI] Ayni yer guncellendi, tekrar eklenmedi")
        return

    # 2. Yoksa: Bu grubun en son kanalini bul, onun altina ekle
    son_grup_idx = -1
    son_grup_bitisi = -1
    for idx, s in enumerate(satirlar):
        if s.startswith("#EXTINF:") and grup_al(s) == GROUP:
            # Bu kaydin bittigi yeri bul (bir sonraki EXTINF'e kadar)
            bitis = idx + 1
            while bitis < len(satirlar) and not satirlar[bitis].startswith("#EXTINF:"):
                bitis = bitis + 1
            son_grup_idx = idx
            son_grup_bitisi = bitis

    ek = []
    ek.append('#EXTINF:-1 tvg-name="' + AD + '" tvg-logo="" group-title="' + GROUP + '",' + AD)
    ek.append('#EXTVLCOPT:http-referer=https://www.atv.com.tr/')
    ek.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36')
    ek.append(link)

    if son_grup_bitisi != -1:
        print("[EKLENDI] Grubun altina eklendi: " + GROUP + " -> " + AD)
        yeni = satirlar[:son_grup_bitisi] + ek + satirlar[son_grup_bitisi:]
    else:
        # Bu grup hic yoksa en sona ekle, en basa degil
        print("[BILGI] Grup bulunamadi, en sona ekleniyor")
        yeni = satirlar + ek

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(yeni) + "\n")
    print("[KAYDEDILDI] " + OUTPUT_FILE)

if __name__ == "__main__":
    main()
