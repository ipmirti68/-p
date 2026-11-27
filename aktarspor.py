# MIRTI68 - SPOR AKTARICI - TAM HALI
# Okur: aktarspor.yaml - ne varsa onu aktarir, dosyayi ASLA uzerine yazmaz
# Yazar: spor.tmp.m3u + mirtitv68.m3u
# Kural: 1) Mevcut grup korunur, hicbir kayda dokunulmaz
#        2) Ayni URL ise hic olusturulmaz (.mp4 / ?.mp4 / / farki sayilmaz)
#        3) Ayni grup varsa icine, yoksa benzer grubun altina, o da yoksa en sona
#        4) EPG / logo korunur, yoksa hedef logoya bakilir
import re, os, shutil, urllib.request
try:
    import yaml
except ImportError:
    yaml = None

HEDEF_DOSYA = "mirtitv68.m3u"
SPOR_YAML = "aktarspor.yaml"
TMP_DOSYA = "spor.tmp.m3u"
USER_AGENT = "Mozilla/5.0"
TIMEOUT = 30

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    return re.sub(r"\s+"," ",s).strip()

def norm_grup(s):
    s = normalize(s)
    return re.sub(r"[^a-z0-9]", "", s)

def url_norm(u):
    # Ayni kanal farkli yazilsa da ayni sayilsin
    u = (u or "").strip()
    u = u.replace("?.mp4", "").replace("?ext=.mp4", "").replace("?.m3u8", "")
    if u.endswith(".mp4"):
        u = u[:-4]
    if u.endswith("/"):
        u = u[:-1]
    return u.lower()

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
        print(f"[HATA] {path} yok")
        return {"sporlar": []}
    if yaml is not None:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if data.get("sporlar"):
                print(f"[BILGI] yaml normal okundu, blok: {len(data['sporlar'])}")
                return data
        except Exception as e:
            print(f"[UYARI] yaml normal okunamadi: {e}, girintisiz okuma deneniyor")
    def temiz(v):
        v = v.strip().strip(",")
        if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
            v = v[1:-1]
        return v.strip()
    out = {"sporlar": []}
    cur = None
    cur_hedef = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s == "sporlar:": continue
            if "kaynak_url:" in s:
                if cur: out["sporlar"].append(cur)
                cur = {"kaynak_url": temiz(s.split("kaynak_url:",1)[1]), "epg_koru": True, "sadece_listedekiler": True, "hedefler": []}
                cur_hedef = None
            elif "hedef_adi:" in s and cur is not None:
                cur_hedef = {"hedef_adi": temiz(s.split("hedef_adi:",1)[1]), "aranacak": "", "hedef_grup": "", "hedef_logo": "", "ek_kod": ""}
                cur["hedefler"].append(cur_hedef)
            elif "aranacak:" in s and cur_hedef is not None:
                cur_hedef["aranacak"] = temiz(s.split("aranacak:",1)[1])
            elif "hedef_grup:" in s and cur_hedef is not None:
                cur_hedef["hedef_grup"] = temiz(s.split("hedef_grup:",1)[1])
            elif "hedef_logo:" in s and cur_hedef is not None:
                cur_hedef["hedef_logo"] = temiz(s.split("hedef_logo:",1)[1])
            elif "ek_kod:" in s and cur_hedef is not None:
                cur_hedef["ek_kod"] = temiz(s.split("ek_kod:",1)[1])
            elif "epg_koru:" in s and cur is not None:
                cur["epg_koru"] = "true" in s.lower()
            elif "sadece_listedekiler:" in s and cur is not None:
                cur["sadece_listedekiler"] = "true" in s.lower()
            elif "->" in s and cur is not None:
                sol, sag = s.split("->", 1)
                sol = temiz(sol); sag = temiz(sag)
                if sol and sag:
                    cur["hedefler"].append({"hedef_adi": f"hedef_{len(cur['hedefler'])+1}", "aranacak": sol, "hedef_grup": sag, "hedef_logo": "", "ek_kod": ""})
    if cur: out["sporlar"].append(cur)
    print(f"[BILGI] Girintisiz okundu, blok: {len(out['sporlar'])}")
    for b in out["sporlar"]:
        for h in b["hedefler"]:
            print(f"  - {h['aranacak']} -> {h['hedef_grup']}")
    return out

def benzer_grup_bul(hedef_grup, mevcut_gruplar):
    hedef_n = norm_grup(hedef_grup)
    hedef_kelimeler = set(normalize(hedef_grup).split())
    hedef_kelimeler.discard("spor")
    en_iyi = None
    en_iyi_skor = 0
    for g in mevcut_gruplar:
        if not g: continue
        g_n = norm_grup(g)
        if g_n == hedef_n:
            return g
        skor = 0
        if hedef_n and g_n and (hedef_n in g_n or g_n in hedef_n):
            skor += 10
        g_kelimeler = set(normalize(g).split())
        g_kelimeler.discard("spor")
        ortak = hedef_kelimeler & g_kelimeler
        skor += len(ortak) * 5
        if "spor" in normalize(g) and "spor" in normalize(hedef_grup):
            skor += 1
        if skor > en_iyi_skor and (len(ortak) > 0 or hedef_n in g_n or g_n in hedef_n):
            en_iyi_skor = skor
            en_iyi = g
    return en_iyi

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
    # Mevcut grup korunuyor, mevcut URL'ler normalize edilip kaydediliyor
    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(url_norm(u))
    print(f"[BILGI] Mevcut kayit: {len(hedef_records)} - mevcut URL: {len(gorulen)}")
    yeni_by_grup = {}
    spor_lines = ["#EXTM3U"]
    eklenen_toplam = 0
    atlanan_toplam = 0
    for sira, s in enumerate(sporlar, 1):
        if not isinstance(s, dict): continue
        kurl = str(s.get("kaynak_url","") or "").strip()
        hedefler = s.get("hedefler", []) or []
        if not kurl: continue
        print(f"[SPOR {sira}] {kurl[:60]} - {len(hedefler)} hedef")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        eklenen_blok = 0
        atlanan_blok = 0
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            # AYNI URL ISE HIC OLUSTURMA
            if url_norm(u) in gorulen:
                atlanan_blok += 1; atlanan_toplam += 1
                continue
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
                if not gelen_logo and hedef_logo:
                    oz["tvg-logo"] = hedef_logo
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            yeni_by_grup.setdefault(hedef_grup, []).extend(yeni)
            spor_lines.extend(yeni); gorulen.add(url_norm(u))
            eklenen_blok += 1; eklenen_toplam += 1
        print(f"  [OK] {sira}. blok bitti, eklenen: {eklenen_blok} - atlanan ayni URL: {atlanan_blok}")
    # YERINDE EKLEME + BENZER GRUP - mevcut kayitlara dokunulmaz
    lines = []
    if not baslik or not baslik[0].strip().startswith("#EXTM3U"):
        lines.append("#EXTM3U")
    else:
        lines.extend(baslik)
    mevcut_gruplar = []
    for r in hedef_records:
        g = grup_bul(r)
        if g and g not in mevcut_gruplar:
            mevcut_gruplar.append(g)
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
                mevcut_gruplar.append(g)
                eklenmis.add(g)
                continue
        print(f"[SONA] {g} icin benzer grup yok, en sona eklendi")
        lines.extend(recs)
        eklenmis.add(g)
    with open(TMP_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(spor_lines)+"\n")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"): lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} + {TMP_DOSYA} - Eklenen: {eklenen_toplam} - Atlanan ayni URL: {atlanan_toplam}")

if __name__ == "__main__":
    main()
