import cloudscraper, re, os, json, time
from bs4 import BeautifulSoup

M3U="showtv.m3u"
MIRTI="mirti68.m3u"
GROUP="SHOW Dizileri"
BASE="https://www.showtv.com.tr"

def get_vmcdn(url):
    try:
        scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
        r=scraper.get(url, timeout=20)
        txt=r.text
        # 1. direkt vmcdn m3u8
        m=re.search(r'(https://vmcdn\.ciner\.com\.tr/ht/[^\s"\'<>]+\.m3u8\?e=[^"\'\s]+&st=[^"\'\s]+)', txt)
        if m:
            return m.group(1).replace('\\/', '/')
        # 2. data-hope-video içinde
        m2=re.search(r'data-hope-video=\'([^\']+)\'', txt)
        if m2:
            j=json.loads(m2.group(1).replace('&quot;','"').replace('&amp;','&'))
            if 'media' in j and 'm3u8' in j['media']:
                return j['media']['m3u8'][0]['src'].replace('\\/', '/')
        # 3. genel m3u8
        m3=re.search(r'(https?://[^"\'\s]*vmcdn[^"\'\s]*\.m3u8[^"\'\s]*)', txt)
        if m3:
            return m3.group(1).replace('\\/', '/')
    except Exception as e:
        print(f"  vmcdn hata {url[-30:]} {e}")
    return None

def get_bolum_links():
    scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
    r=scraper.get(f"{BASE}/diziler", timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')
    links=[]
    for a in soup.find_all('a', href=True):
        href=a['href']
        if '/dizi/tum_bolumler/sevdan-bir-ates' in href or '/dizi/tum_bolumler/kizilcik-serbeti' in href or '/dizi/tum_bolumler/muhtemel-ask' in href:
            full=href if href.startswith('http') else BASE+href
            links.append(full)
    # en azından son 3
    # sevdan-bir-ates için senin verdiğin sayfalar
    links+=[
        "https://www.showtv.com.tr/dizi/tum_bolumler/sevdan-bir-ates-sezon-1-bolum-8-izle/135714",
        "https://www.showtv.com.tr/dizi/tum_bolumler/sevdan-bir-ates-sezon-1-bolum-7-izle/135500",
        "https://www.showtv.com.tr/dizi/tum_bolumler/sevdan-bir-ates-sezon-1-bolum-6-izle/135300",
    ]
    # tekrar temizle
    uniq=[]
    seen=set()
    for l in links:
        if l not in seen:
            seen.add(l)
            uniq.append(l)
    return uniq[:6]

print("SHOW - SHOW Dizileri")
scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
bolum_urls=get_bolum_links()
entries=[]

# manuel taze - senin verdiğin hep dursun
MANUEL="https://vmcdn.ciner.com.tr/ht/2026/10/28/01418A5689B618D9BA980AE927ECD0EC.m3u8?e=1793551971&st=6f8dcf39f79e70a0322648c92043eb04"
entries.append(("Sevdan Bir Ates","8. Bolum",MANUEL))
print(f"MANUEL 8 eklendi {MANUEL[:60]}...")

for url in bolum_urls:
    if 'sevdan-bir-ates-sezon-1-bolum-8' in url: continue # manuel var
    print(f" -> {url}")
    m3u8=get_vmcdn(url)
    if m3u8:
        # numara çıkar
        m=re.search(r'bolum-(\d+)-', url)
        num=m.group(1) if m else "B"
        dizi="Sevdan Bir Ates" if "sevdan-bir-ates" in url else "Kizilcik Serbeti" if "kizilcik" in url else "Muhtemel Ask"
        entries.append((dizi, f"{num}. Bolum", m3u8))
        print(f"   OK {num}")
    time.sleep(0.5)

# yaz
poster="https://showtv.mncdn.com/mnresize/1180/665/upload/diziler/sevdan-bir-ates/afis.jpg"
with open(M3U,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for dizi,bolum,m3u8 in entries:
        f.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{GROUP}",TR: {dizi} - {bolum}\n{m3u8}\n\n')

print(f"{M3U} -> {len(entries)}")

if not os.path.exists(MIRTI): open(MIRTI,"w").write("#EXTM3U\n")
cont=open(MIRTI,"r",encoding="utf-8",errors="ignore").read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
new=["#EXTINF"+p for p in open(M3U,"r",encoding="utf-8",errors="ignore").read().split("#EXTINF")[1:] if "http" in p]
open(MIRTI,"w",encoding="utf-8").write(first+"\n"+"\n\n".join([b.strip() for b in old+new])+"\n")
print(f"{MIRTI} {len(new)} kayit")
