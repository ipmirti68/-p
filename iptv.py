from playwright.sync_api import sync_playwright
import re, os, codecs, shutil

OUTPUT_FILE = "ulusal.m3u"
GROUP = "🟨◆  ULUSALᴴᴰ ⭕"

# SIRALAMA: TRT1 - ATV- SHOW TV - KANAL D - Star TV - NOW - KANAL7 - TV8 - 360 - TV4 - TV2 - BEYAZ
CHANNELS = {
    "TRT 1 ⭕": {"page": "", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt-1", "marker": "# MIRTI68_TRT1_AUTO", "direct": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
    "ATV ⭕": {"page": "", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": "ATV", "marker": "# MIRTI68_ATV_AUTO", "direct": "http://80.253.255.35:8000/play/a00g"},
    "SHOW TV ⭕": {"page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png", "keyword": "showtv", "marker": "# MIRTI68_SHOWTV_AUTO"},
    "KANAL D ⭕": {"page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald", "marker": "# MIRTI68_KANALD_AUTO"},
    "Star TV  ⭕": {"page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv", "marker": "# MIRTI68_STARTV_AUTO"},
    "NOW ⭕": {"page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv", "marker": "# MIRTI68_NOWTV_AUTO"},
    "KANAL 7 ⭕": {"page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7", "marker": "# MIRTI68_KANAL7_AUTO"},
    "TV8 ⭕": {"page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8", "marker": "# MIRTI68_TV8_AUTO"},
    "360 ⭕": {"page": "https://www.tv360.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/360.png", "keyword": "360 tv", "marker": "# MIRTI68_360_AUTO"},
    "TV 4 ⭕": {"page": "https://www.tv4.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv4.png", "keyword": "tv 4", "marker": "# MIRTI68_TV4_AUTO"},
    "TV 2 ⭕": {"page": "https://www.tv2.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv2.png", "keyword": "tv2", "marker": "# MIRTI68_TV2_AUTO"},
    "BEYAZ ⭕": {"page": "https://m.beyaztv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/beyaz.png", "keyword": "beyax tv", "marker": "# MIRTI68_BEYAZ_AUTO"},
}

def get_link(page_url, keyword):
    found=[]
    def on_dialog(d):
        urls=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        if urls:
            found.extend(urls)
        try: d.accept()
        except: pass
    def on_response(resp):
        url=resp.url
        if ".m3u8" in url and (keyword in url.lower() or "daioncdn.net" in url or "ercdn.net" in url):
            if url not in found:
                print(f"  [NETWORK] {url[:120]}...")
                found.append(url)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        page.on("dialog", on_dialog)
        page.on("response", on_response)
        print(f"[*] {keyword} -> {page_url}")
        try:
            page.goto(page_url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(7000)
            try:
                content=page.content()
                m=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', content)
                for u in m:
                    if keyword in u.lower() or "daioncdn.net" in u or "ercdn.net" in u:
                        if u not in found:
                            print(f"  [SOURCE] {u[:120]}...")
                            found.append(u)
            except: pass
            for sel in ["button", ".play-button", ".vjs-big-play-button", "[class*=play]", ".atv-player", ".ciner-player"]:
                try:
                    page.click(sel, timeout=1200)
                    page.wait_for_timeout(1500)
                except: pass
            page.wait_for_timeout(8000)
        except Exception as e:
            print(f"  [!] hata: {e}")
        browser.close()
    for u in found:
        if keyword in u.lower() and "daioncdn.net" in u:
            return u
    for u in found:
        if "daioncdn.net" in u or "ercdn.net" in u:
            return u
    return found[0] if found else None

# ============ DOSYA ISLEMLERI - SILMEDEN GUNCELLE ============

def grup_bul(record_lines):
    for line in record_lines:
        if line.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', line)
            return m.group(1) if m else ""
    return ""

def dosyayi_oku():
    if not os.path.exists(OUTPUT_FILE):
        return ["#EXTM3U"], [], "utf-8", "\n", False
    raw = open(OUTPUT_FILE, "rb").read()
    bom = raw.startswith(codecs.BOM_UTF8)
    metin = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()
    ilk_extinf = next((i for i, s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik = satirlar[:ilk_extinf]  # #EXTM3U + EPG satirlari BURADA, dokunulmaz
    govde = satirlar[ilk_extinf:]
    # kayitlara bol
    records = []
    current = []
    for line in govde:
        if line.startswith("#EXTINF:") and current:
            records.append(current)
            current = []
        current.append(line)
    if current:
        records.append(current)
    return baslik, records, ("utf-8-sig" if bom else "utf-8"), newline, bom

def eski_url_bul(records, marker):
    for r in records:
        if any(marker in l for l in r):
            for l in r:
                if l.startswith("http"):
                    return l.strip()
    return None

def main():
    print("MIRTI68 ULUSAL - DIGER GRUPLARA DOKUNMADAN GUNCELLE")

    baslik, records, encoding, newline, bom = dosyayi_oku()
    print(f"[BILGI] Dosyada {len(records)} kayit var, baslik korundu: {baslik[:2]}")

    # 1. Linkleri topla
    results = {}
    for name, info in CHANNELS.items():
        if info.get("direct"):
            url = info["direct"]
            print(f"[+] {name} SABIT: {url}")
        else:
            url = get_link(info["page"], info["keyword"])
            if not url:
                url = eski_url_bul(records, info["marker"])
                if url:
                    print(f"[!] {name} ALINAMADI - eski link korundu")
                else:
                    print(f"[!] {name} ALINAMADI - atlaniyor")
                    continue
            else:
                print(f"[+] {name} OK: {url[:100]}...")
        results[name] = url

    # 2. Yeni ULUSAL kayitlarini SIRALI hazirla
    yeni_ulusal = []
    for name, info in CHANNELS.items():
        if name not in results:
            continue
        yeni_ulusal.append([
            info["marker"],
            f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{info["logo"]}" group-title="{GROUP}",{name}',
            results[name]
        ])

    # 3. Eski ULUSAL grubunu cikar, diger gruplar aynen kalsin
    digerleri = [r for r in records if grup_bul(r) != GROUP]
    # ULUSAL grubunun eski yerini bul - oraya yeni blogu koy
    # Eger ULUSAL hic yoksa, en basa koy
    ulusal_index = None
    for i, r in enumerate(records):
        if grup_bul(r) == GROUP:
            ulusal_index = i
            break

    if ulusal_index is None:
        # ULUSAL yoksa en basa ekle
        son_records = yeni_ulusal + digerleri
        print("[BILGI] ULUSAL grubu yoktu, en basa eklendi")
    else:
        # digerleri icinde ULUSAL'in oldugu pozisyonu bul
        # Basit yontem: ULUSAL en bastaysa basa, degilse digerlerinin icinde o noktaya koy
        # En guvenlisi: ULUSAL grubunu oldugu yere koy - once digerlerinde o indexe karsilik gelen yeri bul
        # Biz burada ULUSAL'i en basa koymuyoruz, eski konumunu koruyoruz:
        # records icinde ULUSAL'dan once kac tane diger grup kaydi var?
        onceki_diger_sayisi = sum(1 for r in records[:ulusal_index] if grup_bul(r) != GROUP)
        son_records = digerleri[:onceki_diger_sayisi] + yeni_ulusal + digerleri[onceki_diger_sayisi:]
        print(f"[BILGI] ULUSAL grubu eski yerine ({onceki_diger_sayisi}. kayit sonrasi) yazildi")

    # 4. Yedek al + yaz
    if os.path.exists(OUTPUT_FILE):
        shutil.copy2(OUTPUT_FILE, OUTPUT_FILE + ".bak")
    sonuc = list(baslik)
    for record in son_records:
        sonuc.extend(record)
    yeni_metin = newline.join(sonuc) + newline
    with open(OUTPUT_FILE, "w", encoding=encoding, newline="") as f:
        f.write(yeni_metin)

    print(f"[TAMAMLANDI] ULUSAL: {len(yeni_ulusal)} / Diger gruplar: {len(digerleri)} kayit korundu - EPG silinmedi")

if __name__ == "__main__":
    main()
