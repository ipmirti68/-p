import cloudscraper, re, os, time
m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
site_url="https://www.showtv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.showtv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    # GitHub blok yememesi için direkt WORKER'dan çek
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=25)
        print(f"fetch {url[:60]} -> {len(r.text)} byte")
        return r.text
    except Exception as e:
        print(f"fetch hata: {e}")
        return ""

# Sadece Sevdan Bir Ates test edelim
diziler=[
    {"name":"Sevdan Bir Ates","id":"sevdan-bir-ates","url":f"{site_url}/dizi/sevdan-bir-ates"}
]

all_data=[]
for s in diziler:
    print(f"\n{s['name']} sayfasi aliniyor...")
    html=fetch(s["url"])
    # tum bolum linkleri
    links=re.findall(r'/dizi/'+re.escape(s["id"])+r'/bolum/[^"\']+',html)
    links=re.findall(r'/dizi/sevdan-bir-ates/bolum/[^\"]+',html) if not links else links
    # uniq + sort - 8 en son
    uniq=sorted(list(dict.fromkeys(links)))
    print(f"HTML -> {len(uniq)} bolum linki")
    for u in uniq:
        print(f"  link: {u}")
    
    # eger hala 0 ise manuel ekle - 8. bolum garanti
    if len(uniq)==0:
        uniq=[f"/dizi/sevdan-bir-ates/bolum/{i}-bolum" for i in range(1,9)]
        print(f"Manuel liste kullaniliyor: {uniq}")

    ok=[]
    for u in uniq[-10:]: # son 10 bolum, 8 dahil
        full=u if u.startswith("http") else site_url+u
        print(f"\nDeniyor: {full}")
        h=fetch(full)
        # Show TV m3u8 3 yontem
        stream=None
        # 1. direkt m3u8
        m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',h)
        if m:
            stream=m[0].replace("\\/","/")
        # 2. data-hope-video
        if not stream:
            mh=re.search(r"data-hope-video='(.*?)'",h)
            if mh:
                try:
                    import json
                    data=json.loads(mh.group(1).replace('&quot;','"'))
                    stream=data.get("media",{}).get("m3u8",[{}])[0].get("src")
                except: pass
        
        if stream:
            mm=re.search(r'(\d+)[-_]?bolum',u,re.I)
            name=f"{mm.group(1)}. Bolum" if mm else "Bolum"
            ok.append({"name":name,"stream_url":stream,"img":""})
            print(f"  OK {name} -> {stream[:80]}")
        else:
            print(f"  m3u8 bulunamadi")
        time.sleep(1)

    if ok:
        s["episodes"]=ok
        all_data.append(s)

with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for serie in all_data:
        for ep in serie["episodes"]:
            f.write(f'#EXTINF:-1 group-title="SHOWTV Dizileri",TR: {ep["name"]} - {serie["name"]}\n{ep["stream_url"]}\n')

print(f"\n{m3u_file} -> {sum(len(s['episodes']) for s in all_data)} bolum")

# mirti68'e ekle
if os.path.exists(mirti_file):
    with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff:
        blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0]
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
    with open(mirti_file,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
    print(f"Mirti: {len(old)} eski + {len(blocks)} SHOW")
