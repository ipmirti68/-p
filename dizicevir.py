import json, urllib.request, re

SOURCES = [
    ("https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/atv_state.json", "atv.m3u"),
    ("https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/kanald_state.json", "kanalddizi.m3u"),
    ("https://raw.githubusercontent.com/KiNGTV2025/Kingof/refs/heads/main/startv_state.json", "stardizi.m3u"),
]

LOGO_KEYS = ("logo", "poster", "image", "img", "thumb", "thumbnail", "cover", "poster_url", "logo_url")
GROUP_KEYS = ("group", "type", "category", "kategori", "grup")
EP_KEYS = ("episodes", "bolumler", "bolum", "bölümler", "bölümler", "items", "videos", "list", "episode_list")
NAME_KEYS = ("name", "title", "baslik", "ad")
URL_KEYS = ("url", "link", "video_url", "stream", "src", "m3u8", "mp4")

def temiz(s):
    return re.sub(r"\s+", " ", (str(s or "")).replace("\n", " ").replace("\r", " ")).strip()

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
    # "Bölüm 12" / "12. Bolum" / "Episode 12" gibi haller
    m = re.search(r"Bölüm\s*(\d+)", name or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    if "İlk" in (name or "") or "ilk" in (name or "").lower():
        return 1
    return 9999

def bolum_listesi_bul(dizi):
    # episodes / bolumler / vs. hangisi varsa onu al
    for k in EP_KEYS:
        v = dizi.get(k)
        if isinstance(v, list) and v:
            return v
    # Hiçbiri yoksa: dict içindeki ilk liste değerini al (Star TV farklı isim kullanmış olabilir)
    for v in dizi.values():
        if isinstance(v, list) and v and isinstance(v[0], (dict, str)):
            return v
    return []

def cevir(url, out):
    print(f"İndiriliyor: {url}")
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read().decode("utf-8"))

    lines = ['#EXTM3U x-tvg-url=""']
    say = 0

    # Üst seviye liste de olabilir: [{"name":..., "episodes":[...]}]
    if isinstance(data, list):
        data = {temiz(ilk(x, NAME_KEYS) or f"dizi-{i}"): x for i, x in enumerate(data) if isinstance(x, dict)}

    for key, dizi in data.items():
        if not isinstance(dizi, dict):
            continue
        dizi_adi = temiz(ilk(dizi, NAME_KEYS) or key)
        group = temiz(ilk(dizi, GROUP_KEYS) or "DIZI")
        logo = temiz(ilk(dizi, LOGO_KEYS))
        eps = bolum_listesi_bul(dizi)

        def siralama(e):
            if isinstance(e, dict) and "order" in e:
                try:
                    return int(e["order"])
                except:
                    pass
            if isinstance(e, dict):
                return bolum_no(temiz(ilk(e, NAME_KEYS)))
            return 9999
        eps = sorted(eps, key=siralama)

        gorulen = set()
        for ep in eps:
            # Bölüm bazen düz string url olabilir
            if isinstance(ep, str):
                url_ep, ep_adi = ep.strip(), ""
            elif isinstance(ep, dict):
                url_ep = temiz(ilk(ep, URL_KEYS))
                ep_adi = temiz(ilk(ep, NAME_KEYS))
            else:
                continue
            if not url_ep or url_ep in gorulen:
                continue
            gorulen.add(url_ep)

            ep_adi = ep_adi.replace("Izle.", "").replace("izle", "").strip()
            ep_adi = ep_adi.replace("/", ". ").strip()
            ep_adi = temiz(ep_adi)

            if not ep_adi:
                title = dizi_adi
            elif ep_adi.startswith(dizi_adi):
                title = ep_adi
            else:
                title = f"{dizi_adi} - {ep_adi}"

            lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{title}')
            lines.append(url_ep)
            say += 1

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Yazildi: {out} - {say} bolum")

for u, o in SOURCES:
    cevir(u, o)
