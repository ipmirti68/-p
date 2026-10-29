import cloudscraper, re, os, time, json
m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
site_url="https://www.showtv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.showtv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=30)
        print(f"fetch {url[-50:]} -> {len(r.text)} byte")
        return r.text
    except Exception as e:
        print(f"hata {e}")
        return ""

# Senin verdigin ornek - Sevdan Bir Ates 8
MANUEL_LINK = "https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793317167&st=9f56173e468ce41d4a9e21d474c60eb9"

def extract_show_m3u8(html):
    # 1. senin ornekteki gibi vmcdn
    m = re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*', html)
    if m:
        return m[0].replace("\\/","/")
    # 2. data-hope-video icinde
    mh = re.search(r"data-hope-video='(.*?)'", html)
    if mh:
        try:
            data = json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            media = data.get("media",{})
            if "m3u8" in media:
                return media["m3u8"][0].get("src","").replace("\\/","/")
            # bazen sources
            for k,v in data.items():
                if isinstance(v,str) and "vmcdn" in v and ".m3u8" in v:
                    return v.replace("\\/","/")
        except: pass
    # 3. genel m3u8
    m2 = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html)
    for url in m2:
        if "ciner" in url or "showtv" in url or "vmcdn" in url:
            return url.replace("\\/","/")
    return None

def main():
    print("=== MANUEL TEST - Senin verdigin link ===")
    print(f"Sevdan Bir Ates 8 = {MANUEL_LINK[:80]}...")
    
    all_entries=[]
    # Manuel olarak ekle - senin linkin
    all_entries.append({"dizi":"Sevdan Bir Ates","bolum":"8. Bolum","url":MANUEL_LINK})
    
    slugs=["sevdan-bir-ates","kizilcik-serbeti","bahar","deha"]
    for slug in slugs:
        print(f"\n=== {slug.upper()} ===")
        html=fetch(f"{site_url}/dizi/{slug}")
        links=re.findall(r'/dizi/'+re.escape(slug)+r'/bolum/[^"\'\s]+', html)
        uniq=sorted(list(dict.fromkeys(links)))[:10]
        print(f"  Bulunan bolum link: {len(uniq)}")
        for u in uniq:
            print(f"    {u}")

        for link in uniq[-5:]:
            full=site_url+link if link.startswith("/") else link
            print(f"\nDeniyor: {full}")
            bhtml=fetch(full)
            if len(bhtml)<1000:
                continue
            m3u8 = extract_show_m3u8(bhtml)
            if m3u8:
                bm=re.search(r'(\d+)[-_]?bolum',link,re.I)
                bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
                all_entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
                print(f"  OK {bname} -> {m3u8[:80]}")
            else:
                print(f"  m3u8 YOK")
            time.sleep(1)

    # Yaz
    with open(m3u_file,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in all_entries:
            f.write(f'#EXTINF:-1 group-title="SHOWTV Dizileri",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')
    
    print(f"\n{m3u_file} -> {len(all_entries)} bolum - icinde Sevdan 8 var")

    if os.path.exists(mirti_file):
        with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff:
            blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
        with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff:
            cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
            old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "SHOWTV Dizileri" not in p]
        with open(mirti_file,"w",encoding="utf-8") as out:
            out.write(first+"\n")
            for b in old: out.write(b+"\n\n")
            for b in blocks: out.write(b+"\n\n")
        print(f"Mirti: {len(old)} eski + {len(blocks)} SHOW")

if __name__=="__main__": main()
