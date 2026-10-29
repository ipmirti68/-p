import cloudscraper, re, os, time, json
OUTPUT_FILE="atv_playlist.m3u"
MIRTI_FILE="mirti68.m3u"
BASE_URL="https://www.atv.com.tr"
WORKER="https://mak.sadecenjoy.workers.dev"

scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
scraper.headers.update({"Referer":"https://www.atv.com.tr/","User-Agent":"Mozilla/5.0"})

def fetch(url):
    try:
        r=scraper.get(f"{WORKER}/?url={url}",timeout=25)
        print(f"fetch {url[-50:]} -> {len(r.text)} byte")
        return r.text
    except Exception as e:
        print(f"fetch hata: {e}")
        return ""

# Sadece Alti Ustu Istanbul test
slugs=["alti-ustu-istanbul"]

entries=[]
for slug in slugs:
    print(f"\n{slug} bolumleri aliniyor...")
    # 1. bolumler sayfasi
    html=fetch(f"{BASE_URL}/diziler/{slug}/bolumler")
    if len(html)<1000:
        html=fetch(f"{BASE_URL}/diziler/{slug}")
    
    links=re.findall(r'/diziler/'+re.escape(slug)+r'/bolum/[^"\'\s]+',html)
    uniq=sorted(list(dict.fromkeys(links)))
    print(f"  {len(uniq)} bolum linki bulundu")
    for u in uniq[-5:]:
        print(f"    link: {u}")

    # 0 ise manuel ekle - 18 dahil
    if len(uniq)==0:
        uniq=[f"/diziler/{slug}/bolum/{i}-bolum" for i in range(1,19)]
        print(f"  Manuel liste: {uniq[-3:]}")

    for link in uniq[-10:]: # son 10, 18 dahil
        full=BASE_URL+link if link.startswith("/") else link
        print(f"\nDeniyor: {full}")
        bhtml=fetch(full)
        
        m3u8=None
        # ATV patternleri - 4 yontem
        pats=[
            r'"videoUrl"\s*:\s*"([^"]+m3u8[^"]*)"',
            r'"src"\s*:\s*"([^"]+m3u8[^"]*)"',
            r'source\s*:\s*"([^"]+m3u8[^"]*)"',
            r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        ]
        for pat in pats:
            m=re.search(pat,bhtml)
            if m:
                m3u8=m.group(1).replace("\\/","/").replace("\\u002F","/").replace("\\","")
                print(f"  Pattern {pat[:20]} ile bulundu")
                break
        
        # iframe webtv fallback
        if not m3
