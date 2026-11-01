import requests, re, os
from bs4 import BeautifulSoup
from tqdm import tqdm
base_url="https://www.startv.com.tr"
m3u_file="mirti68.m3u"
mirti_file="mirti68.m3u"
WANTED_SERIES=["baskalarinin-hayati","tuzlu-kahve","sevdigim-sensin"]

def normalize(s):
    s=s.lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return s

def get_poster(dizi_url):
    """poster ya da son bölüm görselini al - logo yerine"""
    try:
        r=requests.get(dizi_url, timeout=15)
        soup=BeautifulSoup(r.content, "html.parser")
        # 1. og:image - genelde poster oluyor
        og=soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        # 2. twitter:image
        tw=soup.find("meta", attrs={"name":"twitter:image"})
        if tw and tw.get("content"):
            return tw["content"]
        # 3. dizi afişi img
        for img in soup.find_all("img"):
            src=img.get("src","") or img.get("data-src","")
            if src and ("dizi" in src.lower() or "poster" in src.lower() or "afis" in src.lower()):
                if src.startswith("/"): src=base_url+src
                return src
        # 4. ilk büyük resim
        for img in soup.find_all("img"):
            src=img.get("src","")
            if src.startswith("http") and "startv" in src and len(src)>30:
                return src
    except: pass
    return ""

def get_items_page():
    r=requests.get(f"{base_url}/dizi", timeout=15)
    soup=BeautifulSoup(r.content, "html.parser")
    out=[]
    for a in soup.find_all("a", href=re.compile(r'/dizi/')):
        href=a.get("href","").strip().strip("/")
        slug=href.split("/")[-1].lower()
        norm_slug=normalize(slug)
        for wanted in WANTED_SERIES:
            nw=normalize(wanted)
            if nw in norm_slug or norm_slug in nw or "baskalarinin" in norm_slug or "baskasinin" in norm_slug or "tuzlu" in norm_slug or "sevdigim" in norm_slug or "sevdim" in norm_slug:
                if "tuzlu" in norm_slug: real="tuzlu-kahve"
                elif "baskalarinin" in norm_slug or "baskasinin" in norm_slug: real="baskalarinin-hayati"
                elif "sevdigim" in norm_slug or "sevdim" in norm_slug: real="sevdigim-sensin"
                else: real=slug
                if real not in [x["slug"] for x in out]:
                    # poster çek
                    poster=get_poster(base_url+"/dizi/"+slug)
                    out.append({"slug":real,"url":base_url+"/dizi/"+slug,"poster":poster})
                break
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
                    # son bölüm görseli varsa
                    thumb=""
                    if "images" in it and it["images"]:
                        thumb=it["images"][0].get("url","") if isinstance(it["images"], list) else ""
                    item_list.append({"name":name,"url":stream,"thumb":thumb})
            if len(items)<100: break
            skip+=100
        except Exception as e:
            print(f"  episode hata {e}")
            break
    return item_list

def main():
    series=get_items_page()
    print(f"Filtrelenen: {len(series)} - {series}")
    if len(series)==0:
        print("Site parse edemedi, manuel ekleniyor")
        series=[
            {"slug":"baskalarinin-hayati","url":base_url+"/dizi/baskalarinin-hayati","poster":""},
            {"slug":"tuzlu-kahve","url":base_url+"/dizi/tuzlu-kahve","poster":""},
            {"slug":"sevdigim-sensin","url":base_url+"/dizi/sevdigim-sensin","poster":""},
        ]
        # posterleri tek tek çek
        for s in series:
            s["poster"]=get_poster(s["url"])
    
    all_eps=[]
    for s in series:
        print(f"\n=== {s['slug']} poster: {s.get('poster','')[:60]} ===")
        try:
            r=requests.get(s["url"]+"/bolumler", timeout=15)
            m=re.findall(r'"apiUrl\\":\\"(.*?)\\"', r.text)
            if not m: m=re.findall(r'"apiUrl":\s*"(.*?)"', r.text)
            if not m:
                print(f"  apiUrl bulunamadı {s['url']}")
                continue
            eps=get_episodes(m[0])
            print(f"  {len(eps)} bolum")
            # poster öncelikli, yoksa son bölüm görseli
            logo=s.get("poster","")
            for ep in eps[-3:]:
                use_logo=ep.get("thumb") or logo
                # logo varsa tvg-logo ekle
                if use_logo:
                    all_eps.append(f'#EXTINF:-1 tvg-logo="{use_logo}" group-title="STAR Dizileri", {ep["name"]}\n{ep["url"]}\n')
                else:
                    all_eps.append(f'#EXTINF:-1 group-title="STAR Dizileri",TR: {ep["name"]}\n{ep["url"]}\n')
        except Exception as e:
            print(f"  hata {e}")
            continue

    with open(m3u_file,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for b in all_eps: f.write(b+"\n")

    if os.path.exists(mirti_file):
        with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "STAR Dizileri" not in p]
        with open(mirti_file,"a",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")
    print(f"\nBitti toplam {len(all_eps)} bolum - posterli")

if __name__=="__main__": main()
