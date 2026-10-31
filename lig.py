import os
import re
import json
import requests
import concurrent.futures

# --- AYARLAR ---
super_lig_sezonlar = {
    3853: '2025/2026', 
    3974: '2026/2027',
}
super_lig_haftalar = {
    3853: range(1, 39),
    3974: range(1, 39),
}

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
        if not match: return []
        data = json.loads(match.group(1))
        highlights_data = data.get("props", {}).get("pageProps", {}).get("initialReduxState", {}).get("highlights", {}).get("data", [])
        if not highlights_data: return []
        for season in highlights_data[0].get("seasons", []):
            sid = season.get("id")
            sname = season.get("name")
            for rnd in season.get("rounds", []):
                url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=130&s={sid}&r={rnd.get('round')}&st={rnd.get('st',0)}"
                urls_to_fetch.append((url, f"TFF 1. Lig {sname}"))
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
            logo = ev.get('highlightThumbnail', '') or ev.get('thumbnail', '')
            mid = ev.get('matchId', '')
            if video_url:
                title = f"{home} {hs}-{aws} {away}"
                # DİREKT GOLLER GRUBU
                line1 = f'#EXTINF:-1 tvg-id="{mid}" tvg-logo="{logo}" group-title="GOLLER",{title}\n'
                line2 = f"{video_url}\n"
                result.append((line1, line2))
        return result
    except Exception as e:
        print(f"FAIL {url} - {e}")
        return []

def main():
    all_urls = []
    for sid, sname in super_lig_sezonlar.items():
        for hafta in super_lig_haftalar.get(sid, range(1,39)):
            url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=18&s={sid}&r={hafta}&st=0"
            all_urls.append((url, sname))

    all_urls.extend(get_birinci_lig_urls_dynamically())
    print(f"Toplam {len(all_urls)} hafta taranacak...")

    all_videos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(fetch_and_parse, all_urls):
            all_videos.extend(res)

    # mirti68.m3u oluştur
    with open("mirti68.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
        for l1, l2 in all_videos:
            f.write(l1)
            f.write(l2)

    print(f"BİTTİ: {len(all_videos)} gol -> mirti68.m3u oluşturuldu")

if __name__ == "__main__":
    main()
