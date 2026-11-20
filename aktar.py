# MIRTI68 - TEK AKTARICI
import re, os, shutil, urllib.request, urllib.error, socket
HEDEF_DOSYA = "mirti68.m3u"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
TIMEOUT = 30

AKTARIMLAR = [
    {
        "kaynak_url": "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u",
        "kaynak_gruplar": ["IMDb Top Rated","YERLI FILM","KEMAL SUNAL","KORKU","WESTERN","YeniEklenenler","2026","2025","2023 2024","2021 2022","2019 2020","2017 2018","2015 2016","2013 2014","2011 2012","2001 2010"],
        "kaynak_grup": "", 
        "aranacak": "", 
        "hedef_grup": "", 
        "hedef_logo": "", 
        "ek_kod": "⭕",
        "grup_onek": False, "sinema_modu": True,
    },
    {
        "kaynak_url": "https://raw.githubusercontent.com/Adnan4161/TvDizi/refs/heads/main/Tv%20Dizi.m3u",
        "kaynak_grup": "",
        "aranacak": "", 
        "hedef_grup": "🟪◆ GÜNCEL DİZİLER ⭕",
        "hedef_logo": "", 
        "ek_kod": "⭕", 
        "grup_onek": True,
    },
       {
        "kaynak_url": "http://190502.tomtv.eu/get.php?username=GokmenS947&password=5rr53m3b8c&type=m3u_plus&output=ts",
        "kaynak_grup": "GUNCEL DiZiLER SON BOLUM",
        "aranacak": "",
        "hedef_grup": "🟪◆ GÜNCEL DİZİLER ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },
    {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | ULUSAL",
        "aranacak": "trt1, star tv, kanal d, show tv, atv, now, beyaz tv, fx, kanal 7, tv 8",
        "hedef_grup": "🟨◆ ULUSAL ᴴᴰ⁺ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

  {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/livetv/dc73a3a52d0d5be4ba926d7b40a759fb9d5777a3/tv247tr.m3u",
        "kaynak_grup": "Spor-Avva",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Avva",
    },

    
    {
        "kaynak_url": "https://raw.githubusercontent.com/smtv62/atomspor/refs/heads/main/atom.m3u",
        "kaynak_grup": "Atom-Panel",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "https://i.imgur.com/71TSn0Q.jpeg",
        "ek_kod": "⭕ Atom",
    },
  {
        "kaynak_url": "https://raw.githubusercontent.com/smtv62/smtv/refs/heads/main/turkce.m3u",
        "kaynak_grup": "",
        "aranacak": "trt1, atv, show, kanal d, star, now, kanal7. tv8",
        "hedef_grup": "🟨◆ ULUSAL ᴴᴰ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },
  
    {
        "kaynak_url": "https://raw.githubusercontent.com/mzabidin80/OTT_Navigator_Indonesia_Korea_China_Movies.m3u/refs/heads/main/OTT_Navigator_V2_Indonesia_Korea_China_Movies_Knowledge.m3u",
        "kaynak_grup": "",
        "aranacak": "Korea",
        "hedef_grup": "🟨◆ YABANCI 🇰🇷⭕",
        "hedef_logo": "https://upload.wikimedia.org/wikipedia/commons/0/09/Flag_of_South_Korea.svg?utm_source=tr.wikipedia.org&utm_campaign=index&utm_content=original",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/mehmetey03/METV/refs/heads/main/mahsun.m3u",
        "kaynak_grup": "",
        "aranacak": "beIN Sports",
        "hedef_grup": "🟩◆  beIN SPORTS 🖥",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

      
    {
        "kaynak_url": "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "Diziler | Prison Break | Prison Break",
        "aranacak": "",
        "hedef_grup": "🟪◆ DİZİLER - PRİSON BREAK ⭕",
        "hedef_logo": "",
        "ek_kod": "",
    },

    {
        "kaynak_url": "http://190502.tomtv.eu:80/get.php?username=MustafaozdemR7808&password=z189b8mv2r&type=m3u_plus&output=ts",
        "kaynak_grup": "SONVIZYON FILMLER",
        "aranacak": "",
        "hedef_grup": "🟪◆ GÜNCEL FİLİMLER ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },

    {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | 7/24 DIZI",
        "aranacak": "",
        "hedef_grup": "🟪◆  7/24 DİZİ 📺⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },



    {
        "kaynak_url": "https://79.76.50.223/get.php?username=ViP&password=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "Yerel / 🔴 SPOR",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "0️⃣⭕",
    },

    {
        "kaynak_url": "http://31.43.191.142:8880/get.php?username=191703089055131&password=01703089055686&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | SPORT",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "1️⃣⭕",
    },

    {
        "kaynak_url": "http://ruzgarplayer.site:8080/get.php?username=KH6Rn39q4WpL&password=bnzSVts6Lner&type=m3u_plus&output=tsrd=GaraveliForum&type=m3u_plus&output=m3u8",
        "kaynak_grup": "⫸TR SUPER LİG 1⫷",
        "aranacak": "",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "2️⃣⭕",
    },

    {
        "kaynak_url": "http://190502.tomtv.eu/get.php?username=GokmenS947&password=5rr53m3b8c&type=m3u_plus&output=ts",
        "kaynak_grup": "TR-SPOR",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "3️⃣⭕",
    },

    {
        "kaynak_url": "https://raw.githubusercontent.com/kadirsener1/livetv/dc73a3a52d0d5be4ba926d7b40a759fb9d5777a3/tv247tr.m3u",
        "kaynak_grup": "Spor Vavoo",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "4️⃣⭕",
    },
     
    {
        "kaynak_url": "https://ekmek82.shop/get.php?username=adnan678&password=uBjabktvQP&type=m3u_plus&output=ts",
        "kaynak_grup": "TR • BeIN SPORTS",
        "aranacak": "beIN SPORTS",
        "hedef_grup": "🟩◆  beIN SPORTS 📡⭕",
        "hedef_logo": "https://i.imgur.com/TgW5452.png",
        "ek_kod": "5️⃣⭕",
    },

     {
        "kaynak_url": "http://mekantv56.win/get.php?username=akifalioglu33&password=33akifalioglu&type=m3u_plus&output=ts",
        "kaynak_grup": "TR | TABii",
        "aranacak": "",
        "hedef_grup": "🟪◆  TABİİ DİZİLERİ ⭕",
        "hedef_logo": "",
        "ek_kod": "⭕",
    },
     

    
]

def normalize(s):
    s = (s or "").lower().strip()
    cevir = {"ı":"i","İ":"i","i":"i","ö":"o","Ö":"o","ü":"u","Ü":"u","ç":"c","Ç":"c","ğ":"g","Ğ":"g","ş":"s","Ş":"s"}
    s = "".join(cevir.get(c,c) for c in s)
    s = s.replace("|"," ").replace("-"," ").replace("_"," ")
    s = re.sub(r"\s+"," ",s).strip()
    return s

SINEMA_WANTED_RAW = ["IMDb Top Rated","YERLI FILM","KEMAL SUNAL","KORKU","WESTERN","YeniEklenenler","2026","2025","2023 2024","2021 2022","2019 2020","2017 2018","2015 2016","2013 2014","2011 2012","2001 2010"]
def norm_sinema(s):
    return re.sub(r'[^a-z0-9çğıöşü]+','',(s or "").lower())
SINEMA_WANTED = {norm_sinema(x): x for x in SINEMA_WANTED_RAW}
SINEMA_EXCLUDED = ["adam sandler","clint eastwood","sylvester stallone","jackie chan","nicolas cage","steven seagal","jason statham","seri","dizi","series","sezon","season","episode","bölüm","bolum","s01e","s02e","s03e"]
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
            if 'tvg-name="' in ad or 'group-title="' in ad or ('"' in ad and 'tvg-' in ad):
                m = re.search(r'tvg-name="([^"]*)"', ad)
                if m: return m.group(1).strip()
                ad = re.sub(r'.*group-title="[^"]*",','',ad).strip()
                ad = ad.split('"')[-1].strip()
            return ad
    return ""
def temiz_isim(ad):
    ad = (ad or "").lower().strip()
    for e in ["⭕ atom","⭕","atom"]:
        if ad.endswith(e): ad = ad[:-len(e)].strip()
    ad = re.split(r'\s*-\s*\d+\.?\s*bölüm', ad)[0]
    ad = re.split(r'\s*-\s*\d+\.?\s*bolum', ad)[0]
    ad = re.split(r'\s*-\s*\d{4}-\d{2}-\d{2}', ad)[0]
    return ad.strip().rstrip("-").strip()
def grup_baslangici(g):
    g = (g or "").strip()
    if not g: return ""
    if "◆" in g: return g[:g.find("◆")+1].strip()
    return g.split()[0] if g.split() else ""
def grup_eslesiyor_mu(a,b):
    if not b: return True
    if not normalize(a): return False
    return normalize(a)==normalize(b)
def oku_m3u(p):
    if p.startswith("http"):
        req = urllib.request.Request(p, headers={"User-Agent":USER_AGENT,"Accept":"*/*","Connection":"close"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r: metin = r.read().decode("utf-8-sig", errors="ignore")
    else:
        if not os.path.exists(p): raise FileNotFoundError(p)
        with open(p,"rb") as f: metin = f.read().decode("utf-8-sig", errors="ignore")
    newline = "\r\n" if "\r\n" in metin else "\n"
    satirlar = metin.splitlines()
    ilk = next((i for i,s in enumerate(satirlar) if s.startswith("#EXTINF:")), len(satirlar))
    baslik, govde = satirlar[:ilk], satirlar[ilk:]
    records, cur = [], []
    for line in govde:
        if line.startswith("#EXTINF:") and cur: records.append(cur); cur=[]
        cur.append(line)
    if cur: records.append(cur)
    return baslik, records, newline, "utf-8"

def hedefe_uyarla(rec,cfg):
    yeni_rec = list(rec)
    idx = next((i for i,x in enumerate(yeni_rec) if x.startswith("#EXTINF:")), None)
    if idx is None: return yeni_rec
    extinf = yeni_rec[idx]
    m = re.match(r"#EXTINF:(-?\d+)", extinf); sure = m.group(1) if m else "-1"
    ad = extinf.rsplit(",",1)[-1].strip() if "," in extinf else ""
    # Bozuk satırda adın içinde tvg-name kalmışsa temizle
    if 'tvg-name="' in ad:
        mm = re.search(r'tvg-name="([^"]*)"', ad)
        if mm: ad = mm.group(1).strip()
    oz = {}
    for k,v in re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', extinf): oz[k]=v
    if cfg.get("sinema_modu"):
        _g = grup_bul(rec).strip()
        _clean = SINEMA_WANTED.get(norm_sinema(_g), _g)
        _clean = re.sub(r"\s+"," ",_clean).strip()
        if "FILM" not in _clean.upper(): _clean = f"FILM - {_clean}"
        cfg = dict(cfg); cfg["hedef_grup"] = f"🟪◆ {_clean} ⭕"; cfg["_sinema_tvg_type"]=True
    if cfg.get("grup_onek"):
        _g = grup_bul(rec).strip()
        if _g and not ad.lower().startswith(_g.lower()): ad = f"{_g} - {ad}"
    if cfg.get("hedef_grup"): oz["group-title"]=cfg["hedef_grup"]
    logo = cfg.get("hedef_logo","")
    if logo: oz["tvg-logo"]=logo
    ek = (cfg.get("ek_kod") or "").strip()
    if ek and "=" not in ek and not ad.endswith(ek) and ek not in ad: ad = f"{ad} {ek}"
    if "tvg-name" in oz: oz["tvg-name"]=ad
    if cfg.get("_sinema_tvg_type"): oz["tvg-type"]="movie"
    oz_str = " ".join(f'{k}="{v}"' for k,v in oz.items())
    yeni_rec[idx] = f"#EXTINF:{sure} {oz_str},{ad}"
    if cfg.get("sinema_modu"):
        for i,l in enumerate(yeni_rec):
            if l.strip().startswith(("http://","https://")): yeni_rec[i]=sinema_fix_url(l.strip())
    return yeni_rec

def aranacak_parcala(raw):
    s=(raw or "").strip()
    if not s: return []
    s_low=s.lower()
    for ik in ["kanal d","kanal 7","show tv","star tv","beyaz tv","tv 8","tv 8.5","a2 tv","trt 1"]:
        if ik in s_low: s_low=s_low.replace(ik, ik.replace(" ","_"))
    if any(x in s_low for x in [",",";","|","\n"]): par=re.split(r"[,;|\n]+", s_low)
    else: par=s_low.split()
    return [normalize(p.strip().replace("_"," ")) for p in par if p.strip()]

def kanal_kok(ad_n):
    # "tr:atv hd" -> "atv", "tr:tv 8.5 hd" -> "tv 8.5", "tr:atv avrupa hd" -> "atv avrupa"
    a = ad_n.strip()
    a = re.sub(r"^tr[:\s\-]+","",a)
    a = re.sub(r"^tr\s+","",a)
    a = re.sub(r"\s+(hd|hq|fhd|4k)$","",a)
    a = re.sub(r"\s+\[yedek\]$","",a)
    a = re.sub(r"\s+yedek$","",a)
    return a.strip()

def kaynak_sec(records,cfg):
    liste = aranacak_parcala(cfg.get("aranacak",""))
    kg = (cfg.get("kaynak_grup","") or "").strip()
    kgs = cfg.get("kaynak_gruplar",[]) or []
    if cfg.get("sinema_modu"): kgs_n=[norm_sinema(g) for g in kgs if g.strip()]
    else: kgs_n=[normalize(g) for g in kgs if g.strip()]
    out=[]
    for r in records:
        g=grup_bul(r)
        if kgs_n:
            _n = norm_sinema(g) if cfg.get("sinema_modu") else normalize(g)
            if _n not in kgs_n: continue
        elif kg and not grup_eslesiyor_mu(g,kg): continue
        if cfg.get("sinema_modu") and (sinema_excluded(g) or sinema_excluded(kanal_adi(r))): continue
        if liste:
            kok = kanal_kok(normalize(kanal_adi(r)))
            kok_nospace = kok.replace(" ","")
            ok=False
            for ana in liste:
                if kok==ana or kok_nospace==ana.replace(" ",""): ok=True; break
            if not ok: continue
        if "bilgilendirme" in kanal_adi(r).lower(): continue
        out.append(hedefe_uyarla(r,cfg))
    return out

def grubu_birlestir(hedef_records, secilen, hedef_grup):
    gelen={}
    for r in secilen:
        isim=temiz_isim(kanal_adi(r))
        if isim: gelen[isim]=r
    yeni=[]; gor=set(); son=None
    for r in hedef_records:
        if grup_bul(r)!=hedef_grup: yeni.append(r); continue
        isim=temiz_isim(kanal_adi(r))
        if isim in gelen: yeni.append(gelen[isim]); gor.add(isim); print(f"    [REVİZE] {kanal_adi(r)}")
        else: yeni.append(r); print(f"    [KORUNDU] {kanal_adi(r)}")
        son=len(yeni)
    ek=[]
    for isim,rec in gelen.items():
        if isim not in gor: ek.append(rec); print(f"    [EKLENDİ] {kanal_adi(rec)}")
    if ek:
        if son is not None: yeni[son:son]=ek
        else: yeni.extend(ek)
    return yeni
def benzer_bitis(hedef_records, bas):
    idx=[i for i,r in enumerate(hedef_records) if grup_baslangici(grup_bul(r))==bas and grup_bul(r)]
    return max(idx) if idx else None

def main():
    if not os.path.exists(HEDEF_DOSYA):
        print(f"[HATA] {HEDEF_DOSYA} bulunamadı!"); return
    print("\n====================================\n MIRTI68 - TEK AKTARICI BAŞLADI\n HATALI URL ATLANACAK\n====================================")
    try: baslik, hedef_records, newline, enc = oku_m3u(HEDEF_DOSYA)
    except Exception as e: print(f"[HATA] Hedef dosya okunamadı: {e}"); return
    basarili=hatali=eklenen_toplam=0
    hatali_list=[]
    def hata_ekle(cfg,sebep):
        hatali_list.append({"hedef_grup":cfg.get("hedef_grup","?"),"kaynak_grup":cfg.get("kaynak_grup",""),"url":cfg.get("kaynak_url","").split("?")[0],"sebep":str(sebep)})
    for sira,cfg in enumerate(AKTARIMLAR,1):
        url=cfg["kaynak_url"]
        print(f"\n[{sira}/{len(AKTARIMLAR)}] KAYNAK:\n{url.split('?')[0]}\nHEDEF GRUP: {cfg['hedef_grup']}")
        if cfg.get("kaynak_grup"): print(f"ARANAN KAYNAK GRUP: {cfg['kaynak_grup']}")
        try: _,kaynak_records,_,_ = oku_m3u(url)
        except urllib.error.HTTPError as e: hatali+=1; hata_ekle(cfg,f"HTTP {e.code} - {e.reason}"); print(f"  [ATLANDI] HTTP {e.code}"); continue
        except urllib.error.URLError as e: hatali+=1; hata_ekle(cfg,f"Bağlantı hatası: {e.reason}"); print(f"  [ATLANDI] {e.reason}"); continue
        except (TimeoutError,socket.timeout) as e: hatali+=1; hata_ekle(cfg,f"Zaman aşımı: {e}"); print(f"  [ATLANDI] Zaman aşımı"); continue
        except Exception as e: hatali+=1; hata_ekle(cfg,f"{type(e).__name__}: {e}"); print(f"  [ATLANDI] {e}"); continue
        if not kaynak_records: hatali+=1; hata_ekle(cfg,"Kaynakta M3U kaydı bulunamadı"); print("  [ATLANDI] Boş kaynak"); continue
        if cfg.get("kaynak_grup"):
            gruplar=sorted(set(grup_bul(r) for r in kaynak_records if grup_bul(r)))
            print(f"  [DEBUG] Kaynakta {len(gruplar)} grup var")
            es=[g for g in gruplar if grup_eslesiyor_mu(g,cfg["kaynak_grup"])]
            print(f"  [DEBUG] Eşleşen: {es}" if es else f"  [UYARI] '{cfg['kaynak_grup']}' eşleşmedi!")
        try: secilen=kaynak_sec(kaynak_records,cfg)
        except Exception as e: hatali+=1; hata_ekle(cfg,f"Filtreleme: {e}"); print(f"  [ATLANDI] Filtreleme {e}"); continue
        if not secilen:
            print("  [BOŞ] Uygun kanal bulunamadı.")
            _g=sorted(set(grup_bul(r) for r in kaynak_records if grup_bul(r)))
            print(f"  [DEBUG] Kaynakta {len(_g)} grup var, ilk 30:")
            for gg in _g[:30]: print(f"    - '{gg}'")
            basarili+=1; continue
        print(f"  [OKUNDU] {len(secilen)} kanal bulundu.")
        hedef_grup=cfg["hedef_grup"]
        if any(grup_bul(r)==hedef_grup for r in hedef_records) and hedef_grup:
            once=len(hedef_records); hedef_records=grubu_birlestir(hedef_records,secilen,hedef_grup); eklenen_toplam+=max(0,len(hedef_records)-once); print(f"  [YAZILDI] Grup birleştirildi: {hedef_grup}"); basarili+=1; continue
        if not hedef_grup:
            def _url(r):
                for l in r:
                    if l.strip().startswith(("http://","https://")): return l.strip()
                return ""
            mevcut={_url(r) for r in hedef_records if _url(r)}
            yeni=[r for r in secilen if _url(r) not in mevcut]
            print(f"  [BİLGİ] Sinema: {len(secilen)} bulundu, {len(yeni)} yeni, {len(secilen)-len(yeni)} zaten var")
            hedef_records.extend(yeni); eklenen_toplam+=len(yeni); print(f"  [YAZILDI] Kaynak grupları aynen eklendi: {len(yeni)} kanal"); basarili+=1; continue
        baslangic=grup_baslangici(hedef_grup); print(f"  [DEBUG] Hedef başlangıç: '{baslangic}'")
        son=benzer_bitis(hedef_records,baslangic)
        if son is not None: hedef_records=hedef_records[:son+1]+secilen+hedef_records[son+1:]; print(f"  [YAZILDI] Benzer grubun altına eklendi: {baslangic}")
        else: hedef_records.extend(secilen); print("  [YAZILDI] Yeni grup en sona eklendi.")
        eklenen_toplam+=len(secilen); basarili+=1
    print("\n====================================\n MIRTI68 - DOSYA KAYDEDİLİYOR\n====================================")
    try: shutil.copy2(HEDEF_DOSYA, HEDEF_DOSYA+".bak"); print("[YEDEK] mirti68.m3u.bak oluşturuldu.")
    except Exception as e: print(f"[UYARI] Yedek: {e}")
    sonuc=list(baslik)
    for r in hedef_records: sonuc.extend(r)
    try:
        with open(HEDEF_DOSYA,"w",encoding=enc,newline="") as f: f.write(newline.join(sonuc)+newline)
    except Exception as e: print(f"[HATA] Dosya yazılamadı: {e}"); return
    print(f"\n====================================\n MIRTI68 - AKTARIM TAMAMLANDI\n====================================\n[BAŞARILI] {basarili}\n[HATALI / ATLANAN] {hatali}\n[EKLENEN KAYIT] {eklenen_toplam}\n[TOPLAM KANAL] {len(hedef_records)}\n[DOSYA] {HEDEF_DOSYA}")
    try:
        with open("hatali_url_listesi.txt","w",encoding="utf-8") as f:
            f.write("MIRTI68 - HATALI URL LİSTESİ\n"+"="*50+"\n")
            if not hatali_list: f.write("\n[TEMİZ] Hata yok\n")
            for h in hatali_list: f.write(f"\nHEDEF GRUP: {h['hedef_grup']}\nKAYNAK GRUP: {h['kaynak_grup']}\nURL: {h['url']}\nSEBEP: {h['sebep']}\n")
        print("[DOSYA] hatali_url_listesi.txt yazıldı.")
    except Exception as e: print(f"[UYARI] Hatalı liste yazılamadı: {e}")
    print("\n====================================\n HATALI URL LİSTESİ\n====================================")
    if not hatali_list: print("[TEMİZ] Hata veren URL yok")
    else:
        for i,h in enumerate(hatali_list,1): print(f"\n[{i}] HEDEF GRUP: {h['hedef_grup']}\n    URL: {h['url']}\n    SEBEP: {h['sebep']}")
    print("====================================\n[TAMAM] ÇALIŞAN KAYNAKLAR AKTARILDI\n[TAMAM] Hatalı URL'ler işlemi durdurmadı\n====================================")

if __name__ == "__main__":
    main()
