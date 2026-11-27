#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MIRTI68 - DIZI - Nostalji icinde dizi grup
# Okur: aktardizi.yaml
# Yazar: mirtitv68.m3u
# KURAL: Var olani SILME, YERINI DEGISTIRME, EPG SILME
# Grup eslestirme: emoji, sembol, bosluk yok sayilir
# Grup adi: "🟪◆ DİZİ - NOSTALJI ⭕ / BIZIMKILER" gibi olur
# Ic isim: Sadece "S01E01" olur, dizi adi tekrar yazilmaz
import re, os, shutil, urllib.request

HEDEF_DOSYA = "mirtitv68.m3u"
DIZI_YAML = "aktardizi.yaml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
TIMEOUT = 30

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    return re.sub(r"\s+"," ",s).strip()

def norm_grup(s):
    # SEMBOL / BOSLUK BAGIMSIZ
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    return re.sub(r'[^a-z0-9çğıöşü]+','',s)

def grup_eslesiyor_mu(kaynak_grup, istenen_grup):
    if not (istenen_grup or "").strip():
        return True
    a = norm_grup(kaynak_grup)
    b = norm_grup(istenen_grup)
    if not a or not b:
        return False
    return a == b or b in a or a in b

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
        v = (v or "").strip()
        if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
            v = v[1:-1]
        return v.strip()
    out = []
    cur = None
    cur_hedef = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s == "diziler:" or s == "?" or s.startswith("? "):
                continue
            if s.startswith("hedef_dosya:"):
                continue
            if "kaynak_url:" in s:
                if cur: out.append(cur)
                cur = {"kaynak_url": temiz(s.split("kaynak_url:",1)[1]), "dizi_adi": "", "hedef_grup": "", "hedef_logo": "", "filtre_grup_icerir": "", "filtre_ad_icerir": "", "filtre_grup_haric": "", "filtre_ad_haric": "", "hedefler": [], "kaynak_grup": "", "kaynak_gruplar": []}
                cur_hedef = None
                continue
            if cur is None:
                continue
            if "hedef_adi:" in s:
                cur_hedef = {"hedef_adi": temiz(s.split("hedef_adi:",1)[1]), "aranacak": "", "hedef_grup": "", "hedef_logo": "", "ek_kod": ""}
                cur["hedefler"].append(cur_hedef)
                continue
            if ":" not in s:
                continue
            k, v = s.split(":", 1)
            k = k.strip(); v = temiz(v)
            if cur_hedef is not None and k in ("aranacak","hedef_grup","hedef_logo","ek_kod"):
                cur_hedef[k] = v
                continue
            if k in ("dizi_adi", "hedef_grup", "hedef_logo", "filtre_grup_icerir", "filtre_ad_icerir", "filtre_grup_haric", "filtre_ad_haric", "kaynak_grup"):
                cur[k] = v
            elif k == "kaynak_gruplar":
                v2 = v.strip("[]")
                cur["kaynak_gruplar"] = [x.strip().strip('"').strip("'") for x in v2.split(",") if x.strip()]
    if cur: out.append(cur)
    print(f"[BILGI] Girintisiz okundu, blok: {len(out)}")
    return out

def extinf_guncelle_dizi(rec, hedef_grup, yeni_ad, hedef_logo):
    # EPG KORU: tvg-id, catchup vs. aynen kalir
    yeni = list(rec)
    idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
    if idx is None: return yeni
    extinf = yeni[idx]
    m = re.match(r"#EXTINF:(-?\d+)", extinf); sure = m.group(1) if m else "-1"
    oz = {}
    for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf): oz[k]=v
    oz["group-title"] = hedef_grup
    oz["tvg-name"] = yeni_ad
    oz["tvg-type"] = "series"
    if not oz.get("tvg-logo","").strip() and hedef_logo:
        oz["tvg-logo"] = hedef_logo
    oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
    yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
    return yeni

