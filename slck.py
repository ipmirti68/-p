"""SLCK (SelcukSportsHD) - FIXED"""
import re, sys, requests, urllib3, warnings, os
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

# Domain listesi - biri patlarsa digerini dene
POSSIBLE_DOMAINS = [
    "https://www.selcuksportshd14e17ba2ad.xyz/",
    "https://www.selcuksportshd15e17ba2ad.xyz/",
    "https://selcuksportshd14e17ba2ad.xyz/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/152.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

STREAM_DOMAIN = "dga1op10s1u3lea.308aae467c3965.click"
STREAM_REFERER = "https://main.uxsyplayer6859599e6c.click/"
OUTPUT_FILENAME = "mirti68.m3u"
BEIN_GROUP = "🖥beINSPORTS"
LOGO = "https://i.ibb.co/mrrwmxDX/p-Lhc-Pi-Bn-400x400.jpg"

PRETTY_NAMES = {
    "selcukbeinsports1": "beIN SPORTS 1 Selcuk 1\U0001f534",
    "selcukbeinsports2": "beIN SPORTS 2 Selcuk 1\U0001f534",
    "selcukbeinsports3": "beIN SPORTS 3 Selcuk 1\U0001f534",
    "selcukbeinsports4": "beIN SPORTS 4 Selcuk 1\U0001f534",
    "selcukbeinsports5": "beIN SPORTS 5 Selcuk 1\U0001f534",
    "selcukbeinsportsmax1": "beIN SPORTS MAX 1 Selcuk 1\U0001f534",
    "selcukbeinsportsmax2": "beIN SPORTS MAX 2 Selcuk 1\U0001f534",
    "selcukbeinsportshaber": "beIN SPORTS Haber Selcuk 1\U0001f534",
    "selcukbeinconnect1": "beIN Con 1 Selcuk 1\U0001f534",
    "beinsports1": "beIN SPORTS 1 Selcuk 1\U0001f534",
    "beinsports2": "beIN SPORTS 2 Selcuk 1\U0001f534",
    "beinsports3": "beIN SPORTS 3 Selcuk 1\U0001f534",
    "beinsports4": "beIN SPORTS 4 Selcuk 1\U0001f534",
    "beinsports5": "beIN SPORTS 5 Selcuk 1\U0001f534",
}

def pretty(cid: str) -> str:
    c = cid.strip().lower().replace("-","").replace("_","")
    for k,v in PRETTY_NAMES.items():
        if k in c or c in k:
            return v
    return PRETTY_NAMES.get(cid.lower(), cid.replace("selcuk","").title())

def fetch_home():
    for url in POSSIBLE_DOMAINS:
        try:
            print(f"Deniyor: {url}")
            r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if r.status_code==200 and "id=" in r.text:
                print(f"OK: {url}")
                r.encoding = r.apparent_encoding or "utf-8"
                return r.text
        except Exception as e:
            print(f"Fail {url}: {e}")
    # son carek - direkt domaini dene
    raise Exception("Tum Selcuk domainleri fail")

def parse_bein_ids(html):
    # daha genis regex - id=... her seyi al
    ids = re.findall(r"index\.php\?id=([A-Za-z0-9_\-\s]+)", html)
    # temizle
    ids = [i.strip() for i in ids if i.strip()]
    # bein icerenleri filtrele - ama PRETTY_NAMES zorunlu degil
    out=[]
    seen=set()
    for cid in ids:
        low=cid.lower()
        if "bein" not in low and "connect" not in low:
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(cid)
    print(f"Raw ids: {ids[:20]}")
    print(f"Filtered beIN: {out}")
    return out

def append_to_mirti68(new_entries):
    if not new_entries:
        print("\u274c Yeni kayit bulunamadi - bos oldugu icin dosyaya yazilmiyor, eski liste korunuyor")
        return
    try:
        from m3u_manager import update_group
    except ImportError:
        print("\u274c m3u_manager.py bulunamadi! Manuel yaziliyor")
        # fallback - dosyayi silmeden ekle
        try:
            with open(OUTPUT_FILENAME,"r",encoding="utf-8",errors="ignore") as f:
                old=f.read()
            block="\n".join([f'#EXTINF:-1 tvg-logo="{LOGO}" group-title="{BEIN_GROUP}",{n}\n#EXTVLCOPT:http-referrer={STREAM_REFERER}\n{u}' for n,u in new_entries])
            # eski beIN bloklarini silme, sadece ekle (koruma)
            with open(OUTPUT_FILENAME,"a",encoding="utf-8") as f:
                f.write(old.rstrip()+"\n\n"+block+"\n")
            print(f"\u2705 {len(new_entries)} kanal eklendi (fallback)")
        except Exception as e:
            print(f"\u274c Fallback hata: {e}")
        return

    formatted=[]
    for name,url in new_entries:
        entry=f'#EXTINF:-1 tvg-logo="{LOGO}" group-title="{BEIN_GROUP}",{name}\n#EXTVLCOPT:http-referrer={STREAM_REFERER}\n{url}'
        formatted.append(entry)
    try:
        update_group(BEIN_GROUP, formatted, filename=OUTPUT_FILENAME)
        print(f"\u2705 {len(formatted)} beIN kanali {BEIN_GROUP} grubunda guncellendi.")
    except Exception as e:
        print(f"\u274c M3U guncelleme hatasi: {e}")

def main():
    print("--- \U0001f3df SLCK (SelcukSportsHD) beIN taraniyor ---")
    try:
        html=fetch_home()
    except Exception as e:
        print(f"\u274c Ana sayfa erisilemiyor: {e}")
        return
    ids=parse_bein_ids(html)
    print(f"\u2705 {len(ids)} beIN kanali bulundu")
    if not ids:
        print("\u274c beIN KANAL YOK - dosya korunacak, silinmeyecek")
        return
    entries=[]
    for cid in ids:
        url=f"https://{STREAM_DOMAIN}/live/{cid}/playlist.m3u8"
        entries.append((pretty(cid),url))
        print(f"  \u2705 {pretty(cid)} -> {cid}")
    entries.sort(key=lambda x: x[0].lower())
    append_to_mirti68(entries)

if __name__=="__main__":
    main()
