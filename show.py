import cloudscraper, re, json, os, time
m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
site_url="https://www.showtv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
def fetch(url):
    try:
        r=scraper.get(url,timeout=10)
        if len(r.text)>1000 and "html" in r.text.lower(): return r.text
    except: pass
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=20)
        return r.text
    except: return ""
def main():
    diziler=[]
    for slug in ["kizilcik-serbeti","bahar","sandik-kokusu","siyah-kalp","deha","kalpazan","sevdan-bir-ates","guldur-guldur-show"]:
        diziler.append({"name":slug.replace("-"," ").title(),"id":slug,"url":f"{site_url}/dizi/{slug}"})
    print(f"Toplam {len(diziler)} dizi")
    all_data=[]
    for s in diziler:
        html=fetch(s["url"])
        links=re.findall(r'/dizi/'+re.escape(s["id"])+r'/[^"\']*bolum[^"\']*',html)
        uniq=list(dict.fromkeys(links))
        print(f"  {s['name']} HTML -> {len(uniq)} bolum")
        ok=[]
        for u in uniq[:10]:
            full=u if u.startswith("http") else site_url+u if u.startswith("/") else site_url+"/"+u
            h=fetch(full)
            m=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',h)
            if m:
                url=m[0].replace("\\/","/")
                mm=re.search(r'(\d+)[-_]?bolum',u,re.I)
                name=f"{mm.group(1)}. Bolum" if mm else "Bolum"
                ok.append({"name":name,"stream_url":url,"img":""})
                print(f"    OK {name}")
            time.sleep(0.5)
        if ok:
            s["episodes"]=ok
            all_data.append(s)
    with open(m3u_file,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in all_data:
            for ep in serie["episodes"]:
                f.write(f'#EXTINF:-1 group-title="SHOWTV Dizileri",TR: {ep["name"]} - {serie["name"]}\n{ep["stream_url"]}\n')
    print(f"{m3u_file} -> {sum(len(s['episodes']) for s in all_data)} bolum")
    if os.path.exists(mirti_file):
        with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read(); first=cont.splitlines()[0]; old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
        with open(mirti_file,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")
if __name__=="__main__": main()
