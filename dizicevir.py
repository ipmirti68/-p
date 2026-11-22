import json, urllib.request, re, os

# ---------- AYARLAR: Buradan dizi ekleyip çıkarabilirsin ----------
EK_KOD = "⭕"
FILTRELER = {
    "atv.m3u": {
        "aranacak": ["Altı Üstü İstanbul",  "Güneşin Doğduğu Yer"],
        "hedef_grup": "🟪◆ DİZİ - ATV  📺⭕",
    },
    "kanalddizi.m3u": {
        "aranacak": ["Haysiyet", "Uzak Şehir", "Güller ve Günahlar", "Daha 17"],
        "hedef_grup": "🟪◆ DİZİ - KANAL D  📺⭕",
    },
    "stardizi.m3u": {
        "aranacak": ["Başkalarının Hayatı", "Tuzlu Kahve", "Sevdiğim Sensin"],
        "hedef_grup": "🟪◆ DİZİ - STAR  📺⭕",
    },
}
SOURCES = [
    ("https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/atv_state.json", "atv.m3u"),
    ("https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/kanald_state.json", "kanalddizi.m3u"),
    ("https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/startv_state.json", "stardizi.m3u"),
]
HEDEF_M3U = "mirti68.m3u"  # senin listen, buna dokunulmaz, sadece bu 3 grup eklenir/silinir

LOGO_KEYS = ("logo", "poster", "image", "img", "thumb", "thumbnail", "cover", "poster_url", "logo_url")
GROUP_KEYS = ("group", "type", "category", "kategori", "grup")
EP_KEYS = ("episodes", "bolumler", "bolum", "bölümler", "bölümler", "items", "videos", "list", "episode_list")
NAME_KEYS = ("name", "title", "baslik", "ad")
URL_KEYS = ("url", "link", "video_url", "stream", "src", "m3u8", "mp4")

def temiz(s):
    return re.sub(r"\s+", " ", str(s or "").replace("\n", " ").replace("\r", " ")).strip()

def ilk(d, keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""

def bolum_no(name):
    m = re.search(r"(\d+)\s*\.\s*Bölüm", name or "")
    if m:
        return int(m.group(1))
    m = re.search(r"Bölüm\s*(\d+)", name or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    if "İlk" in (name or ""):
        return 1
    return 9999

def bolum_listesi_bul(dizi):
    for k in EP_KEYS:
        v = dizi.get(k)
        if isinstance(v, list) and v:
            return v
    for v in dizi.values():  # farklı isim kullanılmışsa ilk listeyi al
        if isinstance(v, list) and v and isinstance(v[0], (dict, str)):
            return v
    return []

def cevir(url, out):
    filtre = FILTRELER[out]
    aranacak, hedef_grup = filtre["aranacak"], filtre["hedef_grup"]
    print(f"İndiriliyor: {url}")
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read().decode("utf-8"))
    if isinstance(data, list):
        data = {temiz(ilk(x, NAME_KEYS) or f"dizi-{i}"): x for i, x in enumerate(data) if isinstance(x, dict)}

    lines, say = [], 0
    for key, dizi in data.items():
        if not isinstance(dizi, dict):
            continue
        dizi_adi = temiz(ilk(dizi, NAME_KEYS) or key)
        if dizi_adi not in aranacak:  # sadece listedekiler
            continue
        logo = temiz(ilk(dizi, LOGO_KEYS))  # ATV: logo, KanalD: poster, Star: ne varsa
        eps = bolum_listesi_bul(dizi)
        def siralama(e):
            if isinstance(e, dict) and "order" in e:
                try: return int(e["order"])
                except: pass
            return bolum_no(temiz(ilk(e, NAME_KEYS))) if isinstance(e, dict) else 9999
        eps = sorted(eps, key=siralama)

        gorulen = set()
        for ep in eps:
            if isinstance(ep, str):
                url_ep, ep_adi = ep.strip(), ""
            elif isinstance(ep, dict):
                url_ep, ep_adi = temiz(ilk(ep, URL_KEYS)), temiz(ilk(ep, NAME_KEYS))
            else:
                continue
            if not url_ep or url_ep in gorulen:
                continue  # son-bolum tekrarı
            gorulen.add(url_ep)
            ep_adi = temiz(ep_adi.replace("Izle.", "").replace("izle", "").replace("/", ". "))
            if not ep_adi:
                title = dizi_adi
            elif ep_adi.startswith(dizi_adi):
                title = ep_adi  # KanalD: "Haysiyet 9. Bölüm" zaten tam
            else:
                title = f"{dizi_adi} - {ep_adi}"  # ATV: "Altı Üstü İstanbul - 8. Bölüm"
            if EK_KOD and not title.endswith(EK_KOD):
                title = f"{title} {EK_KOD}"
            lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{hedef_grup}",{title}')
            lines.append(url_ep)
            say += 1
    with open(out, "w", encoding="utf-8") as f:
        f.write("#EXTM3U x-tvg-url=\"\"\n" + "\n".join(lines) + "\n")
    print(f"Yazildi: {out} - {say} bolum")
    return lines

def mirti68e_ekle(tum_satirlar):
    """Sadece 3 hedef grubu değiştirir. Senin listenin geri kalanına,
    başlık/EPG (x-tvg-url), tvg-id, tvg-logo satırlarına HİÇ dokunmaz."""
    if not os.path.exists(HEDEF_M3U):
        print(f"{HEDEF_M3U} yok, atlaniyor (önce iptv.py çalışmalı)")
        return
    hedef_gruplar = {v["hedef_grup"] for v in FILTRELER.values()}
    with open(HEDEF_M3U, encoding="utf-8", errors="ignore") as f:
        ham = f.read().splitlines()
    header = ham[0] if ham and ham[0].startswith("#EXTM3U") else "#EXTM3U"
    geri = ham[1:] if ham and ham[0].startswith("#EXTM3U") else ham
    bloklar, cur = [], []
    for satir in geri:
        if satir.startswith("#EXTINF"):
            if cur: bloklar.append(cur)
            cur = [satir]
        elif cur:
            cur.append(satir)
        elif satir.strip():
            bloklar.append([satir])
    if cur: bloklar.append(cur)
    tutulan, atilan = [], 0
    for b in bloklar:
        ilk_satir = b[0] if b else ""
        if ilk_satir.startswith("#EXTINF") and any(f'group-title="{g}"' in ilk_satir for g in hedef_gruplar):
            atilan += 1
            continue
        tutulan.append(b)
    yeni = [header]
    for b in tutulan:
        yeni.extend(b)
    yeni.extend(tum_satirlar)
    with open(HEDEF_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(yeni) + "\n")
    print(f"{HEDEF_M3U} güncellendi: eski 3 gruptan {atilan} kanal silindi, yeni {len(tum_satirlar)//2} bölüm eklendi, diğer kanallara dokunulmadı")

tum = []
for u, o in SOURCES:
    tum.extend(cevir(u, o))
mirti68e_ekle(tum)
