# ==================================================
# MIRTI68 - TEK AKTARICI - KOMPLE DÜZELTİLMİŞ
# HATALI URL ATLA - ÇALIŞANLARA DEVAM ET
# HATALI URL'LERİ EN SONDA LİSTELE
# ==================================================

import re
import os
import shutil
import urllib.request
import urllib.error
import socket

HEDEF_DOSYA = "mirti68.m3u"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

TIMEOUT = 30

AKTARIMLAR = [
    {
        # SİNEMA - power-sinema.m3u - istediğin gruplar aynen kalsın
        "kaynak_url": "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u",
        # Birden fazla kaynak grup - bunlardan biri ise al
        "kaynak_gruplar": [
            "IMDb Top Rated",
            "YERLI FILM",
            "KEMAL SUNAL",
            "KORKU",
            "WESTERN",
            "YeniEklenenler",
            "2026",
            "2025",
            "2023 2024",
            "2021 2022",
            "2019 2020",
            "2017 2018",
            "2015 2016",
            "2013 2014",
            "2011 2012",
            "2001 2010",
        ],
        "kaynak_grup": "",
        "aranacak": "",
        # hedef_grup boş = kaynak grup adı aynen kalsın, değiştirme
        "hedef_grup": "",
        "hedef_logo": "",
        "ek_kod": "⭕",
        "grup_onek": False,
        "sinema_modu": True,
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/Adnan4161/TvDizi/refs/heads/main/Tv%20Dizi.m3u",
        "kaynak_grup": "",
        "aranacak": "",
        "hedef_grup": "🟪◆ GÜNCEL DİZİLER ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
        # YENİ: Kaynak grup adını kanal adının önüne yaz
        # Örnek: Kaynak grup "Yalı Çapkını" ise -> "Yalı Çapkını - 1.Bölüm ⭕"
        "grup_onek": True,
    },


      {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/livetv/dc73a3a52d0d5be4ba926d7b40a759fb9d5777a3/tv247tr.m3u",
        "kaynak_grup": "Spor-Avva",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Avva",
    },

    
    {
        "kaynak_url": "https://raw.githubusercontent.com/smtv62/atomspor/refs/heads/main/atom.m3u",
        "kaynak_grup": "Atom-Panel",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Atom",
    },
  {
        "kaynak_url": "https://raw.githubusercontent.com/smtv62/smtv/refs/heads/main/turkce.m3u",
        "kaynak_grup": "",
        "aranacak": "trt1, atv, show, kanal d, star, now, kanal7. tv8",
        "hedef_grup": "🟨◆ ULUSAL ᴴᴰ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },
    {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | ULUSAL",
        "aranacak": "trt1, atv, show, kanal d, star, now, kanal7. tv8",
        "hedef_grup": "🟨◆ ULUSAL ᴴᴰ⁺ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/mzabidin80/OTT_Navigator_Indonesia_Korea_China_Movies.m3u/refs/heads/main/OTT_Navigator_V2_Indonesia_Korea_China_Movies_Knowledge.m3u",
        "kaynak_grup": "",
        "aranacak": "Korea",
        "hedef_grup": "🟨◆ YABANCI 🇰🇷⭕",
        "hedef_logo": "https://upload.wikimedia.org/wikipedia/commons/0/09/Flag_of_South_Korea.svg?utm_source=tr.wikipedia.org&utm_campaign=index&utm_content=original",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/mehmetey03/METV/refs/heads/main/mahsun.m3u",
        "kaynak_grup": "",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

      
    {
        "kaynak_url": "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "Diziler | Prison Break | Prison Break",
        "aranacak": "",
        "hedef_grup": "🟪◆ DİZİLER - PRİSON BREAK ⭕",
        "hedef_logo": "",
        "ek_kod": "",
    },

    {
        "kaynak_url": "http://190502.tomtv.eu:80/get.php?username=MustafaozdemR7808&password=z189b8mv2r&type=m3u_plus&output=ts",
        "kaynak_grup": "SONVIZYON FILMLER",
        "aranacak": "",
        "hedef_grup": "🟪◆ GÜNCEL FİLİMLER ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

  

    {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | 7/24 DIZI",
        "aranacak": "",
        "hedef_grup": "🟪◆  7/24 DİZİ 📺⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },



    {
        "kaynak_url": "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "Yerel / 🔴 SPOR",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "0️⃣⭕",
    },

    {
        "kaynak_url": "http://31.43.191.142:8880/get.php?username=191703089055131&password=01703089055686&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | SPORT",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "1️⃣⭕",
    },

    {
        "kaynak_url": "http://ruzgarplayer.site:8080/get.php?username=KH6Rn39q4WpL&password=bnzSVts6Lner&type=m3u_plus&output=tsrd=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "⫸TR SUPER LİG 1⫷",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "2️⃣⭕",
    },

    {
        "kaynak_url": "http://190502.tomtv.eu/get.php?username=GokmenS947&password=5rr53m3b8c&type=m3u_plus&output=ts",
        "kaynak_grup": "TR-SPOR",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "3️⃣⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/livetv/dc73a3a52d0d5be4ba926d7b40a759fb9d5777a3/tv247tr.m3u",
        "kaynak_grup": "Spor Vavoo",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "4️⃣⭕",
    },
     
    {
        "kaynak_url": "https://ekmek82.shop/get.php?username=adnan678&password=uBjabktvQP&type=m3u_plus&output=ts",
        "kaynak_grup": "TR • BeIN SPORTS",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "5️⃣⭕",
    },

     {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | TABii",
        "aranacak": "",
        "hedef_grup": "🟪◆  TABİİ DİZİLERİ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },
     
]

# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {
        "ı": "i", "İ": "i", "i": "i",
        "ö": "o", "Ö": "o",
        "ü": "u", "Ü": "u",
        "ç": "c", "Ç": "c",
        "ğ": "g", "Ğ": "g",
        "ş": "s", "Ş": "s",
    }
    s = "".join(cevir.get(c, c) for c in s)
    s = s.replace("|", " ").replace("-", " ").replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ==================================================
# SİNEMA ÖZEL - EKSİK GÖNDERİLEN KISIM
# Grup adı değişmeli: "IMDb Top Rated" -> "🟪◆ FILM - IMDb Top Rated ⭕"
# + tvg-type="movie" + EXCLUDED filtresi + URL düzeltme
# ==================================================
SINEMA_WANTED_RAW = [
    "IMDb Top Rated", "YERLI FILM", "KEMAL SUNAL", "KORKU", "WESTERN",
    "YeniEklenenler", "2026", "2025", "2023 2024", "2021 2022",
    "2019 2020", "2017 2018", "2015 2016", "2013 2014",
    "2011 2012", "2001 2010",
]
def norm_sinema(s):
    s = (s or "").lower()
    s = re.sub(r'[^a-z0-9çğıöşü]+', '', s)
    return s
SINEMA_WANTED = {norm_sinema(x): x for x in SINEMA_WANTED_RAW}
SINEMA_EXCLUDED = [
    "adam sandler", "clint eastwood", "sylvester stallone", "jackie chan",
    "nicolas cage", "steven seagal", "jason statham",
    "seri", "dizi", "series", "sezon", "season", "episode",
    "bölüm", "bolum", "s01e", "s02e", "s03e",
]
def sinema_excluded(text):
    t = " " + re.sub(r'[^a-z0-9çğıöşü]+', ' ', (text or "").lower()) + " "
    compact = (text or "").lower().replace(" ", "")
    for w in SINEMA_EXCLUDED:
        if w in ("s01e", "s02e", "s03e"):
            if w in compact:
                return True
        else:
            nw = re.sub(r'[^a-z0-9çğıöşü]+', ' ', w.lower()).strip()
            if f" {nw} " in t:
                return True
    return False
def sinema_fix_url(url):
    url = (url or "").strip().replace("?.mp4", "").replace("?ext=.mp4", "")
    if "vixolity.com/vs/" in url and url.endswith(".mp4"):
        url = url[:-4]
    return url

def grup_bul(rec):
    for l in rec:
        if l.startswith("#EXTINF:"):
            m = re.search(r'group-title="([^"]*)"', l)
            return m.group(1) if m else ""
    return ""

def kanal_adi(rec):
    for l in rec:
        if l.startswith("#EXTINF:"):
            return l.split(",", 1)[-1].strip()
    return ""

def temiz_isim(ad):
    ad = (ad or "").lower().strip()
    for son_ek in ["⭕ atom", "⭕", "atom"]:
        if ad.endswith(son_ek):
            ad = ad[:-len(son_ek)].strip()
    ad = re.split(r'\s*-\s*\d+\.?\s*bölüm', ad)[0]
    ad = re.split(r'\s*-\s*\d+\.?\s*bolum', ad)[0]
    ad = re.split(r'\s*-\s*\d{4}-\d{2}-\d{2}', ad)[0]
    return ad.strip().rstrip("-").strip()

def grup_baslangici(grup_adi):
    g = (grup_adi or "").strip()
    if not g:
        return ""
    if "◆" in g:
        idx = g.find("◆")
        return g[:idx + 1].strip()
    return g.split()[0] if g.split() else ""

def grup_eslesiyor_mu(kaynak_grup, hedef_kaynak_grup):
    if not hedef_kaynak_grup:
        return True
    n_kaynak = normalize(kaynak_grup)
    n_hedef = normalize(hedef_kaynak_grup)
    if not n_kaynak:
        return False
    return n_kaynak == n_hedef

def oku_m3u(path_or_url):
    if path_or_url.startswith("http"):
        req = urllib.request.Request(
            path_or_url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Connection": "close"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            veri = r.read()
        metin = veri.decode("utf-8-sig", errors="ignore")
    else:
        if not os.path.exists(path_or_url):
            raise FileNotFoundError(path_or_url)
        with open(path_or_url, "rb") as f:
            metin = f.read().decode("utf-8-sig", errors="ignore")
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()
    ilk = next((i for i, s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik = satirlar[:ilk]
    govde = satirlar[ilk:]
    records = []
    cur = []
    for line in govde:
        if line.startswith("#EXTINF:") and cur:
            records.append(cur)
            cur = []
        cur.append(line)
    if cur:
        records.append(cur)
    return baslik, records, newline, "utf-8"

def hedefe_uyarla(rec, cfg):
    # BOZUK SATIR DUZELTME: EXTINF'i sifirdan kur, cift tvg-name / group-title kalmasin
    yeni_rec = list(rec)
    extinf_index = next((i for i, x in enumerate(yeni_rec) if x.startswith("#EXTINF:")), None)
    if extinf_index is None:
        return yeni_rec
    extinf = yeni_rec[extinf_index]
    m_sure = re.match(r"#EXTINF:(-?\d+)", extinf)
    sure = m_sure.group(1) if m_sure else "-1"
    if "," in extinf:
        ad = extinf.rsplit(",", 1)[-1].strip()
    else:
        ad = ""
    ozellikler = {}
    for k, v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf):
        ozellikler[k] = v
    # SINEMA MODU: Grup adi degismeli - IMDb Top Rated -> 🟪◆ FILM - IMDb Top Rated ⭕
    if cfg.get("sinema_modu"):
        _g = grup_bul(rec).strip()
        _clean = SINEMA_WANTED.get(norm_sinema(_g), _g)
        _clean = re.sub(r"\s+", " ", _clean).strip()
        if "FILM" not in _clean.upper():
            _clean = f"FILM - {_clean}"
        cfg = dict(cfg)
        cfg["hedef_grup"] = f"🟪◆ {_clean} ⭕"
        cfg["_sinema_tvg_type"] = True
    # YENİ: Kaynak grup adını kanal adının önüne yaz
    if cfg.get("grup_onek"):
        kaynak_grup_adi = grup_bul(rec).strip()
        if kaynak_grup_adi and not ad.lower().startswith(kaynak_grup_adi.lower()):
            ad = f"{kaynak_grup_adi} - {ad}"
    # hedef_grup boşsa kaynak grup adını aynen koru (SİNEMA gibi)
    if cfg.get("hedef_grup"):
        ozellikler["group-title"] = cfg["hedef_grup"]
    logo = cfg.get("hedef_logo", "")
    if logo:
        ozellikler["tvg-logo"] = logo
    ek = (cfg.get("ek_kod") or "").strip()
    if ek and "=" not in ek:
        if not ad.endswith(ek) and ek not in ad:
            ad = f"{ad} {ek}"
    if "tvg-name" in ozellikler:
        ozellikler["tvg-name"] = ad
    if cfg.get("_sinema_tvg_type"):
        ozellikler["tvg-type"] = "movie"
    oz_str = " ".join(f'{k}="{v}"' for k, v in ozellikler.items())
    yeni_rec[extinf_index] = f"#EXTINF:{sure} {oz_str},{ad}"
    # SİNEMA: URL'deki ?.mp4 / ?ext=.mp4 temizle
    if cfg.get("sinema_modu"):
        for _i, _line in enumerate(yeni_rec):
            _s = _line.strip()
            if _s.startswith(("http://", "https://")):
                yeni_rec[_i] = sinema_fix_url(_s)
    return yeni_rec

def aranacak_parcala(aranacak_raw):
    s = (aranacak_raw or "").strip()
    if not s:
        return []
    s_low = s.lower()
    for ikili in ["kanal d", "kanal 7", "show tv", "star tv", "beyaz tv", "tv 8", "tv 8.5", "a2 tv", "trt 1"]:
        if ikili in s_low:
            s_low = s_low.replace(ikili, ikili.replace(" ", "_"))
    if any(x in s_low for x in [",", ";", "|", "\n"]):
        parcalar = re.split(r"[,;|\n]+", s_low)
    else:
        parcalar = s_low.split()
    out = []
    for p in parcalar:
        p = p.strip().replace("_", " ").strip()
        if p:
            out.append(normalize(p))
    return out

def kaynak_sec(kaynak_records, cfg):
    aranacak_liste = aranacak_parcala(cfg.get("aranacak", ""))
    kaynak_grup = cfg.get("kaynak_grup", "").strip()
    # YENİ: birden fazla kaynak grup (SİNEMA WANTED_RAW gibi)
    kaynak_gruplar = cfg.get("kaynak_gruplar", []) or []
    # SİNEMA: norm_sinema kullan - boşluk / - farkını yok say
    # "YeniEklenenler" == "Yeni Eklenenler" == "yeni-eklenenler"
    if cfg.get("sinema_modu"):
        kaynak_gruplar_n = [norm_sinema(g) for g in kaynak_gruplar if g.strip()]
    else:
        kaynak_gruplar_n = [normalize(g) for g in kaynak_gruplar if g.strip()]
    secilen = []
    for r in kaynak_records:
        g = grup_bul(r)
        # Tek grup varsa onu, liste varsa listeden birini kontrol et
        if kaynak_gruplar_n:
            _g_norm = norm_sinema(g) if cfg.get("sinema_modu") else normalize(g)
            if _g_norm not in kaynak_gruplar_n:
                continue
        elif kaynak_grup and not grup_eslesiyor_mu(g, kaynak_grup):
            continue
        # SİNEMA: hariç tutulanları atla (dizi/seri/bölüm/sezon vs.)
        if cfg.get("sinema_modu"):
            if sinema_excluded(g) or sinema_excluded(kanal_adi(r)):
                continue
        if aranacak_liste:
            ad_n = normalize(kanal_adi(r))
            ad_n_bosluksuz = ad_n.replace(" ", "")
            eslesti = False
            for anahtar in aranacak_liste:
                if anahtar in ad_n or anahtar.replace(" ", "") in ad_n_bosluksuz:
                    eslesti = True
                    break
            if not eslesti:
                continue
        if "bilgilendirme" in kanal_adi(r).lower():
            continue
        secilen.append(hedefe_uyarla(r, cfg))
    return secilen

def grubu_birlestir(hedef_records, secilen, hedef_grup):
    gelen = {}
    for r in secilen:
        isim = temiz_isim(kanal_adi(r))
        if isim:
            gelen[isim] = r
    yeni_kayitlar = []
    gorulen = set()
    son = None
    for r in hedef_records:
        if grup_bul(r) != hedef_grup:
            yeni_kayitlar.append(r)
            continue
        isim = temiz_isim(kanal_adi(r))
        if isim in gelen:
            yeni_kayitlar.append(gelen[isim])
            gorulen.add(isim)
            print(f"    [REVİZE] {kanal_adi(r)}")
        else:
            yeni_kayitlar.append(r)
            print(f"    [KORUNDU] {kanal_adi(r)}")
        son = len(yeni_kayitlar)
    eklenecek = []
    for isim, rec in gelen.items():
        if isim not in gorulen:
            eklenecek.append(rec)
            print(f"    [EKLENDİ] {kanal_adi(rec)}")
    if eklenecek:
        if son is not None:
            yeni_kayitlar[son:son] = eklenecek
        else:
            yeni_kayitlar.extend(eklenecek)
    return yeni_kayitlar

def benzer_grubun_bitisini_bul(hedef_records, hedef_baslangic):
    benzer_indexler = [i for i, r in enumerate(hedef_records) if grup_baslangici(grup_bul(r)) == hedef_baslangic and grup_bul(r)]
    if not benzer_indexler:
        return None
    return max(benzer_indexler)

# ==================================================
# ANA İŞLEM
# ==================================================

def main():
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} bulunamadı!")
        return

    print("\n====================================")
    print(" MIRTI68 - TEK AKTARICI BAŞLADI")
    print(" HATALI URL ATLANACAK")
    print("====================================")

    try:
        baslik, hedef_records, newline, enc = oku_m3u(HEDEF_DOSYA)
    except Exception as hata:
        print(f"[HATA] Hedef dosya okunamadı: {hata}")
        return

    basarili = 0
    hatali = 0
    eklenen_toplam = 0

    # YENİ EKLENDİ: Hatalı URL'leri burada toplayacağız
    hatali_url_listesi = []

    def hata_ekle(cfg, sebep):
        # Şifreyi logda gizle, sadece domain + hedef grup göster
        ham_url = cfg.get("kaynak_url", "")
        temiz_url = ham_url.split("?")[0]
        hatali_url_listesi.append({
            "hedef_grup": cfg.get("hedef_grup", "?"),
            "kaynak_grup": cfg.get("kaynak_grup", ""),
            "url": temiz_url,
            "sebep": str(sebep),
        })

    for sira, cfg in enumerate(AKTARIMLAR, 1):
        url = cfg["kaynak_url"]
        print(f"\n[{sira}/{len(AKTARIMLAR)}] KAYNAK:")
        print(url.split("?")[0])
        print(f"HEDEF GRUP: {cfg['hedef_grup']}")
        if cfg.get("kaynak_grup"):
            print(f"ARANAN KAYNAK GRUP: {cfg['kaynak_grup']}")

        try:
            _, kaynak_records, _, _ = oku_m3u(url)
        except urllib.error.HTTPError as hata:
            hatali += 1
            sebep = f"HTTP {hata.code} - {hata.reason}"
            hata_ekle(cfg, sebep)
            print(f"  [ATLANDI] {sebep}")
            print("  [DEVAM] Sonraki kaynağa geçiliyor.")
            continue
        except urllib.error.URLError as hata:
            hatali += 1
            sebep = f"Bağlantı hatası: {hata.reason}"
            hata_ekle(cfg, sebep)
            print(f"  [ATLANDI] {sebep}")
            continue
        except (TimeoutError, socket.timeout) as hata:
            hatali += 1
            sebep = f"Zaman aşımı: {hata}"
            hata_ekle(cfg, sebep)
            print(f"  [ATLANDI] {sebep}")
            continue
        except Exception as hata:
            hatali += 1
            sebep = f"{type(hata).__name__}: {hata}"
            hata_ekle(cfg, sebep)
            print(f"  [ATLANDI] {sebep}")
            continue

        if not kaynak_records:
            hatali += 1
            sebep = "Kaynakta M3U kaydı bulunamadı (boş dosya)"
            hata_ekle(cfg, sebep)
            print(f"  [ATLANDI] {sebep}")
            continue

        if cfg.get("kaynak_grup"):
            kaynak_gruplar = sorted(set(grup_bul(r) for r in kaynak_records if grup_bul(r)))
            print(f"  [DEBUG] Kaynakta {len(kaynak_gruplar)} grup var")
            eslesen = [gg for gg in kaynak_gruplar if grup_eslesiyor_mu(gg, cfg["kaynak_grup"])]
            if eslesen:
                print(f"  [DEBUG] Eşleşen kaynak grupları: {eslesen}")
            else:
                print(f"  [UYARI] '{cfg['kaynak_grup']}' ile eşleşen grup bulunamadı!")

        try:
            secilen = kaynak_sec(kaynak_records, cfg)
        except Exception as hata:
            hatali += 1
            sebep = f"Filtreleme hatası: {hata}"
            hata_ekle(cfg, sebep)
            print(f"  [ATLANDI] {sebep}")
            continue

        if not secilen:
            print("  [BOŞ] Uygun kanal bulunamadı.")
            # DEBUG: Kaynakta gerçekte hangi gruplar var?
            _gruplar = sorted(set(grup_bul(r) for r in kaynak_records if grup_bul(r)))
            print(f"  [DEBUG] Kaynakta {len(_gruplar)} grup var, ilk 30:")
            for _gg in _gruplar[:30]:
                print(f"    - '{_gg}' -> norm_sinema: '{norm_sinema(_gg)}' | normalize: '{normalize(_gg)}'")
            if cfg.get("kaynak_gruplar"):
                print(f"  [DEBUG] Aranan kaynak_gruplar (norm_sinema): {[norm_sinema(x) for x in cfg['kaynak_gruplar']]}")
            print("  [DEVAM] Hedef gruba dokunulmadı.")
            # BOŞ da bir hata sayılsın istiyorsan bunu aç:
            # hata_ekle(cfg, "Eşleşen kanal bulunamadı (grup adı / aranacak yanlış olabilir)")
            basarili += 1
            continue

        print(f"  [OKUNDU] {len(secilen)} kanal bulundu.")
        hedef_grup = cfg["hedef_grup"]

        ayni_grup_var = any(grup_bul(r) == hedef_grup for r in hedef_records)

        if ayni_grup_var:
            onceki_sayi = len(hedef_records)
            hedef_records = grubu_birlestir(hedef_records, secilen, hedef_grup)
            fark = len(hedef_records) - onceki_sayi
            eklenen_toplam += max(0, fark)
            print(f"  [YAZILDI] Grup birleştirildi: {hedef_grup}")
            basarili += 1
            continue

        # hedef_grup boşsa (SİNEMA) kendi grubuyla sona ekle, benzer grup arama
        if not hedef_grup:
            hedef_records.extend(secilen)
            print(f"  [YAZILDI] Kaynak grupları aynen eklendi: {len(secilen)} kanal")
            eklenen_toplam += len(secilen)
            basarili += 1
            continue
        hedef_baslangic = grup_baslangici(hedef_grup)
        print(f"  [DEBUG] Hedef başlangıç: '{hedef_baslangic}'")
        son_benzer_idx = benzer_grubun_bitisini_bul(hedef_records, hedef_baslangic)
        if son_benzer_idx is not None:
            hedef_records = hedef_records[:son_benzer_idx + 1] + secilen + hedef_records[son_benzer_idx + 1:]
            print(f"  [YAZILDI] Benzer grubun altına eklendi: {hedef_baslangic}")
        else:
            hedef_records.extend(secilen)
            print("  [YAZILDI] Yeni grup en sona eklendi.")
        eklenen_toplam += len(secilen)
        basarili += 1

    print("\n====================================")
    print(" MIRTI68 - DOSYA KAYDEDİLİYOR")
    print("====================================")

    try:
        shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA + ".bak")
        print("[YEDEK] mirti68.m3u.bak oluşturuldu.")
    except Exception as hata:
        print(f"[UYARI] Yedek oluşturulamadı: {hata}")

    sonuc = list(baslik)
    for r in hedef_records:
        sonuc.extend(r)

    try:
        with open(HEDEF_DOSYA, "w", encoding=enc, newline="") as f:
            f.write(newline.join(sonuc) + newline)
    except Exception as hata:
        print(f"[HATA] Dosya yazılamadı: {hata}")
        return

    print("\n====================================")
    print(" MIRTI68 - AKTARIM TAMAMLANDI")
    print("====================================")
    print(f"[BAŞARILI] {basarili}")
    print(f"[HATALI / ATLANAN] {hatali}")
    print(f"[EKLENEN KAYIT] {eklenen_toplam}")
    print(f"[TOPLAM KANAL] {len(hedef_records)}")
    print(f"[DOSYA] {HEDEF_DOSYA}")

    # YENİ EKLENDİ: Hatalı URL listesi - en sonda toplu göster
    print("\n====================================")
    print(" HATALI URL LİSTESİ")
    print("====================================")
    if not hatali_url_listesi:
        print("[TEMİZ] Hata veren URL yok, hepsi çalıştı.")
    else:
        for i, h in enumerate(hatali_url_listesi, 1):
            print(f"\n[{i}] HEDEF GRUP: {h['hedef_grup']}")
            print(f"    KAYNAK GRUP: {h['kaynak_grup']}")
            print(f"    URL: {h['url']}")
            print(f"    SEBEP: {h['sebep']}")
        # Ayrıca dosyaya da yaz - GitHub Actions logundan kaybolmasın
        try:
            with open("hatali_url_listesi.txt", "w", encoding="utf-8") as f:
                f.write("MIRTI68 - HATALI URL LİSTESİ\n")
                f.write("="*50 + "\n")
                for h in hatali_url_listesi:
                    f.write(f"\nHEDEF GRUP: {h['hedef_grup']}\n")
                    f.write(f"KAYNAK GRUP: {h['kaynak_grup']}\n")
                    f.write(f"URL: {h['url']}\n")
                    f.write(f"SEBEP: {h['sebep']}\n")
            print("\n[DOSYA] hatali_url_listesi.txt dosyasına da yazıldı.")
        except Exception as e:
            print(f"[UYARI] Hatalı liste dosyaya yazılamadı: {e}")

    print("====================================")
    print("[TAMAM] ÇALIŞAN KAYNAKLAR AKTARILDI")
    print("[TAMAM] Hatalı URL'ler işlemi durdurmadı")
    print("====================================")

if __name__ == "__main__":
    main()    # SINEMA MODU: Grup adı değişmeli - IMDb Top Rated -> 🟪◆ FILM - IMDb Top Rated ⭕
    if cfg.get("sinema_modu"):
        _g = grup_bul(rec).strip()
        _clean = SINEMA_WANTED.get(norm_sinema(_g), _g)
        _clean = re.sub(r"\s+", " ", _clean).strip()
        if "FILM" not in _clean.upper():
            _clean = f"FILM - {_clean}"
        cfg = dict(cfg)
        cfg["hedef_grup"] = f"🟪◆ {_clean} ⭕"
        cfg["_sinema_tvg_type"] = True
