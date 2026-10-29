import cloudscraper, re, os, time
OUTPUT_FILE="atv_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.atv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.atv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=25)
        if len(r.text)>1000: return r.text
    except: pass
    try:
        r=scraper.get(url,timeout=15)
        return r.text
    except: return ""

def extract_atv_m3u8(html):
    # senin verdigin ornek: erbvr.com
    m=re.findall(r'https?://[^"\'\s]*erbvr\.com[^"\'\s]*\.m3u8[^"\'\s]*',html)
    if m: return m[0].replace("\\/","/")
    # genel
    m2=re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',html)
    for u in m2:
        if "erbvr" in u or "atv" in u or "vms" in u:
            return u.replace("\\/","/")
    return None

entries=[]
# SENIN VERDIGIN ATV ORNEGI - Altı Üstü İstanbul
# https -> hxxp yapmissin, duzelttim
MANUEL_ATV = "https://htxkbiqd.erbvr.com/vms/b/ed/37/bed370e4-9d69-4e43-9f14-a0f06d76deda/bed370e4-9d69-4e43-9f14-a0f06d76deda.smil/.m3u8?st=fCvXO6JJBqhmiQSqOCS1Bw&e=1793352335&sid=LfEBink3_EaHevhNMPf_Vg"
entries.append({"dizi":"Alti Ustu Istanbul","bolum":"18. Bolum","url":MANUEL_ATV})
print(f"MANUEL ATV eklendi: Alti Ustu 18 - erbvr")

slugs=["alti-ustu-istanbul","kurulus-osman","bir-gece-masali","can-borcu","karadut","kor-nokta"]
for slug in slugs:
    print(f"\n=== {slug.upper()} ===")
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=list(dict.fromkeys(links))[:6]
    print(f"  {len(uniq)} link")
    if len(uniq)==0:
        uniq=[f"/diziler/{slug}/bolum/{i}-bolum" for i in range(15,19)]
    for link in uniq:
        if "18-bolum" in link and slug=="alti-ustu-istanbul": continue
        full=BASE_URL+link
        bhtml=fetch(full)
        m3u8=extract_atv_m3u8(bhtml)
        if m3u8:
            bm=re.search(r'(\d+)',link)
            bname=f"{bm.group(1)}. Bolum" if bm else "Bolum"
            entries.append({"dizi":slug.replace("-"," ").title(),"bolum":bname,"url":m3u8})
            print(f"  OK {bname} -> {m3u8[:70]}...")
        time.sleep(0.6)

with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for e in entries:
        f.write(f'#EXTINF:-1 group-title="ATV Dizileri",{e["dizi"]} - {e["bolum"]}\n{e["url"]}\n\n')
print(f"\n{OUTPUT_FILE} - {len(entries)} bolum - hepsi erbvr m3u8")

if os.path.exists(MIRTI_FILE):
    with open(OUTPUT_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        blocks=["#EXTINF"+p.strip() for p in ff.read().split("#EXTINF")[1:] if "http" in p]
    with open(MIRTI_FILE,"r",encoding="utf-8",errors="ignore") as ff:
        cont=ff.read(); first=cont.splitlines()[0] if cont else "#EXTM3U"
        old=["#EXTINF"+p.strip() for p in cont.split("#EXTINF")[1:] if "http" in p and "ATV Dizileri" not in p]
    with open(MIRTI_FILE,"w",encoding="utf-8") as out:
        out.write(first+"\n")
        for b in old: out.write(b+"\n\n")
        for b in blocks: out.write(b+"\n\n")
