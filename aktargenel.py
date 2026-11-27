#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MIRTI68 - GENEL AKTARICI - AYRI CALISIR - TAM HALI
# Okur: aktargenel.yaml - BOZUK YAML'I DA OKUR, ? satirini atlar
# Yazar: HEDEF_DOSYA + genel.tmp.m3u
# HEDEF_DOSYA yaml'den gelir, yoksa mirti_test.m3u
# 1 url -> 5 hedef, her hedef farkli grup
# KURAL: Var olani SILME, YERINI DEGISTIRME, EPG SILME, BASLIK BOZMA
# - Once ayni grubu ara, varsa icine ekle
# - Yoksa benzer grubun altina ekle
# - Benzer de yoksa en sona ekle
# - Ayni URL varsa ayni satirda guncelle, tekrar olusturma
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

HEDEF_DOSYA = "mirtitv68.m3u"
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

def norm_grup(s):
    return re.sub(r'[^a-z0-9]', '', normalize(s))

def url_norm(u):
    # DUZELTILDI: Ayni kanal farkli yazilsa da ayni sayilsin
    u = (u or "").strip()
    u = u.replace("?.mp4", "").replace("?ext=.mp4", "").replace("?.m3u8", "")
    if u.endswith(".mp4"):
        u = u[:-4]
    if u.endswith("/"):
        u = u[:-1]
    return u.lower()

def benzer_grup_bul(hedef_grup, mevcut_gruplar):
    # DUZELTILDI: Once ayni grup aranir, yoksa benzer grup bulunur
    # Ornek: "🟥🔹 CANLI KAMERA 📹" yoksa "CANLI KAMERA" / "CANLI" grubuna ekler
    hedef_n = norm_grup(hedef_grup)
    hedef_kelimeler = set(normalize(hedef_grup).split())
    en_iyi = None; en_iyi_skor = 0
    for g in mevcut_gruplar:
        if not g: continue
        g_n = norm_grup(g)
        if g_n == hedef_n:
            return g
        skor = 0
        if hedef_n and g_n and (hedef_n in g_n or g_n in hedef_n):
            skor += 10
        g_kelimeler = set(normalize(g).split())
        ortak = hedef_kelimeler & g_kelimeler
        skor += len(ortak) * 5
        if skor > en_iyi_skor and (len(ortak) > 0 or hedef_n in g_n or g_n in hedef_n):
            en_iyi_skor = skor; en_iyi = g
    return en_iyi

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

def _deger_temizle(v):
    v = (v or "").strip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        v = v[1:-1]
    if v in ("?", "null", "Null", "NULL", "~"):
        return ""
    return v.strip()

def _yaml_temizle(metin):
    out = []
    for line in metin.splitlines():
        s = line.strip()
        if s == "?" or s.startswith("? ") or s == "- ?" or s == "-?":
            continue
        m = re.match(r"^(\s*(?:- )?[\w_]+:\s*)(.+)$", line)
        if m and "://" in m.group(2):
            val = m.group(2).strip()
            if not (val.startswith('"') or val.startswith("'") or val.startswith("[")):
                line = m.group(1) + '"' + val.replace('"', '') + '"'
        out.append(line)
    return "\n".join(out)

def _manuel_yaml_parse(metin):
    data = {"hedef_dosya": "", "genel": []}
    cur_genel = None
    cur_hedef = None
    for raw in metin.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        s = raw.strip()
        if s == "?" or s.startswith("? "):
            continue
        if s.startswith("hedef_dosya:"):
            data["hedef_dosya"] = _deger_temizle(s.split(":", 1)[1])
            continue
        if s == "genel:":
            continue
        if s.startswith("- ") and "kaynak_url" in s:
            cur_genel = {"kaynak_url": "", "sadece_listedekiler": True, "kaynak_grup": "", "kaynak_gruplar": [], "hedefler": []}
            data["genel"].append(cur_genel)
            cur_hedef = None
            if "kaynak_url:" in s:
                cur_genel["kaynak_url"] = _deger_temizle(s.split("kaynak_url:", 1)[1])
            continue
        if s.startswith("- ") and cur_genel is not None and "hedef_adi" in s:
            cur_hedef = {"hedef_adi": "", "aranacak": "", "hedef_grup": "", "hedef_logo": "", "ek_kod": ""}
            cur_genel["hedefler"].append(cur_hedef)
            if "hedef_adi:" in s:
                cur_hedef["hedef_adi"] = _deger_temizle(s.split("hedef_adi:", 1)[1])
            continue
        if s.startswith("- ") and cur_genel is not None and cur_hedef is None:
            continue
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        k = k.strip()
        v = _deger_temizle(v)
        if cur_hedef is not None and k in ("hedef_adi", "aranacak", "hedef_grup", "hedef_logo", "ek_kod"):
            cur_hedef[k] = v
        elif cur_genel is not None and k in ("kaynak_url", "kaynak_grup", "sadece_listedekiler"):
            if k == "sadece_listedekiler":
                cur_genel[k] = v.lower() not in ("false", "0", "no", "hayir")
            else:
                cur_genel[k] = v
        elif k == "kaynak_gruplar" and v:
            cur_genel["kaynak_gruplar"] = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
    return data

