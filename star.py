import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
import re
import os

base_url = "https://www.startv.com.tr"
img_base_url = "https://media.startv.com.tr/star-tv"
dizi_url = "https://www.startv.com.tr/dizi"
m3u_file = "startv.m3u"
mirti_file = "mirti68.m3u"  # ANA LISTEN
pattern = r'"apiUrl\\":\\"(.*?)\\"'

api_params = {
    "sort": "episodeNo asc",
    "limit": "100"
}

def get_items_page(url):
    item_list = []
    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.content, "html.parser")
    links = soup.find_all("a", href=re.compile(r'^/dizi/'))
    seen = set()
    for a in links:
        href = a.get("href")
        if href and href not in seen:
            seen.add(href)
            item_url = base_url + href
            slug = href.split("/")[-1]
            name = slug.replace("-", "").strip()
            item_list.append({
                "name": name,
                "img": "",
                "url": item_url
            })
    return item_list

def get_item_api_url(url):
    api_path = ""
    r = requests.get(url + "/bolumler", timeout=15)
    results = re.findall(pattern, r.text)
    if results:
        api_path = results[0]
    return api_path

def get_item_api(path):
    item_list = []
    params = api_params.copy()
    flag = True
    skip = 0
    url = base_url + path
    while flag:
        params["skip"] = skip
        try:
            r = requests.get(url, params=params, timeout=15)
            data = r.json()
            items = data.get("items", [])
            for item in items:
                name = f'{item["heading"]} {item["title"]}'
                name = name.replace("-", " ").replace("  ", " ").strip()
                img = img_base_url + item["image"]["fullPath"] if item.get("image") else ""
                stream_url = ""
                if "video" in item:
                    stream_url = f'https://dygvideo.dygdigital.com/api/redirect?PublisherId=1&ReferenceId=StarTV_{item["video"]["referenceId"]}&SecretKey=NtvApiSecret2014*&.m3u8'
                if stream_url:
                    item_list.append({
                        "name": name,
                        "img": img,
                        "stream_url": stream_url
                    })
            if len(items) < 100:
                flag = False
            else:
                skip += 100
        except:
            flag = False
    return item_list

def append_to_mirti68():
    """startv.m3u -> mirti68.m3u bozmayacak şekilde ekle"""
    if not os.path.exists(m3u_file):
        print(f"{m3u_file} yok!")
        return
    if not os.path.exists(mirti_file):
        print(f"{mirti_file} yok, önce iptv.py çalıştır")
        return

    # startv.m3u bloklarını oku
    with open(m3u_file, "r", encoding="utf-8", errors="ignore") as f:
        startv_content = f.read()
    
    startv_blocks = []
    parts = startv_content.split("#EXTINF")
    for p in parts[1:]:
        if "http" in p:
            startv_blocks.append("#EXTINF" + p.strip())

    print(f"STARTV Dizileri: {len(startv_blocks)} bölüm bulundu")

    # mirti68.m3u oku, EPG + eski STARTV Dizileri hariç her şey kalsın
    with open(mirti_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        first_line = content.splitlines()[0] if content else "#EXTM3U"
        epg_header = first_line if "#EXTM3U" in first_line else "#EXTM3U"
        
        old_blocks = []
        parts2 = content.split("#EXTINF")
        for p in parts2[1:]:
            # Eğer daha önce eklenmiş STARTV Dizileri varsa sil, yenileyeceğiz
            if "STARTV Dizileri" in p:
                continue
            if "http" in p:
                old_blocks.append("#EXTINF" + p.strip())

    # Geri yaz: EPG + eski liste + yeni STARTV Dizileri
    with open(mirti_file, "w", encoding="utf-8") as out:
        out.write(epg_header + "\n")
        for b in old_blocks:
            out.write(b + "\n\n")
        for b in startv_blocks:
            out.write(b + "\n\n")

    print(f"Bitti! {mirti_file} bozulmadı, {len(old_blocks)} eski + {len(startv_blocks)} STARTV eklendi")

def main(start=0, end=0):
    data = []
    series_list = get_items_page(dizi_url)
    if end == 0:
        end_index = len(series_list)
    else:
        end_index = end

    for i in tqdm(range(start, end_index)):
        serie = series_list[i]
        print(i+1, serie["name"])
        api_path = get_item_api_url(serie["url"])
        if not api_path:
            continue
        episodes = get_item_api(api_path)
        temp_serie = serie.copy()
        temp_serie["episodes"] = episodes
        data.append(temp_serie)

    # M3U oluştur
    with open(m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in data:
            for ep in serie["episodes"]:
                line = f'#EXTINF:-1 tvg-id="vod.tr" tvg-name="TR: {ep["name"]}" tvg-logo="{ep["img"]}" group-title="STAR Dizileri",TR: {ep["name"]}\n{ep["stream_url"]}\n'
                f.write(line)

    print(f"{m3u_file} başarıyla oluşturuldu!")

    # HEMEN mirti68.m3u'ya bozmayacak şekilde ilave et
    append_to_mirti68()

if __name__ == "__main__":
    main()
