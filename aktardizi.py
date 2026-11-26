# MIRTI68 - DIZI AKTARICI - TiviMate DIZI KATALOGU
# Okur: aktardizi.yaml - filtre yaml'da
# Yazar: HEDEF_DOSYA
# Kural: Hepsi ayni grup, isim hep "Dizi Adi S01E01", tvg-type=series
# Eskiyi silme, icine ekle
import re, os, shutil, urllib.request


HEDEF_DOSYA = "mirti.m3u"
DIZI_YAML = "aktardizi.yaml"
USER_AGENT = "Mozilla/5.0"
TIMEOUT = 30

YEDEK_ADRES = "https://raw.githubusercontent.com/kimbumuratyavuz/capcanli/refs/heads/main/dizi.m3u"
YEDEK_GRUP = "🟪◆ DİZİLER ⭕"

def deger_al(s):
    s = (s or "").strip()
    if len(s) >= 2 and ((s[0] == "'" and s[-1] == "'") or (s[0] == '"' and s[-1] == '"')):
        return s[1:-1]
    return s

def liste_al(v):
    if not v: return []
    if isinstance(v, list):
        out = []
        for x in v: out.extend([y.strip().lower() for y in str(x).split(",") if y.strip()])
        return out
    return [y.strip().lower() for y in str(v).split(",") if y.strip()]

def oku_yaml_toleransli(path):
    bloklar = []
    cur = None
    if not os.path.exists(path):
        return [{"kaynak_url": YEDEK_ADRES, "hedef_grup": YEDEK_GRUP, "hedef_logo": "", "filtre_grup_icerir": "", "filtre_ad_icerir": "", "filtre_grup_haric": "", "filtre_ad_haric": ""}]
    with open(path, encoding="utf-8") as f:
        for ham in f:
            line = ham.strip()
            if not line or line.startswith("#"): continue
            if "kaynak_url" in line:
                if cur: bloklar.append(cur)
                cur = {"kaynak_url": "", "hedef_grup": YEDEK_GRUP, "hedef_logo": "", "filtre_grup_icerir": "", "filtre_ad_icerir": "", "filtre_grup_haric": "", "filtre_ad_haric": ""}
                idx = line.find("kaynak_url:")
                cur["kaynak_url"] = deger_al(line[idx + len("kaynak_url:"):].strip())
                continue
            if cur is None: continue
            if ":" not in line: continue
            k, v = line.split(":", 1)
            k = k.strip().lstrip("- ").strip()
            if k in ("hedef_grup", "hedef_logo", "kaynak_grup", "filtre_grup_icerir", "filtre_ad_icerir", "filtre_grup_haric", "filtre_ad_haric"):
                cur[k] = deger_al(v.strip())
    if cur: bloklar.append(cur)
    if not bloklar:
        return [{"kaynak_url": YEDEK_ADRES, "hedef_grup": YEDEK_GRUP, "hedef_logo": "", "filtre_grup_icerir": "", "filtre_ad_icerir": "", "filtre_grup_haric": "", "filtre_ad_haric": ""}]
    return bloklar

def filtre_gecer(ad, grup, blok):
    ad_l = (ad or "").lower()
    grup_l = (grup or "").lower()
    icerir_grup = liste_al(blok.get("filtre_grup_icerir", ""))
    icerir_ad = liste_al(blok.get("filtre_ad_icerir", ""))
    haric_grup = liste_al(blok.get("filtre_grup_haric", ""))
    haric_ad = liste_al(blok.get("filtre_ad_haric", ""))
    for w in haric_grup:
        if w and w in grup_l: return False
    for w in haric_ad:
        if w and w in ad_l: return False
    if icerir_grup:
        if not any(w and w in grup_l for w in icerir_grup):
            if icerir_ad:
                if not any(w and w in ad_l for w in icerir_ad): return False
            else:
                return False
    if icerir_ad:
        if not any(w and w in ad_l for w in icerir_ad):
            if not icerir_grup: return False
            if not any(w and w in grup_l for w in icerir_grup): return False
    return True

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
        if s and not s.startswith("#") and s.startswith("http"):
            return s
    return ""