def oku_yaml(path):
    if not os.path.exists(path):
        print(f"[HATA] {path} yok")
        return {"genel": []}
    with open(path, encoding="utf-8", errors="ignore") as f:
        ham = f.read()
    if yaml is not None:
        try:
            data = yaml.safe_load(ham) or {}
            if data.get("genel"):
                return data
        except Exception as e:
            print(f"[UYARI] yaml.safe_load basarisiz, toleransli okunuyor: {e}")
    temiz = _yaml_temizle(ham)
    if yaml is not None:
        try:
            data = yaml.safe_load(temiz) or {}
            if data.get("genel"):
                print("[BILGI] Girintisiz / toleransli okundu")
                return data
        except Exception as e:
            print(f"[UYARI] Temizli yaml da olmadi: {e}")
    print("[BILGI] Manuel yaml okuyucu kullaniliyor")
    data = _manuel_yaml_parse(ham)
    if not data.get("genel"):
        print(f"[UYARI] {path} icinde genel bos")
    return data

def extinf_guncelle(rec, hedef_grup, yeni_ad, hedef_logo):
    # EPG KORU VAR: eski EXTINF'teki tum ozellikler aynen kalir
    # Sadece group-title degisir, tvg-name tvg-id varsa degisir, logo yoksa eklenir
    yeni = list(rec)
    idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
    if idx is None:
        return yeni
    extinf = yeni[idx]
    m = re.match(r"#EXTINF:(-?\d+)", extinf)
    sure = m.group(1) if m else "-1"
    oz = {}
    for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf):
        oz[k] = v
    oz["group-title"] = hedef_grup
    # DUZELTILDI: tvg-id veya tvg-epg varsa EPG oradan eslesir, tvg-name degisebilir
    # Yoksa EPG tvg-name'den eslesiyor demektir, tvg-name'i ezme
    if oz.get("tvg-id","").strip() or oz.get("tvg-epg","").strip():
        oz["tvg-name"] = yeni_ad
    if not oz.get("tvg-logo","").strip() and hedef_logo:
        oz["tvg-logo"] = hedef_logo
    # EPG: tvg-id, tvg-epg, catchup, catchup-source hepsi oz'da kaldi, silinmedi
    oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
    yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
    return yeni

