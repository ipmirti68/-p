import requests
import re
import sys
import urllib3
import warnings
import os

# --- YAPILANDIRMA ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
}

OUTPUT_FILENAME = "mirti68.m3u"
STATIC_LOGO = "https://i.imgur.com/71TSn0Q.jpeg"
GROUP = "🟩◆  beIN SPORTS 🖥"

# Ana sayfa yonlendirme zinciri (alan adi her ay degisebiliyor)
START_URL = "https://url24.link/AtomSporTV"
# Zincir kirilirsa son bilinen ana makine
FALLBACK_BASE = "https://www.atomsportv519.top"
# API adresi ana sayfadan dinamik okunur; okunamazsa son bilinen adres
FALLBACK_API = "https://teletv15.top/load/yayinlink.php"

# Kanal adlari sitesiden gelir; bilinen id'ler icin daha duzgun gosterim
PRETTY_NAMES = {
    "bein-sports-1": "beIN SPORTS 1 - Atom ⭕",
    "bein-sports-2": "beIN SPORTS 2 - Atom ⭕",
    "bein-sports-3": "beIN SPORTS 3 - Atom ⭕",
    "bein-sports-4": "beIN SPORTS 4 - Atom ⭕",
    "bein-sports-5": "beIN SPORTS 5 - Atom ⭕",
    "bein-sports-max-1": "beIN SPORTS Max 1 - Atom ⭕",
    "bein-sports-max-2": "beIN SPORTS Max 2 - Atom ⭕",
}

FALLBACK_IDS = list(PRETTY_NAMES.keys())

# channels.php okunamazsa son bilinen kanal id'leri
FALLBACK_IDS = list(PRETTY_NAMES.keys())


def discover_base_domain():
    """url24.link zincirinden guncel ana makineyi bulur."""
    headers = HEADERS.copy()
    headers['Referer'] = 'https://url24.link/'
    url = START_URL
    try:
        for _ in range(3):  # en fazla 3 yonlendirme
            r = requests.get(url, headers=headers, allow_redirects=False, timeout=10)
            loc = r.headers.get('location')
            if not loc:
                break
            url = loc if loc.startswith('http') else f"https://url24.link{loc}"
        if url.startswith('http'):
            base = url.rstrip('/')
            # son atlamada '/' ile bitti ise (orn. ...v519.top/) kullan
            print(f"✅ Ana makine: {base}")
            return base
    except Exception as e:
        print(f"⚠️  Alan adi zinciri okunamadi: {e}")
    print(f"➡️  Son bilinen ana makine kullaniliyor: {FALLBACK_BASE}")
    return FALLBACK_BASE


def discover_api(base_domain):
    """Ana sayfadaki load/*.php adreslerinden API origin'ini bulur.

    yayinlink.php ana sayfada gecmez, o yuzden once origin (orn. teletv15.top)
    bulunur ayni origin'deki yayinlink.php kullanilir.
    """
    try:
        r = requests.get(f"{base_domain}/", headers=HEADERS, timeout=10)
        urls = re.findall(r'https?://[^"\'\s\\]+?/load/[a-z0-9_]+\.php', r.text, re.I)
        if urls:
            m = re.match(r'(https?://[^/]+)', urls[0])
            if m:
                api = f"{m.group(1)}/load/yayinlink.php"
                try:
                    chk = requests.get(f"{api}?id=bein-sports-1", headers=HEADERS, timeout=10)
                    if chk.status_code == 200 and 'deismackanal' in chk.text:
                        print(f"✅ Yayin API: {api}")
                        return api
                    print(f"⚠️  {api} yanit vermedi (HTTP {chk.status_code})")
                except Exception as e:
                    print(f"⚠️  API dogrulanamadi: {e}")
    except Exception as e:
        print(f"⚠️  API adresi okunamadi: {e}")
    print(f"➡️  Son bilinen API kullaniliyor: {FALLBACK_API}")
    return FALLBACK_API