def oku_m3u(p):
    if p.startswith("http"):
        req = urllib.request.Request(p, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            metin = r.read().decode("utf-8-sig", errors="ignore")
    else:
        with open(p, "rb") as f:
            metin = f.read().decode("utf-8-sig", errors="ignore")
    satirlar = [x.strip() for x in metin.splitlines() if x.strip()]
    ilk = next((i for i,s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    govde = satirlar[ilk:]
    records, cur = [], []
    for line in govde:
        if line.startswith("#EXTINF:") and cur:
            records.append(cur); cur = []
        cur.append(line)
    if cur: records.append(cur)
    return records

def dizi_adini_duzelt_tivimate(ad):
    # TiviMate icin: "Dizi Adi S01E01" - baska ek yok
    s = (ad or "").strip()
    # Kalite / dil eklerini at: 1080p, 720p, WEB-DL, Altyazi, Dublaj, vb.
    s = re.sub(r'\b(1080p|720p|4K|UHD|FHD|HD|CAM|TS|WEB-DL|BluRay|Dublaj|Dublajlı|Altyazılı|Altyazili|Türkçe|Turkce|Altyazı|Altyazi)\b', ' ', s, flags=re.I)
    s = re.sub(r'[._\-]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # 1. Zaten S01E01 varsa: "Island S1E1" -> "Island S01E01"
    m = re.search(r'\bS(\d{1,2})E(\d{1,3})\b', s, re.I)
    if m:
        dizi = s[:m.start()].strip(" -|")
        dizi = re.sub(r'\s+', ' ', dizi).strip()
        # Dizi adinin sonunda kalan sezon / bolum kelimelerini at
        dizi = re.sub(r'\s*(Sezon|Season|Bölüm|Bolum|Episode).*$', '', dizi, flags=re.I).strip()
        return f"{dizi} S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    # 2. "Sezon 1 - Bolum 1" -> S01E01
    m2 = re.search(r'(.*?)\s*[-–]?\s*Sezon\s*(\d+)\s*[-–]?\s*B[öo]l[üu]m\s*(\d+)', s, re.I)
    if m2:
        dizi = re.sub(r'\s+', ' ', m2.group(1)).strip(" -|")
        return f"{dizi} S{int(m2.group(2)):02d}E{int(m2.group(3)):02d}"
    # 3. "Season 1 Episode 1" -> S01E01
    m3 = re.search(r'(.*?)\s*[-–]?\s*Season\s*(\d+)\s*[-–]?\s*Episode\s*(\d+)', s, re.I)
    if m3:
        dizi = re.sub(r'\s+', ' ', m3.group(1)).strip(" -|")
        return f"{dizi} S{int(m3.group(2)):02d}E{int(m3.group(3)):02d}"
    # 4. Sadece "Bolum 5" -> S01E05
    m4 = re.search(r'(.*?)\s*[-–]?\s*B[öo]l[üu]m\s*(\d+)', s, re.I)
    if m4:
        dizi = re.sub(r'\s+', ' ', m4.group(1)).strip(" -|")
        return f"{dizi} S01E{int(m4.group(2)):02d}"
    return s

def main():
    print("MIRTI68 - DIZI BASLADI - TiviMate KATALOG")
    print(f"[HEDEF] {HEDEF_DOSYA}")
    diziler = oku_yaml_toleransli(DIZI_YAML)
    print(f"[BILGI] Dizi blok: {len(diziler)}")
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} yok")
        return
    hedef_records = oku_m3u(HEDEF_DOSYA)
    eski_sayi = len(hedef_records)
    gorulen = set()
    for r in hedef_records:
        u = kanal_url(r)
        if u: gorulen.add(u.strip())
    lines = []
    for r in hedef_records: lines.extend(r)
    sayi = 0
    atlanan = 0
    zaten_var = 0
    for blok in diziler:
        kurl = str(blok.get("kaynak_url", "") or "").strip()
        if not kurl: continue
        hedef_grup = str(blok.get("hedef_grup", "") or "").strip() or YEDEK_GRUP
        hedef_logo = str(blok.get("hedef_logo", "") or "").strip()
        print(f"[DIZI] {kurl[:60]}")
        try:
            kaynak = oku_m3u(kurl)
        except Exception as e:
            print(f"  [ATLANDI] {e}")
            continue
        for r in kaynak:
            ad = kanal_adi(r); u = kanal_url(r)
            if not u: continue
            if u.strip() in gorulen:
                zaten_var += 1
                continue
            if not filtre_gecer(ad, grup_bul(r), blok):
                atlanan += 1
                continue
            # TiviMate formati
            yeni_ad = dizi_adini_duzelt_tivimate(ad)
            # S01E01 yoksa ekleme, TiviMate kataloguna girmez
            if not re.search(r'\bS\d{2}E\d{2,3}\b', yeni_ad):
                atlanan += 1
                continue
            yeni = list(r)
            idx = next((i for i,x in enumerate(yeni) if x.startswith("#EXTINF:")), None)
            if idx is not None:
                extinf = yeni[idx]
                m = re.match(r"#EXTINF:(-?\d+)", extinf); sure = m.group(1) if m else "-1"
                oz = {}
                for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf): oz[k] = v
                oz["group-title"] = hedef_grup
                oz["tvg-name"] = yeni_ad
                oz["tvg-type"] = "series"
                # TiviMate dizi adi icin tvg-id de dizi adi olsun
                oz["tvg-id"] = yeni_ad
                gelen_logo = oz.get("tvg-logo", "").strip()
                if not gelen_logo and hedef_logo:
                    oz["tvg-logo"] = hedef_logo
                oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
                yeni[idx] = f"#EXTINF:{sure} {oz_str},{yeni_ad}"
            lines.extend(yeni); gorulen.add(u.strip()); sayi += 1
        print(f"  [OK] Yeni: {sayi} - Zaten vardi: {zaten_var} - Atlanan: {atlanan}")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA + ".bak")
    except Exception: pass
    if not lines or not lines[0].strip().startswith("#EXTM3U"):
        lines.insert(0, "#EXTM3U")
    with open(HEDEF_DOSYA, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[KAYDEDILDI] {HEDEF_DOSYA} - Eski: {eski_sayi} - Yeni: {sayi} - Toplam: {eski_sayi + sayi}")

if __name__ == "__main__":
    main()
