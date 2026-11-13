import os, re, json, requests, concurrent.futures
from datetime import datetime

super_lig_sezonlar = {3974: '2026/2027'}
super_lig_haftalar = {3853: range(1,49), 3974: range(1,49)}

HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://www.beinsports.com.tr/',
    'Origin': 'https://www.beinsports.com.tr'
}

FILM_GROUP = "🟩◆ GOLLER ⭕"

def get_group(line):
    match = re.search(r'group-title="([^"]*)"', line)
    return match.group(1).strip() if match else ""

def read_entries(lines):
    entries = []
    current = []
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            if current:
                entries.append(current)
            current = [line]
        elif current and line:
            current.append(line)
    if current:
        entries.append(current)
    return entries

def get_birinci_lig_urls_dynamically():
    # ... senin fonksiyonun aynı kalsın ...
    page_url = "https://www.beinsports.com.tr/mac-ozetleri-goller/tff-1-lig"
    urls_to_fetch = []
    try:
        r = requests.get(page_url, timeout=20, headers=HEADERS)
        r.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
        if not match: return []
        data = json.loads(match.group(1))
        highlights_data = data.get("props", {}).get("pageProps", {}).get("initialReduxState", {}).get("highlights", {}).get("data", [])
        if not highlights_data: return []
        for season in highlights_data[0].get("seasons", []):
            sid = season.get("id")
            for rnd in season.get("rounds", []):
                url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=130&s={sid}&r={rnd.get('round')}&st={rnd.get('st',0)}"
                urls_to_fetch.append((url, sid))
        return urls_to_fetch
    except Exception as e:
        print(f"TFF 1. Lig hatası: {e}")
        return []

def fetch_and_parse(url_info):
    url, _ = url_info
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        r.raise_for_status()
        j = r.json()
        events = j.get('Data', {}).get('events', []) or j.get('data', {}).get('events', []) or []
        result = []
        for ev in events:
            home = ev.get('homeTeam', {}).get('name', 'Ev')
            away = ev.get('awayTeam', {}).get('name', 'Dep')
            hs = ev.get('homeTeam', {}).get('matchScore', '-')
            aws = ev.get('awayTeam', {}).get('matchScore', '-')
            video_url = ev.get('highlightVideoUrl') or ev.get('videoUrl') or ev.get('mp4Url')
            logo = ev.get('highlightThumbnail', '') or ''
            mid = ev.get('matchId', '')
            raw_date = ev.get('eventDate') or ev.get('matchDate') or ev.get('date') or ev.get('startDate')
            tarih_str = ""
            dt_obj = datetime.min
            if raw_date:
                try:
                    dt_obj = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                    tarih_str = dt_obj.strftime("%d.%m.%Y")
                except:
                    tarih_str = str(raw_date)[:10]
            if video_url:
                title = f"{tarih_str} - {home} {hs}-{aws} {away}" if tarih_str else f"{home} {hs}-{aws} {away}"
                line1 = f'#EXTINF:-1 tvg-id="{mid}" tvg-logo="{logo}" group-title="🟩◆ GOLLER ⭕",{title}\n'
                line2 = f"{video_url.strip()}\n"
                result.append((dt_obj, line1, line2))
        return result
    except Exception as e:
        return []

def main():
    dosya = "mirti68.m3u"

    # === REVİZE: Dosyayı oku, gruplara ayır ===
    old_entries = []
    if os.path.exists(dosya):
        with open(dosya, "r", encoding="utf-8", errors="ignore") as f:
            old_entries = read_entries(f.read().splitlines())
    else:
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

    # Mevcut linkler - tekrar eklememek için
    mevcut_linkler = set()
    for entry in old_entries:
        for line in entry[1:]:
            if line.startswith("http"):
                mevcut_linkler.add(line.strip())

    all_urls=[]
    for sid in super_lig_sezonlar.keys():
        for hafta in super_lig_haftalar.get(sid, range(1,39)):
            all_urls.append((f"https://beinsports.com.tr/api/highlights/events?sp=1&o=18&s={sid}&r={hafta}&st=0", sid))
    all_urls.extend(get_birinci_lig_urls_dynamically())
    print(f"Toplam {len(all_urls)} hafta taranacak")

    yeni_videolar=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(fetch_and_parse, all_urls):
            for dt_obj, l1, l2 in res:
                if l2.strip() not in mevcut_linkler:
                    yeni_videolar.append((dt_obj, l1, l2))

    # EN YENİ TARİH EN ÜSTE - sıralama burada
    yeni_videolar.sort(key=lambda x: x[0], reverse=True)

    if not yeni_videolar:
        print("Yeni gol yok")
        return

    # Yeni videoları entry formatına çevir: [line1, line2]
    yeni_entries = [[l1.strip(), l2.strip()] for dt_obj, l1, l2 in yeni_videolar]

    # === REVİZE: Mevcut GOLLER grubunun içine ekle, en sona gitmesin ===
    final_entries = []
    inserted = False

    for entry in old_entries:
        if get_group(entry[0]) == FILM_GROUP:
            # Grubun ilk kanalını bulduk, yeni golleri tam buraya ekle
            if not inserted:
                final_entries.extend(yeni_entries)
                inserted = True
            # Eski golü de koru, altına ekle - silmek istersen bu satırı sil
            final_entries.append(entry)
            continue
        final_entries.append(entry)

    # Listede hiç GOLLER grubu yoksa, en başa ekle
    if not inserted:
        final_entries = yeni_entries + final_entries

    with open(dosya, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in final_entries:
            for line in entry:
                f.write(line + "\n")

    print(f"BİTTİ: {len(yeni_videolar)} yeni gol eklendi (grubun içine, en yeni en üstte) -> {dosya}")

if __name__=="__main__": main()
