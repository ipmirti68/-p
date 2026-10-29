import cloudscraper, re, os, time
OUTPUT_FILE="kanald_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.kanald.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.kanald.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        # Kanal D sadece WORKER ile geliyor, direkt bos donuyor
        r=scraper.get(f"{WORKER}/?url={url}",timeout=30)
        print(f"fetch {url[-50:]} -> {len(r.text)} byte")
        return r.text
    except Exception as e:
        print(f"fetch hata {e}")
        return ""

# Sadece Haysiyet test
slugs=["haysiyet"]

entries=[]
for slug in slugs:
    print(f"\n=== {slug.upper()} 8. BOLUM TEST ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    if len(html)<1000:
        html=fetch(f"{BASE_URL}/diziler/{slug}")
    
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    # Kanal D linkler /diziler/haysiyet/8-bolum gibi de olabiliyor
    if not links:
        links=re.findall(r'/diziler/'+re.escape(slug)+r'/[^"\'\s]*bolum[^"\'\s]*',html)
    
    uniq=sorted(list(dict.fromkeys(links)))
    print(f"  Bulunan: {len(uniq)}")
    for u in uniq:
        print(f"    {u}")

    # Kanal D'de 8. bolum cok yeni, listede yoksa manuel ekle
    if len(uniq)<8:
        uniq=[f"/diziler/{slug}/bolum/{i}-bolum" for i in range(1,9)]
        uniq.append(f"/diziler/{slug}/8-bolum")
        uniq.append(f"/diziler/{slug}/bolum/8-bolum")
        print(f"  Manuel liste eklendi, son 3: {uniq[-3:]}")

    for link in uniq[-5:]: # son 5 - 8. bolum dahil
        full=BASE_URL+link if link.startswith("/") else link
        print(f"\nDeniyor: {full}")
        bhtml=fetch(full)
        if len(bhtml)<1000:
            print(f"  BOS HTML, devam")
            continue

        m3u8=None
        # Kanal D m3u8 patternleri - senin STAR pattern gibi
        pats=[
            r'"videoUrl"\s*:\s*"([^"]+m3u8[^"]*)"',
            r'"src"\s*:\s*"([^"]+m3u8[^"]*)"',
            r'file\s*:\s*"([^"]+m3u8[^"]*)"',
            r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        ]
        for pat in pats:
            m=re.search(pat,bhtml)
            if m:
                m3u8=m.group(1).replace("\\/","/").replace("\\u002F","/").replace("\\","")
                print(f"  Pattern ile bulundu: {pat[:30]}")
                break
        
        # Kanal D embed
        if not m3u8:
            m_emb=re.search(r'embedURL|iframe[^>]+src=["\']([^"\']+)["\']',bhtml)
            if m_emb:
                emb=m_emb.group(1)
                if emb.startswith("//"): emb="https:"+emb
                if not emb.startswith("http"): emb=BASE_URL+emb
                print(f"  Embed deneniyor: {emb[:80]}")
                bhtml2=fetch(emb)
                m2=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',bhtml2)
                if m2: m3u8=m2[0].replace("\\/","/")

        if m3u8 and ".m3u8" in m3u8:
            bm=re.search(r'(\d+)[-_]?bolum',link,re.I)
            bname=f"{bm.group(1)}. Bolum" if bm else "8. Bolum (Son Bolum)"
            entries.append({"dizi":"Haysiyet","bolum":bname,"url":m3u8})
            print(f"  OK {bname} -> {m3u8[:80]}")
        else:
            print(f"  m3u8 YOK, HTML baslangic: {bhtml[:300]}")
        time.sleep(1)

print(f"\n{OUTPUT_FILE} - {len(entries)} bolum")
with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="KANALD Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')

# mirti68'e ekle
if os.path.exists(MIRTI_FILE):
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "KANALD Dizileri" not in p and "Haysiyet" not in p]
    with open(MIRTI_FILE,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
    print(f"Bitti! {len(old)} eski + {len(blocks)} KANALD - Haysiyet 8 icinde")
