# MIRTI68 - SPOR AKTARICI
# Okur: aktarspor.yaml - bozuksa kendi duzeltir
# Yazar: HEDEF_DOSYA + spor.tmp.m3u
import re, os, shutil, urllib.request
try:
    import yaml
except ImportError:
    yaml = None

HEDEF_DOSYA = os.environ.get("HEDEF_DOSYA", "mirti_test.m3u")
SPOR_YAML = "aktarspor.yaml"
TMP_DOSYA = "spor.tmp.m3u"
USER_AGENT = "Mozilla/5.0"
TIMEOUT = 30

DOGRU_YAML = "sporlar: [{kaynak_url: 'https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/spor.m3u', epg_koru: true, sadece_listedekiler: true, hedefler: [{hedef_adi: 'hedef_1', aranacak: ' beIN SPORTS', hedef_grup: '🟪◆ SPOR - BEIN ⭕', hedef_logo: '', ek_kod: ''}, {hedef_adi: 'hedef_2', aranacak: ' S Sport', hedef_grup: '🟪◆ SPOR - S SPORT ⭕', hedef_logo: '', ek_kod: ''}, {hedef_adi: 'hedef_3', aranacak: '', hedef_grup: '', hedef_logo: '', ek_kod: ''}, {hedef_adi: 'hedef_4', aranacak: '', hedef_grup: '', hedef_logo: '', ek_kod: ''}, {hedef_adi: 'hedef_5', aranacak: '', hedef_grup: '', hedef_logo: '', ek_kod: ''}]}]\n"

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

def oku_yaml(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f: f.write(DOGRU_YAML)
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not data.get("sporlar"):
            raise ValueError("sporlar bos")
        return data
    except Exception as e:
        print(f"[UYARI] {path} bozuk: {e}")
        print(f"[DUZELTME] {path} yeniden yaziliyor")
        try: shutil.copy2(path, path + ".bozuk.bak")
        except Exception: pass
        with open(path, "w", encoding="utf-8") as f: f.write(DOGRU_YAML)
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

def main():
    print("MIRTI68 - SPOR BASLADI - aktarspor.yaml okunuyor")
    print(f"[HEDEF] {HEDEF_DOSYA}")
    cfg = oku_yaml(SPOR_YAML)
    sporlar = cfg.get("sporlar", []) or []
    print(f"[BILGI] Spor blok: {len(sporlar)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return
    hedef_records = [r for r in hedef_records if "🟪◆ SPOR" not in grup_bul(r)]
    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(u.strip())
    lines = []
    for r in hedef_records: lines.extend(r)
    spor_lines = ["#EXTM3U"]
    for sira, s in enumerate(sporlar, 1):
        if not isinstance(s, dict): continue
        kurl = str(s.get("kaynak_url","") or "").strip()
        hedefler = s.get("hedefler", []) or []
        if not kurl: continue
        print(f"[SPOR {sira}] {kurl[:60]} - {len(hedefler)} hedef")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if u.strip() in gorulen: continue
            eslesen = None
            for h in hedefler:
                if not isinstance(h, dict): continue
                aranacak = h.get("aranacak", "") or ""
                aranacak_list = aranacak if isinstance(aranacak, list) else [x.strip() for x in str(aranacak).split(",") if x.strip()]
                hedef_grup = str(h.get("hedef_grup","") or "").strip()
                if not hedef_grup: continue
                if not aranacak_list: continue
                for ara in aranacak_list:
                    if normalize(str(ara)) in normalize(ad) or normalize(str(ara)) in normalize(grup_bul(r)):
                        eslesen = h; break
                if eslesen: break
            if not eslesen: continue
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
                oz["group-title"] = hedef_grup
                oz["tvg-name"] = yeni_ad
                gelen_logo = oz.get("tvg-logo","").strip()
                if not gelen_logo and hedef_logo:
                    oz["tvg-logo"] = hedef_logo
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            lines.extend(yeni); spor_lines.extend(yeni); gorulen.add(u.strip())
        print(f"  [OK] {sira}. blok bitti")
    with open(TMP_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(spor_lines)+"\n")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"): lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} + {TMP_DOSYA}")

if __name__ == "__main__":
    main()
