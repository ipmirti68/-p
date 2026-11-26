# MIRTI68 - ATV Canli Token Tazeleme
# OUTPUT: mirti68.m3u
# GROUP: 🟨◆  ULUSALᴴᴰ ⭕
import requests, time, re, os, shutil

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆  ULUSALᴴᴰ ⭕"
SITE_ID = "0fe2a405-8afa-4238-b429-e5f96aec3a5c"
LIVE_ID = "00000000-0000-0000-0000-000000000000"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.atv.com.tr/",
    "Origin": "https://www.atv.com.tr",
}

def atv_link_al():
    url = f"https://videojs.tmgrup.com.tr/getvideo/{SITE_ID}/{LIVE_ID}"
    r = requests.get(url, headers=headers, timeout=20)
    print("PLAYER:", r.text[:500])
    ham = ""
    try:
        data = r.json()
        for k in ["VideoUrl", "videoUrl", "Url", "url", "Source", "source", "StreamUrl", "VideoURL"]:
            if k in data and data[k]:
                ham = data[k]
                break
        if not ham:
            txt = str(data)
            m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', txt)
            if m: ham = m.group(0)
    except Exception as e:
        print("JSON hatasi:", e)
        m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', r.text)
        if m: ham = m.group(0)
    if not ham:
        print("[HATA] Ham link bulunamadi")
        return ""
    print("HAM:", ham)
    ts = int(time.time())
    token_url = f"https://securevideotoken.tmgrup.com.tr/webtv/secure?{ts}&url={ham}"
    r2 = requests.get(token_url, headers=headers, timeout=20)
    print("TOKEN:", r2.text[:500])
    try:
        d2 = r2.json()
        tokenli = d2.get("Url") or d2.get("url") or d2.get("VideoUrl") or d2.get("VideoURL") or ""
        if not tokenli:
            m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', r2.text)
            tokenli = m.group(0) if m else ""
    except:
        m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', r2.text)
        tokenli = m.group(0) if m else r2.text.strip()
    return tokenli.strip()

def main():
    if not os.path.exists(OUTPUT_FILE):
        print(f"[HATA] {OUTPUT_FILE} yok")
        return
    link = atv_link_al()
    if not link or ".m3u8" not in link:
        print("[HATA] Tokenli link alinamadi, dosya degistirilmedi")
        return
    print("[OK] Yeni ATV linki:", link[:120])

    with open(OUTPUT_FILE, encoding="utf-8") as f:
        satirlar = f.read().splitlines()

    yeni_satirlar = []
    degisti = False
    bulundu = False
    i = 0
    while i < len(satirlar):
        s = satirlar[i]
        # ATV satirini bul - grup ne olursa olsun ATV ise al
        is_atv = s.startswith("#EXTINF:") and (',ATV' in s or 'tvg-name="ATV"' in s or ',ATV ' in s or s.strip().endswith(",ATV"))
        if is_atv:
            bulundu = True
            # group-title'i istedigin gruba zorla
            if 'group-title="' in s:
                s = re.sub(r'group-title="[^"]*"', f'group-title="{GROUP}"', s)
            else:
                s = s.replace("#EXTINF:", f'#EXTINF: group-title="{GROUP}"', 1)
            yeni_satirlar.append(s)
            if i + 1 < len(satirlar) and satirlar[i+1].strip().startswith("http"):
                yeni_satirlar.append(link)
                print(f"[DEGISTI] ATV linki yenilendi + grup -> {GROUP}")
                degisti = True
                i += 2
                continue
            i += 1
            continue
        yeni_satirlar.append(s)
        i += 1

    if not bulundu:
        print(f"[BILGI] Listede ATV yok, {GROUP} grubuna ekleniyor")
        ek = [f'#EXTINF:-1 tvg-name="ATV" tvg-logo="" group-title="{GROUP}",ATV', link]
        if yeni_satirlar and yeni_satirlar[0].startswith("#EXTM3U"):
            yeni_satirlar = [yeni_satirlar[0]] + ek + yeni_satirlar[1:]
        else:
            yeni_satirlar = ["#EXTM3U"] + ek + yeni_satirlar
        degisti = True

    try: shutil.copy2(OUTPUT_FILE, OUTPUT_FILE + ".bak")
    except: pass
    with open(
