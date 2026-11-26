# MIRTI68 - FILM AKTARICI
# Okur: aktarfilm.yaml
# Yazar: film.tmp.m3u + mirti68.m3u
# film_bilgi_al: true ise internetten poster + yil + aciklama ceker
# Bulamazsa eski haline doner, film dusmez
# Ayni url varsa eklemez, EPG korunur
import re, os, shutil, urllib.request, urllib.parse, json, time
try:
    import yaml
except ImportError:
    yaml = None
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

HEDEF_DOSYA = "mirti.m3u"
FILM_YAML = "aktarfilim.yaml"
TMP_DOSYA = "film.tmp.m3u"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
TIMEOUT = 30

# Internetten bilgi icin onbellek, ayni filmi 2. kez sormasin
_FILM_CACHE = {}

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    return re.sub(r"\s+"," ",s).strip()

def norm_sinema(s):
    return re.sub(r'[^a-z0-9çğıöşü]+','',(s or "").lower())

SINEMA_WANTED_RAW = [" 【entity-IMDb¦canonical_name=IMDb】 Top Rated","YERLI FILM","KEMAL SUNAL","KORKU","WESTERN","YeniEklenenler","2026","2025","2023 2024","2021 2022","2019 2020","2017 2018","2015 2016","2013 2014","2011 2012","2001 2010"]
SINEMA_WANTED = {norm_sinema(x): x for x in SINEMA_WANTED_RAW}
SINEMA_EXCLUDED = [" 【entity-adam sandler¦canonical_name=adam sandler】","clint eastwood"," 【entity-sylvester stallone¦canonical_name=sylvester stallone】"," 【entity-jackie chan¦canonical_name=jackie chan】","nicolas cage"," 【entity-steven seagal¦canonical_name=steven seagal】"," 【entity-jason statham¦canonical_name=jason statham】","seri","dizi","series","sezon","season","episode","bölüm","bolum","s01e","s02e","s03e"]
def sinema_excluded(text):
    t = " " + re.sub(r'[^a-z0-9çğıöşü]+',' ',(text or "").lower()) + " "
    compact = (text or "").lower().replace(" ","")
    for w in SINEMA_EXCLUDED:
        if w in ("s01e","s02e","s03e"):
            if w in compact: return True
        else:
            nw = re.sub(r'[^a-z0-9çğıöşü]+',' ',w.lower()).strip()
            if f" {nw} " in t: return True
    return False
def sinema_fix_url(url):
    url = (url or "").strip().replace("?.mp4","").replace("?ext=.mp4","")
    if "vixolity.com/vs/" in url and url.endswith(".mp4"): url = url[:-4]
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
            ad = l.rsplit(",",1)[-1].strip()
            if 'tvg-name="' in ad:
                m = re.search(r'tvg-name="([^"]*)"', ad)
                if m: return m.group(1).strip()
            return ad
    return ""
def kanal_url(rec):
    for l in reversed(rec):
        s = l.strip()
        if s and not s.startswith("#") and re.match(r'^(https?|rtmp|rtsp|ftp)://', s, re.IGNORECASE):
            return s
    return ""

