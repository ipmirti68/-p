# MIRTI68 - DIZI AKTARICI - EPG korur, ust tarafa dokunmaz
# Okur: aktardizi.yaml
# Yazar: mirti.m3u (ust baslik aynen kalir)
import re, os, shutil, urllib.request, urllib.parse

HEDEF_DOSYA = "mirti.m3u"
DIZI_YAML = "aktardizi.yaml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
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
    # "Dizi Adi S01E01 - Bolum" -> ("Dizi Adi", 1, 1)
    s = (ad or "").strip()
    m = re.search(r'[Ss](\d{1,2})[Ee](\d{1,3})', s)
    if not m:
        m2 = re.search(r'Sezon\s*(\d+).*?B[oö]l[uü]m\s*(\d+)', s, re.I)
        if m2: return re.sub(r'Sezon.*', '', s, flags=re.I).strip(" -|"), int(m2.group(1)), int(m2.group(2))
        return s, None, None
    sezon, bolum = int(m.group(1)), int(m.group(2))
    temel = s[:m.start()].strip(" -|_.,")
    temel = re.sub(r'\s+', ' ', temel).strip()
    return temel, sezon, bolum

def yaml_oku_guvenli(path):
    def temiz(v):
        v = v.strip()
        if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
            v = v[1:-1]
        return v.strip()
    out = {"diziler": []}
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s == "diziler:": continue
            if "kaynak_url:" in s:
                if cur: out["diziler"].append(cur)
                v = s.split("kaynak_url:",1)[1]
                cur = {"kaynak_url": temiz(v), "kaynak_grup": "", "hedef_grup": "", "hedefler": []}
            elif "kaynak_grup:" in s and cur is not None:
                v = s.split("kaynak_grup:",1)[1]
                cur["kaynak_grup"] = temiz(v)
            elif "hedef_grup:" in s and cur is not None:
                v = s.split("hedef_grup:",1)[1]
                cur["hedef_grup"] = temiz(v)
                cur["hedefler"] = [{"hedef_adi": "hedef_1", "aranacak": "", "hedef_grup": cur["hedef_grup"], "hedef_logo": "", "ek_kod": ""}]
            elif "aranacak:" in s and cur is not None:
                # aranacak varsa, hedefler icine koy
                v = s.split("aranacak:",1)[1]
                if cur["hedefler"]:
                    cur["hedefler"][0]["aranacak"] = temiz(v)
    if cur: out["diziler"].append(cur)
    print(f"[BILGI] Girintisiz okundu, blok: {len(out['diziler'])}")
    for b in out["diziler"]:
        print(f"  - {b['kaynak_grup']} -> {b['hedef_grup']}")
    return out

def main():
    print("MIRTI68 - DIZI BASLADI - aktardizi.yaml okunuyor")
    if not os.path.exists(DIZI_YAML):
        print(f"[HATA] {DIZI_YAML} yok"); return
    cfg = yaml_oku_guvenli(DIZI_YAML)
    diziler = cfg.get("diziler", []) or []
    print(f"[BILGI] Dizi blok: {len(diziler)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    # EPG DUZELTILDI: Basligi oku, aynen sakla, hic degistirme
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return
    print(f"[EPG] Ust baslik korundu: {baslik}")
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
        if not isinstance(f, dict): continue
        kurl = str(f.get("kaynak_url","") or "").strip()
        if not kurl: continue
        hedefler = f.get("hedefler", []) or []
        if not hedefler and f.get("hedef_grup"):
            hedefler = [{"hedef_adi": "hedef_1", "aranacak": f.get("aranacak",""), "hedef_grup": f.get("hedef_grup",""), "hedef_logo": f.get("hedef_logo",""), "ek_kod": f.get("ek_kod","")}]
        print(f"[DIZI {sira}] {kurl[:60]}")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        kg = str(f.get("kaynak_grup","") or "").strip()
        eklenen_blok = 0
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if u.strip() in gorulen: continue
            g = grup_bul(r)
            if kg:
                if normalize(kg) not in normalize(g) and normalize(g) not in normalize(kg): continue
            eslesen = None
            for h in hedefler:
                if not isinstance(h, dict): continue
                hg = str(h.get("hedef_grup","") or "").strip()
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
            temel, sezon, bolum = dizi_adi_temizle(ad)
            if sezon is not None and bolum is not None:
                yeni_ad = f"{temel} S{sezon:02d}E{bolum:02d}"
            else:
                yeni_ad = temel
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
                gelen_logo = oz.get("tvg-logo","").strip()
                if not gelen_logo and hedef_logo: oz["tvg-logo"] = hedef_logo
                oz["tvg-type"] = "series"
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            lines.extend(yeni); gorulen.add(u.strip())
            eklenen_blok += 1; eklenen_toplam += 1
        print(f"  [OK] {sira}. blok bitti, eklenen: {eklenen_blok}")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    # EPG DUZELTILDI: Basligi aynen geri yaz, yeni #EXTM3U uydurma
    if not baslik:
        baslik = ['#EXTM3U']
    final = baslik + lines
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(final)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} - Toplam eklenen dizi: {eklenen_toplam}")
    print(f"[EPG] Ust baslik aynen korundu, degistirilmedi")

if __name__ == "__main__":
    main()
