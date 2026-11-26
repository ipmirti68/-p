# MIRTI68 - DIZI - Nostalji icinde dizi grup
import re, os, shutil, urllib.request

HEDEF_DOSYA = "MIRTI_TV.m3u"
DIZI_YAML = "aktardizi.yaml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
TIMEOUT = 30

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    return re.sub(r"\s+"," ",s).strip()

def liste_parse(v):
    if not v: return []
    return [x.strip() for x in str(v).split(",") if x.strip()]

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

def dizi_adi_temizle(ad):
    s = (ad or "").strip()
    m = re.search(r'[Ss](\d{1,2})[Ee](\d{1,3})', s)
    if m:
        sezon, bolum = int(m.group(1)), int(m.group(2))
        temel = s[:m.start()].strip(" -|_.,")
        temel = re.sub(r'\s+', ' ', temel).strip()
        return temel, f"S{sezon:02d}E{bolum:02d}"
    m2 = re.search(r'Sezon\s*(\d+).*?B[oö]l[uü]m\s*(\d+)', s, re.I)
    if m2:
        temel = re.sub(r'Sezon.*', '', s, flags=re.I).strip(" -|")
        return temel, f"S{int(m2.group(1)):02d}E{int(m2.group(2)):02d}"
    m3 = re.search(r'(.+?)\s+(\d{1,4})\s*\.\s*(B[oö]l[uü]m|BOLUM)\b', s, re.I)
    if m3:
        return m3.group(1).strip(" -|"), f"{m3.group(2)}. BÖLÜM"
    m4 = re.search(r'(.+?)\s+(\d{1,4})\s*$', s)
    if m4 and len(m4.group(1)) > 2:
        return m4.group(1).strip(), f"{m4.group(2)}. BÖLÜM"
    return s, s

def yaml_oku_guvenli(path):
    def temiz(v):
        v = v.strip()
        if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
            v = v[1:-1]
        return v.strip()
    out = []
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s == "diziler:": continue
            if "kaynak_url:" in s:
                if cur: out.append(cur)
                cur = {"kaynak_url": temiz(s.split("kaynak_url:",1)[1]), "dizi_adi": "", "hedef_grup": "", "hedef_logo": "", "filtre_grup_icerir": "", "filtre_ad_icerir": "", "filtre_grup_haric": "", "filtre_ad_haric": ""}
            elif cur is not None:
                for anahtar in ["dizi_adi", "hedef_grup", "hedef_logo", "filtre_grup_icerir", "filtre_ad_icerir", "filtre_grup_haric", "filtre_ad_haric"]:
                    if anahtar + ":" in s:
                        cur[anahtar] = temiz(s.split(anahtar + ":",1)[1])
                        break
    if cur: out.append(cur)
    print(f"[BILGI] Girintisiz okundu, blok: {len(out)}")
    return out

def main():
    print("MIRTI68 - DIZI BASLADI")
    if not os.path.exists(DIZI_YAML):
        print(f"[HATA] {DIZI_YAML} yok"); return
    diziler = yaml_oku_guvenli(DIZI_YAML)
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return
    def kalacak_mi(r):
        g = grup_bul(r)
        if g.startswith("DIZILER /"): return False
        if "🟪◆ DİZİ" in g or "🟪◆ DIZI" in g: return False
        return True
    hedef_records = [r for r in hedef_records if kalacak_mi(r)]
    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(u.strip())
    lines = []
    for r in hedef_records: lines.extend(r)
    eklenen_toplam = 0
    for sira, f in enumerate(diziler, 1):
        kurl = str(f.get("kaynak_url","") or "").strip()
        if not kurl: continue
        dizi_adi = str(f.get("dizi_adi","") or "").strip()
        hedef_grup_sabit = str(f.get("hedef_grup","") or "").strip()
        hedef_logo = str(f.get("hedef_logo","") or "").strip()
        f_grup = liste_parse(f.get("filtre_grup_icerir",""))
        f_ad = liste_parse(f.get("filtre_ad_icerir",""))
        f_grup_haric = liste_parse(f.get("filtre_grup_haric",""))
        f_ad_haric = liste_parse(f.get("filtre_ad_haric",""))
        print(f"[DIZI {sira}] {dizi_adi or 'KORE LISTE'} -> {hedef_grup_sabit}")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        eklenen_blok = 0
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if u.strip() in gorulen: continue
            g = grup_bul(r)
            ng = normalize(g); na = normalize(ad)
            haric = False
            for x in f_grup_haric:
                if normalize(x) in ng: haric = True; break
            for x in f_ad_haric:
                if normalize(x) in na: haric = True; break
            if haric: continue
            eslesen_filtre = ""
            if dizi_adi:
                if normalize(dizi_adi) not in na and normalize(dizi_adi) not in ng:
                    if normalize(dizi_adi) not in normalize(kurl):
                        continue
            elif f_grup or f_ad:
                tuttu = False
                for x in f_grup:
                    if normalize(x) in ng or normalize(x) in na:
                        tuttu = True; eslesen_filtre = x.strip(); break
                if not tuttu:
                    for x in f_ad:
                        if normalize(x) in na:
                            tuttu = True; eslesen_filtre = x.strip(); break
                if not tuttu: continue
            else:
                break
            temel, bolum_kodu = dizi_adi_temizle(ad)
            # --- ASIL DEGISIKLIK BURADA ---
            # Nostalji / Kore ana grup + altina dizi adi
            if dizi_adi:
                alt_grup = dizi_adi.upper().strip()
            elif eslesen_filtre:
                alt_grup = eslesen_filtre.upper().strip()
            else:
                alt_grup = temel.upper().strip()
            if hedef_grup_sabit:
                # Zaten sonunda dizi adi varsa tekrar ekleme
                if normalize(alt_grup) in normalize(hedef_grup_sabit):
                    hedef_grup = hedef_grup_sabit
                else:
                    hedef_grup = f"{hedef_grup_sabit} / {alt_grup}"
            else:
                hedef_grup = f"DIZILER / {alt_grup}"
            yeni_ad = bolum_kodu
            yeni = list(r)
            idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
            if idx is not None:
                extinf = yeni[idx]
                if 'group-title="' in extinf:
                    extinf = re.sub(r'group-title="[^"]*"', f'group-title="{hedef_grup}"', extinf)
                else:
                    extinf = extinf.replace("#EXTINF:", f'#EXTINF: group-title="{hedef_grup}"', 1)
                if 'tvg-name="' in extinf:
                    extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{yeni_ad}"', extinf)
                else:
                    extinf = extinf.replace('group-title=', f'tvg-name="{yeni_ad}" group-title=', 1)
                if 'tvg-type="' not in extinf:
                    extinf = extinf.replace('group-title=', 'tvg-type="series" group-title=', 1)
                m_logo = re.search(r'tvg-logo="([^"]*)"', extinf)
                gelen_logo = m_logo.group(1).strip() if m_logo else ""
                if not gelen_logo and hedef_logo:
                    extinf = extinf.replace('group-title=', f'tvg-logo="{hedef_logo}" group-title=', 1)
                extinf = extinf.rsplit(",", 1)[0] + "," + yeni_ad
                yeni[idx] = extinf
            lines.extend(yeni); gorulen.add(u.strip())
            eklenen_blok += 1; eklenen_toplam += 1
        print(f"  [OK] {sira}. blok bitti, eklenen: {eklenen_blok}")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not baslik:
        baslik = ['#EXTM3U']
    final = baslik + lines
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(final)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} - Toplam eklenen dizi: {eklenen_toplam}")

if __name__ == "__main__":
    main()
