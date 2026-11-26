# MIRTI68 - TEK AKTARICI
# BUNA DOKUNMA - Tum bilgi sdiziler.yaml'da
# url: MERKEZ ise merkezden, kendi adresi ise kendi adresinden ceker.
# Ayni bolum 2. kez eklenmez, liste cogalmaz.
# Logo: Gelenin logosu varsa onu al, yoksa yaml logosunu al.
import re, os, shutil, urllib.request
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

HEDEF_DOSYA = "mirti.m3u"
YAML_FILE = "aktardizi.yaml"
USER_AGENT = "Mozilla/5.0"
TIMEOUT = 30

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    return re.sub(r"\s+"," ",s).strip()

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
        req = urllib.request.Request(p, headers={"User-Agent":USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r: metin = r.read().decode("utf-8-sig", errors="ignore")
    else:
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

def normalize_m3u_lines(lines):
    out=[]; buf=""
    for raw in lines:
        s = raw.strip()
        if not s: continue
        if s.startswith("#EXTINF"):
            if buf: out.append(buf)
            buf=s; continue
        if buf:
            if re.match(r'^(https?|rtmp|rtsp|ftp)://', s, re.IGNORECASE):
                out.append(buf); buf=""; out.append(s); continue
            if s.startswith("#"): out.append(buf); buf=""; out.append(s); continue
            buf += " "+s; continue
        out.append(s)
    if buf: out.append(buf)
    return out

def fetch_lines(url):
    if HAS_REQUESTS:
        r = requests.get(url, headers={"User-Agent":USER_AGENT}, timeout=TIMEOUT); r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"; return r.text.splitlines()
    req = urllib.request.Request(url, headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r: return r.read().decode("utf-8-sig", errors="ignore").splitlines()

def se_bul(ad):
    m = re.search(r'[Ss](\d+)\s*[Ee](\d+)', ad)
    if m: return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    m = re.search(r'(\d+)\s*x\s*(\d+)', ad, flags=re.I)
    if m: return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    m = re.search(r'Sezon\s*(\d+).*?Bölüm\s*(\d+)', ad, flags=re.I)
    if m: return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    m = re.search(r'(\d+)\.\s*Bölüm', ad, flags=re.I)
    if m: return f"S01E{int(m.group(1)):02d}"
    m = re.search(r'(\d+)\.\s*Bolum', ad, flags=re.I)
    if m: return f"S01E{int(m.group(1)):02d}"
    return None

def get_source_logo(line):
    m = re.search(r'tvg-logo="([^"]*)"', line)
    return m.group(1).strip() if m else ""

def load_config():
    if not os.path.exists(YAML_FILE):
        raise FileNotFoundError(f"{YAML_FILE} bulunamadi!")
    with open(YAML_FILE, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg or {}

_MERKEZ = None
_MERKEZ_URL = None
def merkez_lines(url):
    global _MERKEZ, _MERKEZ_URL
    if _MERKEZ is None or _MERKEZ_URL != url:
        print(f"  [MERKEZ] {url} 1 kere cekiliyor...")
        _MERKEZ = normalize_m3u_lines(fetch_lines(url))
        _MERKEZ_URL = url
    return _MERKEZ

def make_records(src_lines, name, yaml_logo, tek_grup, kaynak_grup_filter=None, gorulen=None):
    # gorulen: daha once eklenen (url + ad) seti, ayni bolum 2. kez eklenmez
    if gorulen is None: gorulen = set()
    src_lines = normalize_m3u_lines(src_lines)
    yaml_logo = (yaml_logo or "").strip()
    records=[]; count=0; atlanan=0; i=0
    while i < len(src_lines):
        line = src_lines[i].strip()
        if not line.startswith("#EXTINF"): i+=1; continue
        if kaynak_grup_filter:
            gm = re.search(r'group-title="([^"]*)"', line); g = gm.group(1).strip() if gm else ""
            if not (g == kaynak_grup_filter or normalize(g) == normalize(kaynak_grup_filter)):
                i+=1; continue
        m = re.search(r',\s*(.*)$', line); raw = m.group(1).strip() if m else ""
        se = se_bul(raw)
        if se: yeni_ad = f"{name.upper()} {se}"
        else: yeni_ad = f"{name.upper()} - {raw}" if raw else name.upper()
        # LOGO KURALI: Gelenin logosu varsa onu al, yoksa yaml logosunu al
        gelen_logo = get_source_logo(line)
        final_logo = gelen_logo if gelen_logo else yaml_logo
        new_inf = f'#EXTINF:-1 tvg-name="{yeni_ad}" tvg-logo="{final_logo}" group-title="{tek_grup}",{yeni_ad}'
        url=""; j=i+1
        while j < len(src_lines):
            nxt = src_lines[j].strip()
            if nxt.startswith("#EXTINF"): break
            if nxt and not nxt.startswith("#") and re.match(r'^(https?|rtmp|rtsp|ftp)://', nxt, re.IGNORECASE): url=nxt; break
            j+=1
        if url:
            anahtar = (normalize(yeni_ad), url.strip())
            if anahtar in gorulen:
                atlanan += 1
            else:
                gorulen.add(anahtar)
                records.append(new_inf); records.append(url); count+=1
        i = j if j>i else i+1
    return records, count, atlanan

def dizi_adi_temizle(ham, sabit=None):
    if sabit: return sabit
    b = re.split(r'\s+[Ss]\d+\s*[Ee]\d+', ham or "", flags=re.I)[0]
    b = re.split(r'\s+\d+\s*x\s*\d+', b, flags=re.I)[0]
    b = re.split(r'\s+Sezon.*', b, flags=re.I)[0]
    b = re.split(r'\s+\d+\.\s*Bölüm.*', b, flags=re.I)[0]
    b = re.split(r'\s+\d+\.\s*Bolum.*', b, flags=re.I)[0]
    b = b.split(" - ")[0].split(" | ")[0]
    return re.sub(r'[🟪◆⭕▶]', '', b).strip().upper() or "DİZİ"

def hedefe_uyarla_dizi(rec, cfg, tek_grup, gorulen):
    # gorulen'e gore tekrar kontrolu, ayni url varsa atla
    u = kanal_url(rec)
    ham0 = kanal_adi(rec); se0 = se_bul(ham0); dizi0 = dizi_adi_temizle(ham0, cfg.get("sabit_dizi_adi") or None)
    ad0 = f"{dizi0} {se0}" if se0 else ham0
    anahtar = (normalize(ad0), u.strip())
    if u and anahtar in gorulen:
        return None
    if u: gorulen.add(anahtar)
    yeni = list(rec)
    idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
    if idx is None: return yeni
    ham = kanal_adi(rec); se = se_bul(ham); dizi = dizi_adi_temizle(ham, cfg.get("sabit_dizi_adi") or None)
    yeni_ad = f"{dizi} {se}" if se else ham
    extinf = yeni[idx]
    m = re.match(r"#EXTINF:(-?\d+)", extinf); sure = m.group(1) if m else "-1"
    oz = {}
    for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf): oz[k]=v
    oz["group-title"] = tek_grup; oz["tvg-name"] = yeni_ad
    # LOGO KURALI: Gelenin logosu varsa koru, yoksa yaml / aktarim logosunu al
    if not oz.get("tvg-logo") and cfg.get("hedef_logo"): oz["tvg-logo"] = cfg["hedef_logo"]
    oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
    yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
    return yeni

def main():
    print("MIRTI68 - YAML'dan okuyor - BASLADI")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: cfg = load_config()
    except Exception as e: print(f"[HATA] YAML: {e}"); return

    merkez_url = str(cfg.get("merkez_url","") or "").strip()
    tek_grup = str(cfg.get("dizi_tek_grup","") or "🟪◆ DİZİLER ⭕").strip()
    aktarimlar = cfg.get("aktarimlar", []) or []
    diziler = cfg.get("series", []) or cfg.get("diziler", []) or []
    print(f"[BILGI] Tek grup: {tek_grup} | Aktarim: {len(aktarimlar)} | Dizi: {len(diziler)}")

    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return

    # Eski dizi gruplarini temizle, kalan canli/film aynen durur
    hedef_records = [r for r in hedef_records if "DİZİ" not in grup_bul(r).upper() and "DIZI" not in grup_bul(r).upper()]

    # GORULEN: Bu calismada eklenenler, ayni bolum 2. kez eklenmez
    gorulen = set()

    # 1. AKTARIMLAR - yaml'dan, tekrar kontrolu ile
    for sira, a in enumerate(aktarimlar, 1):
        url = str(a.get("kaynak_url","") or "").strip()
        kg = str(a.get("kaynak_grup","") or "").strip()
        print(f"\n[{sira}/{len(aktarimlar)}] {kg or 'tum'}")
        if not url: continue
        try: _, kaynak = oku_m3u(url)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        secilen = []
        for r in kaynak:
            if kg and normalize(grup_bul(r)) != normalize(kg): continue
            if "bilgilendirme" in kanal_adi(r).lower(): continue
            c = hedefe_uyarla_dizi(r, a, tek_grup, gorulen)
            if c is not None: secilen.append(c)
        hedef_records.extend(secilen); print(f"  [OK] {len(secilen)} bolum (tekrarlar atlandi)")

    lines = []
    for r in hedef_records: lines.extend(r)
    print(f"\n[DIZILER] {len(diziler)} dizi")
    for sira, d in enumerate(diziler, 1):
        if not isinstance(d, dict): continue
        name = str(d.get("name","") or "").strip()
        url = str(d.get("url","") or "").strip()
        logo = str(d.get("logo","") or "").strip()
        mg = str(d.get("merkez_grup","") or name).strip()
        if not name: continue
        is_merkez = (url.upper() == "MERKEZ" or url == merkez_url)
        print(f"  [{sira}/{len(diziler)}] {name} -> {'MERKEZ' if is_merkez else 'OZEL'}")
        try:
            if is_merkez:
                records, count, atlanan = make_records(merkez_lines(merkez_url), name, logo, tek_grup, kaynak_grup_filter=mg, gorulen=gorulen)
            else:
                src = fetch_lines(url)
                records, count, atlanan = make_records(src, name, logo, tek_grup, kaynak_grup_filter=None, gorulen=gorulen)
        except Exception as e: print(f"    [ATLANDI] {e}"); continue
        if not records and atlanan == 0: print(f"    [BOS] Bulunamadi"); continue
        lines.extend(records); print(f"    [OK] {count} yeni bolum, {atlanan} tekrar atlandi")

    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"): lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} - Liste cogalmadi, tekrar eklenmedi")

if __name__ == "__main__":
    main()
