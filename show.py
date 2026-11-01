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
    m=re.findall(r'https?://[^"\'\s]*vmcdn\.ciner\.com\.tr[^"\'\s]*\.m3u8[^"\'\s]*', html)
    if m:
        # fragman değil, bölüm olan en uzun m3u8
        # galeri ve fragman sayfalarında mp4 oluyor genelde
        long_m=[x for x in m if len(x)>80]
        if long_m: return sorted(long_m, key=len)[-1].replace("\\/","/")
        return m[0].replace("\\/","/")
    mh=re.search(r"data-hope-video='(.*?)'", html)
    if mh:
        try:
            j=json.loads(mh.group(1).replace('&quot;','"').replace("&amp;","&"))
            return j["media"]["m3u8"][0]["src"].replace("\\/","/")
        except: pass
    return None

MANUEL={
    "sevdan-bir-ates": [
        {"num":8, "url":"https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793536249&st=d9a494327d774d3e48f8f8114a94a392", "title":"8. Bolum"},
    ]
}

slugs=["kizilcik-serbeti","sevdan-bir-ates","muhtemel-ask","menekse"]
entries=[]
for slug, items in MANUEL.items():
    for it in items:
        entries.append({"dizi":slug.replace("-"," ").title(),"bolum":it["title"],"url":it["url"],"num":it["num"]})

for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{site}/dizi/{slug}")
    if not html: html=fetch(f"{site}/dizi/{slug}/bolumler")
    soup=BeautifulSoup(html, "html.parser")
    links={}
    for a in soup.find_all("a", href=True):
        h=a["href"].lower()
        # FRAGMAN / GALERI / FOTO ENGELLE
        if "fragman" in h: continue
        if "galeri" in h: continue
        if "fotograf" in h: continue
        if "haber" in h: continue
        if "oyuncu" in h: continue
        if slug not in h: continue
        if "/bolum/" not in h: continue  # sadece gerçek bölüm sayfası /bolum/ içermeli
        if h.startswith("/"): h=site+h
        else: h="https://www.showtv.com.tr"+h if not h.startswith("http") else h
        mm=re.search(r'(\d+)\s*[-.]?\s*bolum', h)
        if not mm: mm=re.search(r'bolum[^0-9]*(\d+)', h)
        num=int(mm.group(1)) if mm else 0
        if num==0: continue
        if h not in links or num>links[h]: links[h]=num

    # son 3
    existing=[e["num"] for e in entries if slug in e["dizi"].lower()]
    sorted_links=sorted(links.items(), key=lambda x:x[1], reverse=True)
    print(f"  bulunan gerçek bölümler: {len(sorted_links)} - {sorted_links[:5]}")
    cnt=0
    for url,num in sorted_links:
        if num in existing: continue
        if cnt>=3: break
        print(f"  -> {url} ({num})")
        bh=fetch(url)
        # fragman sayfası mı kontrol et
        if "fragman" in bh.lower() and "bolum" not in bh.lower().split("fragman")[0][-100:]:
            print(f"    fragman sayfası, atlanıyor")
            continue
        u=extract_m3u8(bh)
        if u and len(u)>60: # gerçek m3u8
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":f"{num}. Bolum","url":u,"num":num})
            print(f"  OK {num}")
            cnt+=1
        time.sleep(0.4)

# son 3'e indir
final={}
for e in entries:
    k=e["dizi"].lower()
    if k not in final: final[k]=[]
    final[k].append(e)

all_final=[]
for k,v in final.items():
    uniq={it["num"]:it for it in v}
    top3=sorted(uniq.values(), key=lambda x:x["num"], reverse=True)[:3]
    all_final.extend(top3)

with open(m3u_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in sorted(all_final, key=lambda x:(x["dizi"], -x["num"])):
        f.write(f'#EXTINF:-1 group-title="{GROUP}",TR: {e["bolum"]} - {e["dizi"]}\n{e["url"]}\n\n')

if not os.path.exists(mirti_file): open(mirti_file,"w").write("#EXTM3U\n")
with open(mirti_file,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(m3u_file,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(mirti_file,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")

print(f"Bitti {len(new)} kayıt - fragman yok")