def main():
    print("MIRTI68 - DIZI BASLADI")
    if not os.path.exists(DIZI_YAML):
        print(f"[HATA] {DIZI_YAML} yok"); return
    diziler = yaml_oku_guvenli(DIZI_YAML)
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return

    # SILME YOK - hedef dosya aynen korunuyor
    url_index = {}
    isim_index = {}
    for i, r in enumerate(hedef_records):
        u = kanal_url(r)
        if u: url_index[u.strip()] = i
        n = normalize(kanal_adi(r))
        if n and n not in isim_index: isim_index[n] = i

    eklenen_toplam = 0; guncellenen_toplam = 0
    for sira, f in enumerate(diziler, 1):
        kurl = str(f.get("kaynak_url","") or "").strip()
        if not kurl: continue
        dizi_adi = str(f.get("dizi_adi","") or "").strip()
        hedef_grup_sabit = str(f.get("hedef_grup","") or "").strip()
        # Hedef listesi varsa ilk hedefi sabit grup say
        hedefler = f.get("hedefler", []) or []
        if not hedef_grup_sabit and hedefler:
            hedef_grup_sabit = str(hedefler[0].get("hedef_grup","") or "").strip()
        hedef_logo = str(f.get("hedef_logo","") or "").strip()
        if not hedef_logo and hedefler:
            hedef_logo = str(hedefler[0].get("hedef_logo","") or "").strip()
        f_grup = liste_parse(f.get("filtre_grup_icerir",""))
        f_ad = liste_parse(f.get("filtre_ad_icerir",""))
        f_grup_haric = liste_parse(f.get("filtre_grup_haric",""))
        f_ad_haric = liste_parse(f.get("filtre_ad_haric",""))
        # kaynak_grup / kaynak_gruplar destegi de eklendi
        kg = str(f.get("kaynak_grup","") or "").strip()
        kgs = f.get("kaynak_gruplar", []) or []
        if kg and kg not in f_grup:
            f_grup.append(kg)
        for x in kgs:
            if x and x not in f_grup:
                f_grup.append(x)
        print(f"[DIZI {sira}] {dizi_adi or 'KORE LISTE'} -> {hedef_grup_sabit}")
        try: _, kaynak = oku_m3u(kurl)
        except Exception as e: print(f"  [ATLANDI] {e}"); continue
        eklenen_blok = 0; guncellenen_blok = 0
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            g = grup_bul(r)
            ng = normalize(g); na = normalize(ad)
            haric = False
            for x in f_grup_haric:
                # SEMBOL BAGIMSIZ haric kontrolu
                if norm_grup(x) in norm_grup(g) or normalize(x) in ng: haric = True; break
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
                    # SEMBOL BAGIMSIZ: "Nostalji" == "✨ Nostalji ✨"
                    if grup_eslesiyor_mu(g, x) or normalize(x) in ng or normalize(x) in na:
                        tuttu = True; eslesen_filtre = x.strip(); break
                if not tuttu:
                    for x in f_ad:
                        if normalize(x) in na:
                            tuttu = True; eslesen_filtre = x.strip(); break
                if not tuttu: continue
            else:
                # Ne dizi_adi ne filtre var - kaynaktaki her seyi alma, atla
                # Eski kod burada break yapip butun blogu bitiriyordu, onu duzelttik
                continue
            temel, bolum_kodu = dizi_adi_temizle(ad)
            # Nostalji / Kore ana grup + altina dizi adi
            if dizi_adi:
                alt_grup = dizi_adi.upper().strip()
            elif eslesen_filtre:
                alt_grup = eslesen_filtre.upper().strip()
            else:
                alt_grup = temel.upper().strip()
            if hedef_grup_sabit:
                if normalize(alt_grup) in normalize(hedef_grup_sabit) or norm_grup(alt_grup) in norm_grup(hedef_grup_sabit):
                    hedef_grup = hedef_grup_sabit
                else:
                    hedef_grup = f"{hedef_grup_sabit} / {alt_grup}"
            else:
                hedef_grup = f"DIZILER / {alt_grup}"
            # Ic isim sadece bolum kodu, dizi adi tekrar yazilmaz
            # Ornek: Grup = "🟪◆ DİZİ - NOSTALJI ⭕ / BIZIMKILER", Ic = "S01E01"
            yeni_ad = bolum_kodu
            # VAR MI?
            idx = url_index.get(u.strip(), None)
            if idx is None:
                idx = isim_index.get(normalize(ad), None)
            if idx is not None:
                # VAR: Ayni satirda guncelle, YERINI DEGISTIRME, EPG KORU
                eski = hedef_records[idx]
                eski_url = kanal_url(eski)
                hedef_records[idx] = extinf_guncelle_dizi(eski, hedef_grup, yeni_ad, hedef_logo)
                if eski_url.strip() != u.strip():
                    for j, satir in enumerate(hedef_records[idx]):
                        if satir.strip() == eski_url.strip():
                            hedef_records[idx][j] = u; break
                guncellenen_blok += 1; guncellenen_toplam += 1
            else:
                # YOK: Ayni grubun altina ekle, yoksa benzer DIZI grubunun altina
                yeni_rec = extinf_guncelle_dizi(r, hedef_grup, yeni_ad, hedef_logo)
                ekle_pos = None
                for i in range(len(hedef_records)-1, -1, -1):
                    if grup_bul(hedef_records[i]) == hedef_grup:
                        ekle_pos = i + 1; break
                if ekle_pos is None:
                    # Ayni ana grubun altina: "🟪◆ DİZİ - NOSTALJI" icinde herhangi bir dizi grubunun altina
                    ana = hedef_grup_sabit
                    for i in range(len(hedef_records)-1, -1, -1):
                        gg = grup_bul(hedef_records[i])
                        if ana and (ana in gg or norm_grup(ana) in norm_grup(gg)):
                            ekle_pos = i + 1; break
                if ekle_pos is None:
                    for i in range(len(hedef_records)-1, -1, -1):
                        gg = grup_bul(hedef_records[i])
                        if "DİZİ" in gg.upper() or "DIZI" in gg.upper() or gg.startswith("DIZILER"):
                            ekle_pos = i + 1; break
                if ekle_pos is None:
                    ekle_pos = len(hedef_records)
                hedef_records.insert(ekle_pos, yeni_rec)
                url_index = {}; isim_index = {}
                for i, rr in enumerate(hedef_records):
                    uu = kanal_url(rr)
                    if uu: url_index[uu.strip()] = i
                    nn = normalize(kanal_adi(rr))
                    if nn and nn not in isim_index: isim_index[nn] = i
                eklenen_blok += 1; eklenen_toplam += 1
        print(f"  [OK] {sira}. blok bitti, yeni: {eklenen_blok}, guncellenen: {guncellenen_blok}")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    if not baslik:
        baslik = ['#EXTM3U']
    final = list(baslik)
    for r in hedef_records: final.extend(r)
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(final)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} - Yeni: {eklenen_toplam}, Guncellenen: {guncellenen_toplam}, Silinen: 0, EPG korundu")

if __name__ == "__main__":
    main()