def discover_channels(api_url):

    print("\nSADECE BEIN SPORTS KANALLARI ARANIYOR")

    m = re.match(r'(https?://[^/]+)', api_url)
    origin = m.group(1) if m else ""

    channels = []
    seen = set()

    try:
        r = requests.get(
            f"{origin}/load/channels.php",
            headers=HEADERS,
            timeout=10
        )
        r.raise_for_status()

        ids = re.findall(
            r'href=["\']matches\?id=([^"\']+)',
            r.text,
            re.I
        )

        for cid in ids:
            cid = cid.strip()

            if cid not in PRETTY_NAMES:
                continue

            if cid in seen:
                continue

            seen.add(cid)
            channels.append((cid, PRETTY_NAMES[cid]))

    except Exception as e:
        print("KANAL LISTESI OKUNAMADI:", e)

    if not channels:
        print("YEDEK BEIN SPORTS LISTESI KULLANILIYOR")

        channels = [
            (cid, PRETTY_NAMES[cid])
            for cid in FALLBACK_IDS
        ]

    print("BEIN SPORTS KANAL SAYISI:", len(channels))

    return channels
    


def get_stream(api_url, cid):
    """yayinlink.php -> JSON {deismackanal: m3u8}"""
    try:
        r = requests.get(f"{api_url}?id={cid}", headers=HEADERS, timeout=12)
        link = ""
        try:
            link = (r.json().get("deismackanal") or "").strip()
        except Exception:
            m = re.search(r'"deismackanal"\s*:\s*"(.*?)"', r.text)
            if m:
                link = m.group(1).replace('\\/', '/').strip()
        if link and "m3u8" in link:
            return link.replace('\\', '')
    except Exception:
        pass
    return ""


def main():
    print("--- 📡 Atom Spor Taranıyor ---")
    base_domain = discover_base_domain()
    api_url = discover_api(base_domain)
    channels = discover_channels(api_url)

    entries = []
    seen_links = set()
    for cid, name in channels:
        link = get_stream(api_url, cid)
        if not link:
            print(f"  ❌ {name} ({cid}): yayin yok")
            continue
        # Ayni yayin iki ayri ad ile gelirse (site yanlis esleme yapabiliyor)
        # ilk gecen ad kalir: yanlis etiketli kanal listeye girmesin.
        if link in seen_links:
            print(f"  ⏭️  {name} ({cid}): ayni yayin zaten var, atlandi")
            continue
        seen_links.add(link)
        entries.append(
            f'#EXTINF:-1 tvg-logo="{STATIC_LOGO}" group-title="{GROUP}", {name}\n{link}'
        )
        print(f"  ✅ {name}")

    # Guvenlik: hic kanal yoksa dosyayi bosaltma! Mevcut liste korunur,
    # workflow hata verir ve boylece eski liste silinmez.
    if not entries:
        print("\n❌ HIC KANAL YOK - atom.m3u DEGISTIRILMEYOR (mevcut liste korunuyor)")
        sys.exit(1)
    def m3u_grup_guncelle(yeni_kayitlar):
        dosya = OUTPUT_FILENAME
        gecici = dosya + ".tmp"
        yedek = dosya + ".bak"

    if not yeni_kayitlar:
        print("HATA: Yeni kayıt yok. Mevcut liste korunuyor.")
        return False

    eski_satirlar = []

    if os.path.exists(dosya):
        with open(dosya, "r", encoding="utf-8") as f:
            eski_satirlar = f.read().splitlines()

    # Mevcut dosyayı yedekle
    if eski_satirlar and not os.path.exists(yedek):
        with open(yedek, "w", encoding="utf-8") as f:
            f.write("\n".join(eski_satirlar) + "\n")

    korunan = []
    i = 0

    while i < len(eski_satirlar):
        satir = eski_satirlar[i]

        if satir.startswith("#EXTINF:") and f'group-title="{GROUP}"' in satir:
            i += 1
            if i < len(eski_satirlar):
                i += 1
            continue

        korunan.append(satir)
        i += 1

    # Başlık yoksa ekle
    if not korunan or korunan[0].strip() != "#EXTM3U":
        korunan.insert(0, "#EXTM3U")

    # Yalnızca hedef grubu ekle
    son_icerik = korunan + yeni_kayitlar

    with open(gecici, "w", encoding="utf-8") as f:
        f.write("\n".join(son_icerik) + "\n")

    os.replace(gecici, dosya)

    print("Güncelleme tamamlandı.")
    print("Diğer gruplar korundu.")
    print("Yedek:", yedek)

    return True
    
    print(f"\n✅ İŞLEM TAMAMLANDI!")
    print(f"💾 Dosya Adı: {OUTPUT_FILENAME}")
    print(f"📝 Toplam Kanal: {len(entries)}")
    print(f"📍 Kayıt Yeri: {os.path.abspath(OUTPUT_FILENAME)}")


if __name__ == "__main__":
    main()