def oku_m3u(p):
    if p.startswith("http"):
        req = urllib.request.Request(p, headers={"User-Agent":USER_AGENT,"Accept":"*/*","Connection":"close"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r: metin = r.read().decode("utf-8-sig", errors="ignore")
    else:
        if not os.path.exists(p): raise FileNotFoundError(p)
        with open(p,"rb") as f: metin = f.read().decode("utf-8-sig", errors="ignore")
    satirlar = metin.splitlines()
    birlesik = []
    for line in satirlar:
        s = line.strip()
        if not s: continue
        if birlesik and birlesik[-1].startswith("#EXTINF:") and not s.startswith("#EXTINF:") and not s.startswith("http") and not s.startswith("#"):
            birlesik[-1] += " " + s; continue
        birlesik.append(s)
    satirlar = birlesik
    ilk = next((i for i,s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik, govde = satirlar[:ilk], satirlar[ilk:]
    records, cur = [], []
    for line in govde:
        if line.startswith("#EXTINF:") and cur: records.append(cur); cur=[]
        cur.append(line)
    if cur: records.append(cur)
    return baslik, records

def film_bilgisi_yerel(ham):
    s = (ham or "").strip()
    yil = ""
    m = re.search(r'\b(19\d{2}|20[0-3]\d)\b', s)
    if m: yil = m.group(1)
    s2 = re.sub(r'\(\s*(19\d{2}|20[0-3]\d)\s*\)', ' ', s)
    s2 = re.sub(r'\b(1080p|720p|4K|UHD|FHD|HD|CAM|TS|WEB-DL|BluRay|Dublaj|Altyazılı|Altyazili|Türkçe|Turkce|Dublajlı)\b', ' ', s2, flags=re.I)
    s2 = re.sub(r'[._\-]+', ' ', s2)
    s2 = re.sub(r'\s+', ' ', s2).strip().strip(" -|")
    if not s2: s2 = s
    return s2, yil

def film_bilgisi_internet(baslik, yil_hint=""):
    # Anahtarsiz acik kaynak: poster + yil + aciklama + kimlik doner
    # Bulamazsa None doner, py eski haline doner
    anahtar = normalize(baslik) + "|" + str(yil_hint)
    if anahtar in _FILM_CACHE: return _FILM_CACHE[anahtar]
    sonuc = None
    try:
        q = baslik
        if yil_hint: q = f"{baslik} {yil_hint}"
        url = "https://search.imdbot.workers.dev/?q=" + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        # Ilk dogru sonucu al
        adaylar = []
        if isinstance(data, dict):
            if isinstance(data.get("description"), list): adaylar = data["description"]
            elif isinstance(data.get("results"), list): adaylar = data["results"]
        for a in adaylar[:3]:
            if not isinstance(a, dict): continue
            poster = a.get("image") or a.get("poster") or ""
            y = str(a.get("year") or a.get("yr") or yil_hint or "")
            kimlik = a.get("id") or a.get("imdb_id") or ""
            aciklama = a.get("plot") or a.get("description") or ""
            if poster or kimlik:
                sonuc = {"poster": poster, "yil": y, "kimlik": kimlik, "aciklama": aciklama}
                break
        time.sleep(0.15)
    except Exception:
        sonuc = None
    _FILM_CACHE[anahtar] = sonuc
    return sonuc

def main():
    print("MIRTI68 - FILM BASLADI - aktarfilm.yaml okunuyor")
    if not os.path.exists(FILM_YAML):
        print(f"[HATA] {FILM_YAML} yok"); return
    with open(FILM_YAML, encoding="utf-8") as f: cfg = yaml.safe_load(f) or {}
    filmler = cfg.get("filmler", []) or []
    print(f"[BILGI] Film blok: {len(filmler)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return

    def kalacak_mi(r):
        g = grup_bul(r)
        if "🟪◆ FİLM" in g or "🟪◆ FILM" in g or "🟪◆ FİLİM" in g: return False
        return True
    hedef_records = [r for r in hedef_records if kalacak_mi(r)]
    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(u.strip())
    lines = []
    for r in hedef_records: lines.extend(r)
    film_lines = ["#EXTM3U"]
    bilgi_alinan = 0

    for sira, f in enumerate(filmler, 1):
        if not isinstance(f, dict): continue
        kurl = str(f.get("kaynak_url","") or "").strip()
        if not kurl: continue
        hedefler = f.get("hedefler", []) or []
        if not hedefler and f.get("hedef_grup"):
            hedefler = [{"hedef_adi": "hedef_1", "aranacak": f.get("aranacak",""), "hedef_grup": f.get("hedef_grup",""), "hedef_logo": f.get("hedef_logo",""), "ek_kod": f.get("ek_kod","")}]
        bilgi_al = bool(f.get("film_bilgi_al", True))
        print(f"[FILM {sira}] {kurl[:60]} - bilgi_al: {bilgi_al}")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        kg = str(f.get("kaynak_grup","") or "").strip()
        kgs = f.get("kaynak_gruplar", []) or []
        if isinstance(kgs, str): kgs = [kgs]
        sinema_modu = bool(f.get("sinema_modu", False))
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if u.strip() in gorulen: continue
            g = grup_bul(r)
            if kgs:
                kgs_n = [norm_sinema(x) if sinema_modu else normalize(x) for x in kgs if str(x).strip()]
                _n = norm_sinema(g) if sinema_modu else normalize(g)
                if _n not in kgs_n: continue
            elif kg:
                if normalize(g) != normalize(kg): continue
            if sinema_modu and (sinema_excluded(g) or sinema_excluded(ad)): continue
            # Hedef sec: sinema modunda hedef_grup bos ise kaynak grubunu kullan
            eslesen = None
            for h in hedefler:
                if not isinstance(h, dict): continue
                # hedef_grup bos + sinema_modu -> kabul et, grup kaynaktan gelecek
                if sinema_modu:
                    eslesen = h; break
                hg = str(h.get("hedef_grup","") or "").strip()
                if not hg: continue
                ar = str(h.get("aranacak","") or "").strip()
                if not ar:
                    eslesen = h; break
                for parca in [x.strip() for x in ar.split(",") if x.strip()]:
                    if normalize(parca) in normalize(ad):
                        eslesen = h; break
                if eslesen: break
            if not eslesen: continue
            hedef_grup = str(eslesen.get("hedef_grup","") or "").strip()
            hedef_logo = str(eslesen.get("hedef_logo","") or "").strip()
            ek_kod = str(eslesen.get("ek_kod","") or "").strip()
            # Sinema grubu: kaynak grubundan uret
            if sinema_modu and not hedef_grup:
                _clean = SINEMA_WANTED.get(norm_sinema(g), g)
                _clean = re.sub(r"\s+", " ", _clean).strip()
                if "FILM" not in _clean.upper(): _clean = f"FILM - {_clean}"
                hedef_grup = f"🟪◆ {_clean} ⭕"
            # Film bilgisi: yerel + internet
            temiz_ad, yil_yerel = film_bilgisi_yerel(ad)
            poster = ""; kimlik = ""; aciklama = ""
            if bilgi_al:
                info = film_bilgisi_internet(temiz_ad, yil_yerel)
                if info:
                    poster = info.get("poster","") or ""
                    if info.get("yil"): yil_yerel = str(info["yil"])
                    kimlik = info.get("kimlik","") or ""
                    aciklama = info.get("aciklama","") or ""
                    bilgi_alinan += 1
            yeni_ad = f"{temiz_ad} ({yil_yerel})" if yil_yerel else temiz_ad
            if ek_kod and not yeni_ad.endswith(ek_kod):
                yeni_ad = f"{yeni_ad} {ek_kod}"
            yeni = list(r)
            idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
            if idx is not None:
                extinf = yeni[idx]
                m = re.match(r"#EXTINF:(-?\d+)", extinf); sure = m.group(1) if m else "-1"
                oz = {}
                for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf): oz[k]=v
                oz["group-title"] = hedef_grup
                oz["tvg-name"] = yeni_ad
                # Logo: gelen varsa onu kullan, yoksa internet posteri, yoksa hedef logosu
                gelen_logo = oz.get("tvg-logo","").strip()
                if not gelen_logo and poster: oz["tvg-logo"] = poster
                elif not gelen_logo and hedef_logo: oz["tvg-logo"] = hedef_logo
                # Kimlik: EPG eslesmesi icin, varsa koru, yoksa internetten geleni yaz
                if kimlik and not oz.get("tvg-id"):
                    oz["tvg-id"] = kimlik
                if sinema_modu: oz["tvg-type"] = "movie"
                # Aciklama varsa tvg-plot olarak sakla, TiviMate bazi surumlerde gosterir
                if aciklama and not oz.get("tvg-plot"):
                    oz["tvg-plot"] = aciklama.replace('"','').replace('\n',' ')[:300]
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            if sinema_modu:
                for i,l in enumerate(yeni):
                    if l.strip().startswith(("http://","https://")): yeni[i]=sinema_fix_url(l.strip())
            lines.extend(yeni); film_lines.extend(yeni); gorulen.add(u.strip())
        print(f"  [OK] {sira}. blok bitti, internetten bilgi alinan: {bilgi_alinan}")

    with open(TMP_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(film_lines)+"\n")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"): lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} + {TMP_DOSYA}")

if __name__ == "__main__":
    main()
