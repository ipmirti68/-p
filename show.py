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

def extract_m3u8(html):
    # senin verdiğin gibi vmcdn
    m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*', html)
    if m:
        # en uzun master'ı al
        return sorted(m, key=len)[-1].replace("\\/","/")
    mh=re.search(r"data-hope-video='(.*?)'", html)
    if mh:
        try:
            j=json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            src=j["media"]["m3u8"][0]["src"].replace("\\/","/")
            return src
        except: pass
    return None

# MANUEL TAZE - senin verdiğin 8. bölüm
MANUEL={
    "sevdan-bir-ates": [
        {"num":8, "url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392", "title":"8. Bolum"},
    ]
}

slugs=["kizilcik-serbeti","sevdan-bir-ates","muhtemel-ask","menekse"]
entries=[]

# 1- manuel ekle
for slug, items in MANUEL.items():
    for it in items:
        entries.append({"dizi":slug.replace("-"," ").title(),"bolum":it["title"],"url":it["url"],"num":it["num"]})
        print(f"MANUEL eklendi {slug} {it['title']}")

# 2- siteden son 3'ü bul
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{site}/dizi/{slug}")
    if not html: html=fetch(f"{site}/dizi/{slug}/bolumler")
    soup=BeautifulSoup(html, "html.parser")
    links={}
    for a in soup.find_all("a", href=True):
        h=a["href"]
        if slug not in h.lower() or "bolum" not in h.lower() or "bolumler" in h.lower(): continue
        if h.startswith("/"): h=site+h
        mm=re.search(r'(\d+)\s*[-.]?\s*bolum', h.lower())
        if not mm: mm=re.search(r'bolum[^0-9]*(\d+)', h.lower())
        num=int(mm.group(1)) if mm else 0
        if num==0: continue
        if h not in links or num>links[h]: links[h]=num

    # zaten manuel eklenen numaraları atla
    existing_nums=[e["num"] for e in entries if slug.replace("-"," ").title().lower() in e["dizi"].lower()]
    # son 3 - 8 zaten varsa 7,6'yı al
    sorted_links=sorted(links.items(), key=lambda x:x[1], reverse=True)
    need=3-len([n for n in existing_nums])
    cnt=0
    for url,num in sorted_links:
        if num in existing_nums: continue
        if cnt>=need and slug!="sevdan-bir-ates": 
            if cnt>=2: break
        # 8 hariç 7 ve 6 lazım
        if slug=="sevdan-bir-ates" and num>=6:
            print(f"  -> {url} ({num})")
            bh=fetch(url)
            u=extract_m3u8(bh)
            if u:
                entries.append({"dizi":"Sevdan Bir Ates","bolum":f"{num}. Bolum","url":u,"num":num})
                print(f"  OK {num}")
                cnt+=1
        elif slug!="sevdan-bir-ates":
            print(f"  -> {url} ({num})")
            bh=fetch(url)
            u=extract_m3u8(bh)
            if u:
                entries.append({"dizi":slug.replace('-',' ').title(),"bolum":f"{num}. Bolum","url":u,"num":num})
                print(f"  OK")
                cnt+=1
        if cnt>=2 and slug=="sevdan-bir-ates": break
        time.sleep(0.4)

# tekrar temizle ve son 3'e indir her diziden
final={}
for e in entries:
    key=e["dizi"].lower()
    if key not in final: final[key]=[]
    final[key].append(e)

all_final=[]
for k,v in final.items():
    uniq={}
    for it in v:
        if it["num"] not in uniq: uniq[it["num"]]=it
    # en büyük 3 numara (son 3 bölüm)
    top3=sorted(uniq.values(), key=lambda x:x["num"], reverse=True)[:3]
    all_final.extend(top3)

# yaz
with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x:(x["dizi"], -x["num"])):
        f.write(f'#EXTINF:-1 group-title="{GROUP}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

print(f"\n{m3u_file} -> {len(all_final)} bolum (Sevdan Bir Ates 8,7,6)")

if not os.path.exists(mirti_file): open(mirti_file,"w").write("#EXTM3U\n")
with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")
