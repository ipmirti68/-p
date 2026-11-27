# MIRTI68 - FILM AKTARICI - EPG KORU + YERINDE EKLE + OK ISARETI OKUR - TAM HALI
# Okur: aktarfilim.yaml - 3 formati da okur, baslikli / basliksiz farketmez
# Yazar: film.tmp.m3u + mirtitv68.m3u
import re, os, shutil, urllib.request, urllib.parse, json, time
try:
    import yaml
except ImportError:
    yaml = None

HEDEF_DOSYA = "mirtitv68.m3u"
FILM_YAML = "aktarfilim.yaml"
TMP_DOSYA = "film.tmp.m3u"
VARSAYILAN_KAYNAK = "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
TIMEOUT = 30
_FILM_CACHE = {}

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    return re.sub(r"\s+"," ",s).strip()

def norm_sinema(s):
    return re.sub(r'[^a-z0-9çğıöşü]+','',(s or "").lower())

def norm_grup(s):
    return re.sub(r'[^a-z0-9]', '', normalize(s))

def url_norm(u):
    u = (u or "").strip()
    u = u.replace("?.mp4", "").replace("?ext=.mp4", "").replace("?.m3u8", "")
    if u.endswith(".mp4"):
        u = u[:-4]
    if u.endswith("/"):
        u = u[:-1]
    return u.lower()

def benzer_grup_bul(hedef_grup, mevcut_gruplar):
    hedef_n = norm_grup(hedef_grup)
    hedef_kelimeler = set(normalize(hedef_grup).split())
    hedef_kelimeler.discard("film"); hedef_kelimeler.discard("filim")
    en_iyi = None; en_iyi_skor = 0
    for g in mevcut_gruplar:
        if not g: continue
        g_n = norm_grup(g)
        if g_n == hedef_n: return g
        skor = 0
        if hedef_n and g_n and (hedef_n in g_n or g_n in hedef_n): skor += 10
        g_kelimeler = set(normalize(g).split()); g_kelimeler.discard("film"); g_kelimeler.discard("filim")
        ortak = hedef_kelimeler & g_kelimeler
        skor += len(ortak) * 5
        if skor > en_iyi_skor and (len(ortak) > 0 or hedef_n in g_n or g_n in hedef_n):
            en_iyi_skor = skor; en_iyi = g
    return en_iyi

SINEMA_WANTED_RAW = [" 【entity-IMDb¦canonical_name=IMDb】 Top Rated","YERLI FILM","KEMAL SUNAL","KORKU","WESTERN","YeniEklenenler","2026","2025","2023 2024","2021 2022","2019 2020","2017 2018","2015 2016","2013 2014","2011 2012","2001 2010"]
SINEMA_WANTED = {norm_sinema(x): x for x in SINEMA_WANTED_RAW}
SINEMA_EXCLUDED = [" adam sandler","clint eastwood"," sylvester stallone"," jackie chan","nicolas cage"," steven seagal"," jason statham","seri","dizi","series","sezon","season","episode","bölüm","bolum","s01e","s02e","s03e"]
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

