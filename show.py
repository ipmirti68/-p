import cloudscraper, re, os, time, json
from bs4 import BeautifulSoup
m3u_file="showtv.m3u"
mirti_file="mirti68.m3u"
GROUP="SHOW Dizileri"
site="https://www.showtv.com.tr"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})

def fetch(u):
    try:
        r=scraper.get(u, timeout=20)
        if len(r.text)>1000: return r.text
    except: return ""
    return ""

def m3u8_from_html(html):
    # vmcdn m3u8
    m=re.findall(r'https?://[^"\'\s]*vmcdn[^"\'\s]*\.m3u8[^"\'\s]*', html)
    if m: return m[0].replace("\\/","/")
    # data-hope-video json
    mh=re.search(r"data-hope-video='(.*?)'", html)
    if mh:
        try:
            j=json.loads(mh.group(1).replace('&quot;','"'))
            return j["media"]["m3u8"][0]["src"].replace("\\/","/")
        except: pass
    return None

slugs=["kizilcik-serbeti","sevdan-bir-ates","muhtemel-ask"]
all_entries=[]

for slug in slugs:
    print(f"\n=== {slug} ===")
    html=fetch(f"{site}/dizi/{slug}")
    soup=BeautifulSoup(html, "html.parser")
    links={}
    for a in soup.find_all("a", href=True):
        h=a["href"]
        if slug not in h.lower() or "bolum" not in h.lower() or "bolumler" in h.lower(): continue
        if h.startswith("/"): h=site+h
        # numara al
        mm=re.search(r'(\d+)[^0-9]*bolum', h.lower())
        num=int(mm.group(1)) if mm else 0
        if h not in links or num>links[h]: links[h]=num

    # son 3 bölümü al, büyükten küçüğe
    last3=sorted(links.items(), key=lambda x:x[1], reverse=True)[:3]
    print(f"  son 3: {last3}")
    for url,num in last3:
        bh=fetch(url)
        u=m3u8_from_html(bh)
        if u:
            all_entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum","url":u,"num":num})
            print(f"  OK {num}. Bolum -> {u[:60]}...")
        else:
            print(f"  URL YOK {url}")

# yaz - tekrar yok
with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_entries, key=lambda x:(x["dizi"], -x["num"])):
        f.write(f'#EXTINF:-1 group-title="{GROUP}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

# mirti68.m3u güncelle - grubunu sil yenisini ekle
if not os.path.exists(mirti_file): open(mirti_file,"w").write("#EXTM3U\n")
with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=[ "#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p ]
with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: new=[ "#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p ]
with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")
print(f"Bitti {len(new)} kayıt, tekrar yok")
