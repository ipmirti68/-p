import os
import re
import requests
import base64

MASTER_FILE = "mirti68.m3u"
GROUP = "📺 ULUSAL"
MARKER = "# MIRTI68_ULUSAL_AUTO"


source_urls = {
    "ATV 🔴": "https://www.atv.com.tr/canli-yayin",
    "KANAL D 🔴": "https://www.kanald.com.tr/canli-yayin",
    "SHOW 🔴": "https://www.showtv.com.tr/canli-yayin",
    "STAR 🔴": "https://www.startv.com.tr/canli-yayin",
    "TV8 🔴": "https://www.tv8.com.tr/canli-yayin",
    "NOW 🔴": "https://www.nowtv.com.tr/canli-yayin",
    "KANAL 7 7 🔴": "https://www.kanal7.com/canli-izle",
    "TV360 🔴": "https://www.tv360.com.tr/canli-yayin",
}

LOGO_URLS = {
    "ATV 🔴": "https://medya.dsmart.com.tr/uploads/atv_1d00e30f_7d773106a0.png",
    "KANAL D 🔴": "https://medya.dsmart.com.tr/uploads/kanal_d_4a0f0323_791e93c4c3.png",
    "SHOW 🔴": "https://medya.dsmart.com.tr/uploads/show_tv_f0716ef6_a0c29b9846.png",
    "STAR 🔴": "https://medya.dsmart.com.tr/uploads/star_abfb3b0c_04b167fd8f.png",
    "TV8 🔴": "https://medya.dsmart.com.tr/uploads/tv8_e29e33cb_383f1b8a2e.png",
    "NOW 🔴": "https://medya.dsmart.com.tr/uploads/now_new_d291a389_a022fe1395.png",
    "Kanal 7 🔴": "https://medya.dsmart.com.tr/uploads/kanal_7_23db4968_45f09094d0.png",
    "360 🔴": "https://medya.dsmart.com.tr/uploads/360_e47c08db_e35a7f2424.png",
}

TVG_IDS = {
    "ATV 🔴": "ATV.tr",
    "KANAL D 🔴": "KanalD.tr",
    "SHOW 🔴": "ShowTV.tr",
    "STAR🔴": "StarTV.tr",
    "TV8 🔴": "TV8.tr",
    "NOW 🔴": "NowTV.tr",
    "Kanal 7 🔴": "Kanal7.tr",
    "TV360 🔴": "360TV.tr",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"}
session = requests.Session()
session.headers.update(HEADERS)

# Logo cache - her seferinde indirmemek icin
LOGO_CACHE = {}

def get_logo_as_base64(name):
    if name in LOGO_CACHE:
        return LOGO_CACHE[name]
    
    url = LOGO_URLS.get(name, "")
    if not url:
        return ""
    
    try:
        print(f"   Logo indiriliyor: {name}")
        r = session.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 100:
            b64 = base64.b64encode(r.content).decode('utf-8')
            # TiviMate data URI destekliyor
            data_uri = f"data:image/png;base64,{b64}"
            LOGO_CACHE[name] = data_uri
            return data_uri
    except Exception as e:
        print(f"   Logo hatasi {name}: {e}")
    
    # Olmazsa normal URL'e dus
    LOGO_CACHE[name] = url
    return url

def extract_m3u8(page_url):
    try:
        r = session.get(page_url, timeout=25)
        html = r.text.replace("\\/", "/")
        matches = re.findall(r'https?://[^\s\'"<>]+?\.m3u8[^\s\'"<>]*', html, re.IGNORECASE)
        for link in matches:
            link = link.rstrip("\\),;\"'")
            if "ads" in link.lower(): continue
            if ".m3u8" in link.lower():
                return link
    except: pass
    return None

def remove_own_records(lines):
    result = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == MARKER:
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith("#EXTINF:"):
                    i += 1
                    while i < len(lines):
                        cur = lines[i].strip()
                        if cur and not cur.startswith("#"):
                            i += 1; break
                        if cur.startswith("#EXTINF:"): break
                        i += 1
                    break
                if lines[i].strip() == MARKER: break
                i += 1
            continue
        result.append(lines[i]); i += 1
    return result

def main():
    print("MIRTI68 ULUSAL - BASE64 LOGO SURUMU")
    if not os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n')

    with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
        old_lines = f.readlines()
    
    output = remove_own_records(old_lines)

    # Basligi duzelt
    has_m3u = False
    for idx, l in enumerate(output):
        if l.strip().startswith("#EXTM3U"):
            has_m3u = True
            if "x-tvg-url" not in l:
                output[idx] = f'#EXTM3U x-tvg-url="{EPG_URL}"\n'
            break
    if not has_m3u:
        output.insert(0, f'#EXTM3U x-tvg-url="{EPG_URL}"\n')

    new_channels = []
    for name, page_url in source_urls.items():
        print(f"\n[+] {name}")
        stream = extract_m3u8(page_url)
        if not stream:
            print(f"[X] Bulunamadi")
            continue
        
        # LOGO ARTIK BASE64
        logo_data = get_logo_as_base64(name)
        tvg_id = TVG_IDS.get(name, "")
        tvg_name = name.replace(" 🔴","").strip()

        extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{logo_data}" group-title="{GROUP}",{name}\n'
        new_channels.extend([MARKER + "\n", extinf, stream + "\n"])
        print(f"[OK] {tvg_id}")

    if new_channels:
        if output and not output[-1].endswith("\n"): output[-1] += "\n"
        output.append("\n")
        output.extend(new_channels)

    with open(MASTER_FILE + ".tmp", "w", encoding="utf-8") as f:
        f.writelines(output)
    os.replace(MASTER_FILE + ".tmp", MASTER_FILE)
    print("\nBITTI - Dosya: mirti68.m3u - Logo: BASE64 GOMULU")

if __name__ == "__main__":
    main()