def yaml_oku_guvenli(path):
    # DUZELTILDI: Once gercek yaml dene, olmazsa satir satir oku - baslikli / basliksiz farketmez
    # 1. Gercek yaml
    if yaml is not None:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            liste = None
            if isinstance(data, dict):
                liste = data.get("filmler") or data.get("filim") or data.get("filimler")
            elif isinstance(data, list):
                liste = data
            if liste:
                out = {"filmler": []}
                for item in liste:
                    if not isinstance(item, dict): continue
                    hedefler = []
                    # hedefler: [...] varsa onu al
                    for h in (item.get("hedefler") or []):
                        if isinstance(h, dict):
                            hedefler.append({"hedef_adi": str(h.get("hedef_adi","") or ""), "aranacak": str(h.get("aranacak","") or ""), "hedef_grup": str(h.get("hedef_grup","") or ""), "hedef_logo": str(h.get("hedef_logo","") or ""), "ek_kod": str(h.get("ek_kod","") or "")})
                    # hedefler yoksa tek hedef_grup'tan hedef yap
                    if not hedefler and item.get("hedef_grup"):
                        hedefler = [{"hedef_adi": "hedef_1", "aranacak": str(item.get("aranacak","") or ""), "hedef_grup": str(item.get("hedef_grup","") or ""), "hedef_logo": str(item.get("hedef_logo","") or ""), "ek_kod": str(item.get("ek_kod","") or "")}]
                    out["filmler"].append({"kaynak_url": str(item.get("kaynak_url","") or VARSAYILAN_KAYNAK), "kaynak_grup": str(item.get("kaynak_grup","") or ""), "hedef_grup": str(item.get("hedef_grup","") or ""), "kaynak_gruplar": item.get("kaynak_gruplar", []) or [], "sinema_modu": True, "film_bilgi_al": True, "hedefler": hedefler})
                print(f"[BILGI] yaml normal okundu, blok: {len(out['filmler'])}")
                for b in out["filmler"]:
                    for h in b["hedefler"]:
                        print(f"  - {h.get('aranacak') or b['kaynak_grup']} -> {h.get('hedef_grup')}")
                return out
        except Exception as e:
            print(f"[UYARI] yaml normal okunamadi: {e}, girintisiz okuma deneniyor")
    # 2. Girintisiz / satir satir - baslik olsun olmasin calisir
    def temiz(v):
        v = v.strip().strip(",")
        if v.startswith("- "): v = v[2:].strip()
        if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
            v = v[1:-1]
        return v.strip().strip("-").strip()
    out = {"filmler": []}
    cur = None
    cur_hedef = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s in ("filmler:", "filim:", "filimler:"): continue
            # Ok isaretli satir
            if "->" in s and "kaynak_url:" not in s and "hedef_grup:" not in s and "kaynak_grup:" not in s:
                sol, sag = s.split("->", 1)
                sol = temiz(sol); sag = temiz(sag)
                sol = re.sub(r'^[🟪◆\s]+', '', sol).strip()
                if not sol or not sag: continue
                if cur: out["filmler"].append(cur)
                cur = {"kaynak_url": VARSAYILAN_KAYNAK, "kaynak_grup": sol, "hedef_grup": sag, "kaynak_gruplar": [], "sinema_modu": True, "film_bilgi_al": True, "hedefler": [{"hedef_adi": "hedef_1", "aranacak": "", "hedef_grup": sag, "hedef_logo": "", "ek_kod": ""}]}
                cur_hedef = cur["hedefler"][0]
                continue
            if "kaynak_url:" in s:
                if cur: out["filmler"].append(cur)
                v = s.split("kaynak_url:",1)[1]
                cur = {"kaynak_url": temiz(v), "kaynak_grup": "", "hedef_grup": "", "kaynak_gruplar": [], "sinema_modu": True, "film_bilgi_al": True, "hedefler": []}
                cur_hedef = None
                continue
            if cur is None: continue
            # DUZELTILDI: hedefler icindeki hedef_adi / aranacak / hedef_grup artik okunuyor
            if "hedef_adi:" in s:
                cur_hedef = {"hedef_adi": temiz(s.split("hedef_adi:",1)[1]), "aranacak": "", "hedef_grup": "", "hedef_logo": "", "ek_kod": ""}
                cur["hedefler"].append(cur_hedef)
                continue
            if "aranacak:" in s and cur_hedef is not None:
                cur_hedef["aranacak"] = temiz(s.split("aranacak:",1)[1]); continue
            if "hedef_logo:" in s and cur_hedef is not None:
                cur_hedef["hedef_logo"] = temiz(s.split("hedef_logo:",1)[1]); continue
            if "ek_kod:" in s and cur_hedef is not None:
                cur_hedef["ek_kod"] = temiz(s.split("ek_kod:",1)[1]); continue
            if "hedef_grup:" in s:
                v = temiz(s.split("hedef_grup:",1)[1])
                if cur_hedef is not None:
                    cur_hedef["hedef_grup"] = v
                else:
                    cur["hedef_grup"] = v
                    cur["hedefler"] = [{"hedef_adi": "hedef_1", "aranacak": "", "hedef_grup": v, "hedef_logo": "", "ek_kod": ""}]
                    cur_hedef = cur["hedefler"][0]
                continue
            if "kaynak_grup:" in s:
                cur["kaynak_grup"] = temiz(s.split("kaynak_grup:",1)[1]); continue
    if cur: out["filmler"].append(cur)
    print(f"[BILGI] Girintisiz okundu, blok: {len(out['filmler'])}")
    for b in out["filmler"]:
        for h in b["hedefler"]:
            print(f"  - {h.get('aranacak') or b['kaynak_grup']} -> {h.get('hedef_grup')}")
    return out

