import requests, re, os
from bs4 import BeautifulSoup
from tqdm import tqdm
base_url="https://www.startv.com.tr"
m3u_file="startv.m3u"
mirti_file="mirti68.m3u"
WANTED_SERIES=["baskasinin-hayati","tuzlu-kahve","sevdim-sensin"]

def get_items_page():
    r=requests.get(f"{base_url}/dizi", timeout=15)
    soup=BeautifulSoup(r.content, "html.parser")
    out=[]
    for a in soup.find_all("a", href=re.compile(r'/dizi/')):
        href=a.get("href","").strip().strip("/")
        slug=href.split("/")[-1].lower()
        if slug in WANTED_SERIES and slug not in [x["slug"] for x in out]:
            out.append({"slug":slug,"url":base_url+"/dizi/"+slug})
    return out

def get_episodes(api_path):
    item_list=[]
    url=base_url+api_path
    skip=0
    while True:
        try:
            r=requests.get(url, params={"sort":"episodeNo asc","limit":"100","skip":skip}, timeout=15)
            data=r.json()
            items=data.get("items",[])
            for it in items:
                name=f'{it["heading"]} {it["title"]}'.strip()
                if "video" in it:
                    stream=f'https://dygvideo.dygdigital.com/api/redirect?PublisherId=1&ReferenceId=StarTV_{it["video"]["referenceId"]}&SecretKey=NtvApiSecret2014*&.m3u8'
                    item_list.append({"name":name,"url":stream})
            if len(items)<100: break
            skip+=100
        except: break
    return item_list

def main():
    series=get_items_page()
    print(f"Filtrelenen: {len(series)} - {series}")
    all_eps=[]
    for s in series:
        print(f"\n=== {s['slug']} ===")
        # apiUrl bul
        r=requests.get(s["url"]+"/bolumler", timeout=15)
        m=re.findall(r'"apiUrl\\":\\"(.*?)\\"', r.text)
        if not m: continue
        eps=get_episodes(m[0])
        print(f"  {len(eps)} bolum")
        for ep in eps:
            all_eps.append(f'#EXTINF:-1 group-title="STAR Dizileri",TR: {ep["name"]}\n{ep["url"]}\n')

    with open(m3u_file,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for b in all_eps: f.write(b+"\n")

    if os.path.exists(mirti_file):
        with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "STAR Dizileri" not in p]
        with open(mirti_file,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")

if __name__=="__main__": main()
