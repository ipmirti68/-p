import os
import re
import json
import requests
import concurrent.futures

super_lig_sezonlar = { 3853: '2025/2026', 3974: '2026/2027' }
super_lig_haftalar = { 3853: range(1, 39), 3974: range(1, 39) }
super_lig_st = {3853: 0, 3974: 0}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.beinsports.com.tr/',
    'Origin': 'https://www.beinsports.com.tr'
}

def get_birinci_lig_urls_dynamically():
    page_url = "https://www.beinsports.com.tr/mac-ozetleri-goller/tff-1-lig"
    urls_to_fetch = []
    try:
        r = requests.get(page_url, timeout=20, headers=HEADERS)
        r.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
        if not match: 
            print("NEXT_DATA bulunamadı")
            return []
        data = json.loads(match.group(1))
        highlights_data = data.get("props", {}).get("pageProps", {}).get("initialReduxState", {}).get("highlights", {}).get("data", [])
        if not highlights_data:
            print("highlights data boş")
            return []
        for season in highlights_data[0].get("seasons", []):
            season_name = season.get("name")
            season_id = season.get("id")
            for rnd in season.get("rounds", []):
                url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=130&s={season_id}&r={rnd.get('round')}&st={rnd.get('st',0)}"
                urls_to_fetch.append((url, f"TFF 1. Lig {season_name}"))
        print(f"TFF 1. Lig için {len(urls_to_fetch)} URL bulundu")
        return urls_to_fetch
    except Exception as e:
        print(f"TFF 1. Lig hatası: {e}")
        return []

def fetch_and_parse(url_info):
    url, group_title = url_info
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        r.raise_for_status()
        j = r.json()
        # API bazen Data, bazen data
        events = j.get('Data', {}).get('events', []) or j.get('data', {}).get('events', []) or j.get('events', [])
        result = []
        for ev in events:
            home = ev.get('homeTeam', {}).get('name', 'Ev')
            away = ev.get('awayTeam', {}).get('name', 'Dep')
            hs = ev.get('homeTeam', {}).get('matchScore', '-')
            aws = ev.get('awayTeam', {}).get('matchScore', '-')
            # video alanı değişmiş olabilir
            video_url = ev.get('highlightVideoUrl') or ev.get('videoUrl') or ev.get('video_url') or ev.get('mp4Url')
            logo = ev.get('highlightThumbnail', '') or ev.get('thumbnail', '')
            mid = ev.get('matchId', '')
            if video_url:
                title = f"{home} {hs}-{aws} {away}"
                line1 = f'#EXTINF:-1 tvg-id="{mid}" tvg-logo="{logo}" group-title="{group_title}",{title}\n'
                line2 = f"{video_url}\n"
                result.append((group_title, line1, line2))
        if result:
            print(f"OK {group_title} -> {url} : {len(result)} video")
        return result
    except Exception as e:
        print(f"FAIL {url} - {e}")
        return []

def main():
    output_folder = 'output' # DÜZELTİLDİ: lig.m3u değil
    os.makedirs(output_folder, exist_ok=True)

    all_urls = []
    for sid, sname in super_lig_sezonlar.items():
        for hafta in super_lig_haftalar.get(sid, range(1,39)):
            url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=18&s={sid}&r={hafta}&st={super_lig_st.get(sid,0)}"
            all_urls.append((url, f"Süper Lig {sname}"))
    
    all_urls.extend(get_birinci_lig_urls_dynamically())
    print(f"Toplam {len(all_urls)} URL çekilecek...")

    grouped = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(fetch_and_parse, all_urls):
            for g, l1, l2 in res:
                grouped.setdefault(g, []).append((l1,l2))

    if not grouped:
        print("HİÇ VİDEO BULUNAMADI! API engelliyor olabilir.")
    
    all_combined = []
    for g, lines in sorted(grouped.items()):
        safe = g.replace('/','-').replace(' ','_')
        fp = os.path.join(output_folder, f"{safe}.m3u")
        with open(fp, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n\n")
            for l1,l2 in lines:
                f.write(l1); f.write(l2)
                all_combined.append((l1,l2))

    with open(os.path.join(output_folder, 'all_leagues.m3u'), 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n\n")
        for l1,l2 in all_combined:
            f.write(l1); f.write(l2)
    
    print(f"BİTTİ: {len(all_combined)} video -> {output_folder}/all_leagues.m3u")

if __name__ == "__main__":
    main()