def main():
    global HEDEF_DOSYA
    print("MIRTI68 - GENEL BASLADI - aktargenel.yaml okunuyor")
    cfg = oku_yaml(GENEL_YAML)
    genel = cfg.get("genel", []) or []
    HEDEF_DOSYA = str(cfg.get("hedef_dosya", "") or "mirti_test.m3u").strip()
    print(f"[HEDEF] {HEDEF_DOSYA}")
    print(f"[BILGI] Genel blok: {len(genel)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok"); return
    try: baslik, hedef_records = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] {e}"); return

    url_index = {}
    for i, r in enumerate(hedef_records):
        u = kanal_url(r)
        if u:
            url_index[url_norm(u)] = i
    isim_index = {}
    for i, r in enumerate(hedef_records):
        n = normalize(kanal_adi(r))
        if n and n not in isim_index:
            isim_index[n] = i

    toplam_guncelle = 0
    toplam_ekle = 0

    for sira, g in enumerate(genel, 1):
        if not isinstance(g, dict): continue
        kurl = str(g.get("kaynak_url","") or "").strip()
        hedefler = g.get("hedefler", []) or []
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
        kg = str(g.get("kaynak_grup","") or "").strip()
        kgs = g.get("kaynak_gruplar", []) or []
        if isinstance(kgs, str): kgs = [kgs]
        kgs_n = [normalize(x) for x in kgs if str(x).strip()]
        kg_n = normalize(kg) if kg else ""
        blok_guncelle = 0
        blok_ekle = 0
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if kgs_n:
                if normalize(grup_bul(r)) not in kgs_n: continue
            elif kg_n:
                if normalize(grup_bul(r)) != kg_n: continue
            eslesen = None
            for h in hedefler:
                if not isinstance(h, dict): continue
                hedef_grup = str(h.get("hedef_grup","") or "").strip()
                if not hedef_grup: continue
                ar_list = aranacak_liste(h.get("aranacak",""))
                if not ar_list:
                    eslesen = h; break
                for ara in ar_list:
                    if normalize(ara) in normalize(ad) or normalize(ara) in normalize(grup_bul(r)):
                        eslesen = h; break
                if eslesen: break
            if not eslesen:
                continue
            hedef_grup = str(eslesen.get("hedef_grup","") or "").strip()
            hedef_logo = str(eslesen.get("hedef_logo","") or "").strip()
            ek_kod = str(eslesen.get("ek_kod","") or "").strip()
            yeni_ad = ad
            if ek_kod and not yeni_ad.endswith(ek_kod):
                yeni_ad = f"{yeni_ad} {ek_kod}"

            # 1. VAR MI? URL ile bak, yoksa isimle bak
            idx = url_index.get(url_norm(u), None)
            if idx is None:
                idx = isim_index.get(normalize(ad), None)
            if idx is not None:
                eski = hedef_records[idx]
                eski_url = kanal_url(eski)
                hedef_records[idx] = extinf_guncelle(eski, hedef_grup, yeni_ad, hedef_logo)
                if url_norm(eski_url) != url_norm(u):
                    for j, satir in enumerate(hedef_records[idx]):
                        if satir.strip() == eski_url.strip():
                            hedef_records[idx][j] = u
                            break
                blok_guncelle += 1
            else:
                # 2. YOK: Once AYNI grubu ara, sonra BENZER grubu ara, sonra en sona
                yeni_rec = extinf_guncelle(r, hedef_grup, yeni_ad, hedef_logo)
                mevcut_gruplar = []
                for rr in hedef_records:
                    gg = grup_bul(rr)
                    if gg and gg not in mevcut_gruplar: mevcut_gruplar.append(gg)
                ekle_pos = None
                # Ayni grup
                for i in range(len(hedef_records)-1, -1, -1):
                    if grup_bul(hedef_records[i]) == hedef_grup:
                        ekle_pos = i + 1
                        print(f"  [AYNI GRUP] {hedef_grup} icine eklendi: {yeni_ad}")
                        break
                # Benzer grup
                if ekle_pos is None:
                    benzer = benzer_grup_bul(hedef_grup, mevcut_gruplar)
                    if benzer:
                        for i in range(len(hedef_records)-1, -1, -1):
                            if grup_bul(hedef_records[i]) == benzer:
                                ekle_pos = i + 1
                                print(f"  [BENZER GRUP] {hedef_grup} yok, benzer bulundu: {benzer} -> altina eklendi: {yeni_ad}")
                                break
                # Hicbiri yoksa en sona
                if ekle_pos is None:
                    ekle_pos = len(hedef_records)
                    print(f"  [SONA] {hedef_grup} icin benzer grup yok, en sona eklendi: {yeni_ad}")
                hedef_records.insert(ekle_pos, yeni_rec)
                url_index = {}
                isim_index = {}
                for i, rr in enumerate(hedef_records):
                    uu = kanal_url(rr)
                    if uu: url_index[url_norm(uu)] = i
                    nn = normalize(kanal_adi(rr))
                    if nn and nn not in isim_index: isim_index[nn] = i
                blok_ekle += 1
        print(f"  [OK] {sira}. blok bitti, guncellenen: {blok_guncelle}, yeni eklenen: {blok_ekle}")
        toplam_guncelle += blok_guncelle
        toplam_ekle += blok_ekle

    with open(TMP_DOSYA,"w",encoding="utf-8",newline="") as f:
        f.write("#EXTM3U\n")
        for r in hedef_records:
            if grup_bul(r).startswith("🟨◆") or grup_bul(r).startswith("🟥🔹"):
                f.write("\n".join(r)+"\n")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak")
    except Exception: pass
    lines = []
    if not baslik or not baslik[0].strip().startswith("#EXTM3U"):
        lines.append("#EXTM3U")
    else:
        lines.extend(baslik)
    for r in hedef_records: lines.extend(r)
    with open(HEDEF_DOSYA,"w",encoding="utf-8",newline="") as f: f.write("\n".join(lines)+"\n")
    print(f"\n[KAYDEDILDI] {HEDEF_DOSYA} + {TMP_DOSYA} - Guncellenen: {toplam_guncelle}, Yeni: {toplam_ekle}, Silinen: 0, Yer degisen: 0, EPG korundu")

if __name__ == "__main__":
    main()
