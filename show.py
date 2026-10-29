import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
import re
import time
import os
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

site_url = "https://www.showtv.com.tr"
diziler_url = "https://www.showtv.com.tr/diziler"
m3u_file = "showtv.m3u"
mirti_file = "mirti68.m3u"  # ANA LISTEN

def create_session():
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    return session

session = create_session()
pattern = r'data-hope-video=\'(.*?)\''

def parse_bolum_page(url):
    try:
        time.sleep(0.5)
        r = session.get(url, timeout=10)
        r.raise_for_status()
        match = re.search(pattern, r.text)
        if match:
            video_data = match.group(1).replace('&quot;', '"')
            video_data = json.loads(video_data)
            m3u8_list = video_data.get("media", {}).get("m3u8", [])
            for item in m3u8_list:
                if "src" in item and item["src"].endswith(".m3u8"):
                    return item["src"]
    except Exception as e:
        print(f"Bölüm hatası: {url} - {e}")
    return None

def parse_episodes_page(url):
    try:
        time.sleep(0.3)
        r = session.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()["episodes"]
        item_list = []
        for item in data:
            item_name = item["title"].replace("-", " ")
            item_img = item["image"]
            item_url = site_url + item["link"]
            item_list.insert(0, {"name": item_name, "img": item_img, "url": item_url})
        return item_list
    except:
        return []

def get_episodes_page(serie_url):
    all_items = []
    base_url = "https://www.showtv.com.tr/dizi/pagination/SERIE_ID/2/"
    serie_id = serie_url.split("/")[-1]
    url = base_url.replace("SERIE_ID", serie_id)
    page_no = 0
    while True:
        page_url = url + str(page_no)
        page_items = parse_episodes_page(page_url)
        if not page_items:
            break
        all_items = page_items + all_items
        page_no += 1
    return all_items

def get_arsiv_page(url):
    item_list = []
    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        items = soup.find_all("div", {"data-name": "box-type6"})
        for item in items:
            item_url = site_url + item.find("a").get("href")
            item_img = item.find("img").get("src")
            item_name = item.find("span", {"class": "line-clamp-3"}).get_text().strip().replace("-", " ")
            item_id = item_url.split("/")[-1]
            item_list.append({"name": item_name, "img": item_img, "url": item_url, "id": item_id})
    except Exception as e:
        print(f"Arşiv hatası: {e}")
    return item_list

def append_to_mirti68():
    """showtv.m3u -> mirti68.m3u bozmayacak şekilde ekle"""
    if not os.path.exists(m3u_file):
        print(f"{m3u_file} yok!")
        return
    if not os.path.exists(mirti_file):
        print(f"{mirti_file} yok!")
        return

    with open(m3u_file, "r", encoding="utf-8", errors="ignore") as f:
        show_content = f.read()
    
    show_blocks = []
    for p in show_content.split("#EXTINF")[1:]:
        if "http" in p:
            show_blocks.append("#EXTINF" + p.strip())

    print(f"SHOWTV Dizileri: {len(show_blocks)} bölüm")

    with open(mirti_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first_line = content.splitlines()[0] if content else "#EXTM3U"
        epg_header = first_line if "#EXTM3U" in first_line else "#EXTM3U"
        old_blocks = []
        for p in content.split("#EXTINF")[1:]:
            if "SHOWTV Dizileri" in p:  # SADECE BUNU SİL
                continue
            if "http" in p:
                old_blocks.append("#EXTINF" + p.strip())

    with open(mirti_file, "w", encoding="utf-8") as out:
        out.write(epg_header + "\n")
        for b in old_blocks:
            out.write(b + "\n\n")
        for b in show_blocks:
            out.write(b + "\n\n")

    print(f"Bitti! Bozulmadı - {len(old_blocks)} eski + {len(show_blocks)} SHOWTV")

def main(start=0, end=0):
    data = []
    series_list = get_arsiv_page(diziler_url)
    end_index = len(series_list) if end == 0 else end
    print(f"Toplam {len(series_list)} dizi bulundu")

    for i in tqdm(range(start, end_index)):
        serie = series_list[i]
        print(f"{i+1}/{end_index} - {serie['name']}")
        try:
            episodes = get_episodes_page(serie["url"])
            if episodes:
                temp_serie = serie.copy()
                temp_serie["episodes"] = []
                print(f"  {len(episodes)} bölüm")
                for episode in episodes:
                    stream_url = parse_bolum_page(episode["url"])
                    episode["stream_url"] = stream_url
                    if stream_url:
                        temp_serie["episodes"].append(episode)
                if temp_serie["episodes"]:
                    data.append(temp_serie)
        except Exception as e:
            print(f"  Hata: {e}")
            continue

    with open(m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in data:
            for ep in serie["episodes"]:
                line = f'#EXTINF:-1 tvg-id="vod.tr" tvg-name="TR: {ep["name"]}" tvg-logo="{ep["img"]}" group-title="SHOWTV Dizileri",TR: {ep["name"]}\n{ep["stream_url"]}\n'
                f.write(line)

    print(f"{m3u_file} oluşturuldu!")
    append_to_mirti68()

if __name__ == "__main__":
    main()