def main():
    print("MIRTI68 - FILM BASLADI - aktarfilim.yaml okunuyor")
    if not os.path.exists(FILM_YAML):
        print(f"[HATA] {FILM_YAML} yok"); return
    cfg = yaml_oku_guvenli(FILM_YAML)
    filmler = cfg.get("filmler", []) or []
    print(f"[BILGI] Film blok: {len(filmler)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return
    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(url_norm(u))
    yeni_by_grup = {}
    film_lines = ["#EXTM3U"]
    bilgi_alinan = 0
    eklenen_toplam = 0
    for sira, f in enumerate(filmler, 1):
        if not isinstance(f, dict): continue
        kurl = str(f.get("kaynak_url","") or "").strip() or VARSAYILAN_KAYNAK
        hedefler = f.get("hedefler", []) or []
        if not hedefler and f.get("hedef_grup"):
            hedefler = [{"hedef_adi": "hedef_1", "aranacak": f.get("aranacak",""), "hedef_grup": f.get("hedef_grup",""), "hedef_logo": f.get("hedef_logo",""), "ek_kod": f.get("ek_kod","")}]
        bilgi_al = bool(f.get("film_bilgi_al", True))
        print(f"[FILM {sira}] {kurl[:60]} - hedef: {len(hedefler)}")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        kg = str(f.get("kaynak_grup","") or "").strip()
        kgs = f.get("kaynak_gruplar", []) or []
        if isinstance(kgs, str): kgs = [kgs]
        sinema_modu = bool(f.get("sinema_modu", False))
        eklenen_blok = 0
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if url_norm(u) in gorulen: continue
            g = grup_bul(r)
            if kgs:
                kgs_n = [norm_sinema(x) if sinema_modu else normalize(x) for x in kgs if str(x).strip()]
                _n = norm_sinema(g) if sinema_modu else normalize(g)
                if _n not in kgs_n: continue
            elif kg:
                if normalize(kg) not in normalize(g) and normalize(g) not in normalize(kg): continue
            if sinema_modu and sinema_excluded(g): continue
            eslesen = None
            for h in hedefler:
                if not isinstance(h, dict): continue
                hg = str(h.get("hedef_grup","") or "").strip()
                if not hg and not sinema_modu: continue
                ar = str(h.get("aranacak","") or "").strip()
                if sinema_modu and not ar:
                    eslesen = h; break
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
            if sinema_modu and not hedef_grup:
                _clean = SINEMA_WANTED.get(norm_sinema(g), g)
                _clean = re.sub(r"\s+", " ", _clean).strip()
                hedef_grup = f"🟪◆FİLM - {_clean.upper()}"
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
                # EPG KORUMA VAR: tvg-id, tvg-epg, catchup aynen kalir
                gelen_id = oz.get("tvg-id","").strip()
                gelen_epg = oz.get("tvg-epg","").strip()
                gelen_logo = oz.get("tvg-logo","").strip()
                gelen_name = oz.get("tvg-name","").strip()
                oz["group-title"] = hedef_grup
                if not gelen_name:
                    oz["tvg-name"] = yeni_ad
                if gelen_epg:
                    oz["tvg-epg"] = gelen_epg
                if gelen_id:
                    oz["tvg-id"] = gelen_id
                # Internetten gelen tt... artik tvg-id'yi ezmiyor
                if not gelen_logo and hedef_logo:
                    oz["tvg-logo"] = hedef_logo
                elif not gelen_logo and not hedef_logo and poster:
                    oz["tvg-logo"] = poster
                if sinema_modu and "tvg-type" not in oz: oz["tvg-type"] = "movie"
                if aciklama and not oz.get("tvg-plot"):
                    oz["tvg-plot"] = aciklama.replace('"','').replace('\n',' ')[:300]
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            if sinema_modu:
                for i,l in enumerate(yeni):
                    if l.strip().startswith(("http://","https://")): yeni[i]=sinema_fix_url(l.strip())
            yeni_by_grup.setdefault(hedef_grup, []).extend(yeni)
            film_lines.extend(yeni); gorulen.add(url_norm(u))
            eklenen_blok += 1; eklenen_toplam += 1
        print(f"  [OK] {sira}. blok bitti, bu blokta eklenen: {eklenen_blok}, internetten bilgi alinan: {bilgi_alinan}")
    lines = []
    if not baslik or not baslik[0].strip().startswith("#EXTM3U"):
        lines.append("#EXTM3U")
    else:
        lines.extend(baslik)
    mevcut_gruplar = []
    for r in hedef_records:
        g = grup_bul(r)
        if g and g not in mevcut_gruplar: mevcut_gruplar.append(g)
    eklenmis = set()
    for i, r in enumerate(hedef_records):
        lines.extend(r)
        g = grup_bul(r)
        sonraki = grup_bul(hedef_records[i+1]) if i+1 < len(hedef_records) else None
        if g in yeni_by_grup and g not in eklenmis and g != sonraki:
            lines.extend(yeni_by_grup[g])
            eklenmis.add(g)
            print(f"[YERLESTI] {g} grubunun icine eklendi")
    for g, recs in yeni_by_grup.items():
        if g in eklenmis: continue
        benzer = benzer_grup_bul(g, mevcut_gruplar)
        if benzer:
            print(f"[BENZER] {g} yok, benzer grup bulundu: {benzer} -> onun altina ekleniyor")
            son_idx = -1
            for idx2, satir in enumerate(lines):
                if satir.startswith("#EXTINF:"):
                    m = re.search(r'group-title="([^"]*)"', satir)
                    if m and m.group(1) == benzer:
                        son_idx = idx2 + 1
                        while son_idx < len(lines) and not lines[son_idx].startswith("#EXTINF:") and not lines[son_idx].startswith("#EXT"):
                            son_idx += 1
            if son_idx > 0:
                for j, yeni_satir in enumerate(recs):
                    lines.insert(son_idx + j, yeni_satir)
                mevcut_gruplar.append(g); eklenmis.add(g)
                continue
        print(f"[SONA] {g} icin benzer grup yok, en sona eklendi")
        lines.extend(recs); eklenmis.add(g)
    with open(TMP_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(film_lines)+"\n")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"): lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} + {TMP_DOSYA} - Toplam eklenen film: {eklenen_toplam}")

if __name__ == "__main__":
    main()
