# MIRTI68 - GENEL AKTARICI - AYRI CALISIR
# Okur: aktargenel.yaml
# Yazar: genel.tmp.m3u + mirti68.m3u icindeki genel bolumunu gunceller
# 1 url -> 5 hedef, her hedef farkli grup
# aranacak: "a, b, c" seklinde virgullu, py listeye cevirir
# kaynak_grup / kaynak_gruplar varsa once ona gore suzer
# Logo: Kendi logosu varsa onu kullan, yoksa hedef logosu
# ek_kod: Kanal adinin sonuna eklenir, zaten varsa 2. kez eklenmez
# Ayni url varsa eklemez, EPG korunur, sadece listedekiler guncellenir
import re, os, shutil, urllib.request
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
GENEL_YAML = "aktargenel.yaml"
TMP_DOSYA = "genel.tmp.m3u"
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

def aranacak_liste(v):
    if not v: return []
    if isinstance(v, list):
        out = []
        for x in v: out.extend([y.strip() for y in str(x).split(",") if y.strip()])
        return out
    return [y.strip() for y in str(v).split(",") if y.strip()]

def main():
    print("MIRTI68 - GENEL BASLADI - aktargenel.yaml okunuyor")
    if not os.path.exists(GENEL_YAML):
        print(f"[HATA] {GENEL_YAML} yok"); return
    with open(GENEL_YAML, encoding="utf-8") as f: cfg = yaml.safe_load(f) or {}
    genel = cfg.get("genel", []) or []
    print(f"[BILGI] Genel blok: {len(genel)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return

    # Eski genel gruplarini temizle: dizi / spor / film grubuna dokunma
    def kalacak_mi(r):
        g = grup_bul(r)
        if g.startswith("🟨◆") or g.startswith("🟥🔹"): return False
        return True
    hedef_records = [r for r in hedef_records if kalacak_mi(r)]

    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(u.strip())
    lines = []
    for r in hedef_records: lines.extend(r)
    genel_lines = ["#EXTM3U"]

    for sira, g in enumerate(genel, 1):
        if not isinstance(g, dict): continue
        kurl = str(g.get("kaynak_url","") or "").strip()
        hedefler = g.get("hedefler", []) or []
        # Eski tek hedef formati varsa onu hedef_1 say
        if not hedefler and g.get("hedef_grup"):
            hedefler = [{
                "hedef_adi": "hedef_1",
                "aranacak": g.get("aranacak",""),
                "hedef_grup": g.get("hedef_grup",""),
                "hedef_logo": g.get("hedef_logo",""),
                "ek_kod": g.get("ek_kod",""),
            }]
        if not kurl: continue
        print(f"[GENEL {sira}] {kurl[:60]} - {len(hedefler)} hedef")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        sadece = bool(g.get("sadece_listedekiler", True))
        # kaynak_grup / kaynak_gruplar filtresi
        kg = str(g.get("kaynak_grup","") or "").strip()
        kgs = g.get("kaynak_gruplar", []) or []
        if isinstance(kgs, str): kgs = [kgs]
        kgs_n = [normalize(x) for x in kgs if str(x).strip()]
        kg_n = normalize(kg) if kg else ""
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if u.strip() in gorulen: continue
            # Kaynak grup filtresi varsa once ona bak
            if kgs_n:
                if normalize(grup_bul(r)) not in kgs_n: continue
            elif kg_n:
                if normalize(grup_bul(r)) != kg_n: continue
            # Hangi hedefe uyuyor?
            eslesen = None
            for h in hedefler:
                if not isinstance(h, dict): continue
                hedef_grup = str(h.get("hedef_grup","") or "").strip()
                if not hedef_grup: continue
                ar_list = aranacak_liste(h.get("aranacak",""))
                # aranacak bos ise: kaynak_grup filtresiyle gelen tumunu al
                if not ar_list:
                    eslesen = h; break
                for ara in ar_list:
                    if normalize(ara) in normalize(ad) or normalize(ara) in normalize(grup_bul(r)):
                        eslesen = h; break
                if eslesen: break
            if not eslesen:
                if sadece: continue
                else: continue
            hedef_grup = str(eslesen.get("hedef_grup","") or "").strip()
            hedef_logo = str(eslesen.get("hedef_logo","") or "").strip()
            ek_kod = str(eslesen.get("ek_kod","") or "").strip()
            yeni_ad = ad
            if ek_kod and not yeni_ad.endswith(ek_kod):
                yeni_ad = f"{yeni_ad} {ek_kod}"
            yeni = list(r)
            idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
            if idx is not None:
                extinf = yeni[idx]
                m = re.match(r"#EXTINF:(-?\d+)", extinf); sure = m.group(1) if m else "-1"
                oz = {}
                for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf): oz[k]=v
                # EPG KORU: tvg-id, catchup vs silinmez
                oz["group-title"] = hedef_grup
                oz["tvg-name"] = yeni_ad
                gelen_logo = oz.get("tvg-logo","").strip()
                if not gelen_logo and hedef_logo:
                    oz["tvg-logo"] = hedef_logo
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            lines.extend(yeni); genel_lines.extend(yeni); gorulen.add(u.strip())
        print(f"  [OK] {sira}. blok bitti")

    with open(TMP_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(genel_lines)+"\n")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"): lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} + {TMP_DOSYA} - Ayni url eklenmedi, liste cogalmadi")

if __name__ == "__main__":
    main()
