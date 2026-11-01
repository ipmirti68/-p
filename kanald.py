import os, re, time
m3u="kanald_playlist.m3u"
mirti="mirti68.m3u"
GROUP="KANALD Dizileri"
BASE="https://www.kanald.com.tr"

def get_m3u8(url):
    if not url.startswith("http"): return None
    try:
        import cloudscraper
        scraper=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','desktop':True})
        r=scraper.get(url, timeout=15)
        m=re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r.text)
        if m: return m.group(0).replace('\\/', '/')
        # worker embed
        em=re.search(r'itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r.text)
        if em:
            import requests
            wr=f"https://mak.sadecenjoy.workers.dev/?url={em.group(1)}"
            r2=scraper.get(wr, timeout=15)
            m2=re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r2.text)
            if m2: return m2.group(0).replace('\\/', '/')
    except: return None
    return None

WANTED={
    "uzak-sehir": 32,
    "haysiyet": 5,
    "guller-ve-gunahlar": 10,
    "daha-17": 4
}

entries=[]
for slug,last in WANTED.items():
    print(f"\n=== {slug} son {last} ===")
    for num in range(last, last-3, -1):
        if num<=0: continue
        # Kanal D'de URL genelde /diziler/{slug}/bolum/{num}-bolum
        url=f"{BASE}/diziler/{slug}/bolum/{num}-bolum"
        print(f"  -> {url}")
        m3u8=get_m3u8(url)
        if m3u8:
            entries.append((slug.replace("-"," ").title(), num, m3u8))
            print(f"  OK {num}")
        else:
            print(f"  yok, dene izle")
            url2=f"{BASE}/diziler/{slug}/bolum/{num}-bolum-izle"
            m3u8=get_m3u8(url2)
            if m3u8:
                entries.append((slug.replace("-"," ").title(), num, m3u8))
                print(f"  OK {num} izle")
        time.sleep(0.5)

# KESİN YAZ - 0 kalsa bile dosya oluşsun
with open(m3u,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    if not entries:
        print("  UYARI 0 bulundu, bos dosya degil placeholder yaziliyor")
        # en azından 1 tane placeholder ki mirti bozulmasin
        f.write('#EXTINF:-1 group-title="KANALD Dizileri",Uzak Sehir - 1. Bolum\nhttps://example.com/placeholder.m3u8\n\n')
    for d,n,u in entries:
        f.write(f'#EXTINF:-1 group-title="{GROUP}",{d} - {n}. Bolum\n{u}\n\n')

print(f"{m3u} -> {len(entries)} bolum")

if not os.path.exists(mirti): open(mirti,"w").write("#EXTM3U\n")
with open(mirti,"r",encoding="utf-8",errors="ignore") as ff: cont=ff.read()
first=cont.splitlines()[0] if cont else "#EXTM3U"
old=["#EXTINF"+p for p in cont.split("#EXTINF")[1:] if "http" in p and GROUP not in p]
with open(m3u,"r",encoding="utf-8",errors="ignore") as ff: new=["#EXTINF"+p for p in ff.read().split("#EXTINF")[1:] if "http" in p]
with open(mirti,"w",encoding="utf-8") as out:
    out.write(first+"\n")
    for b in old: out.write(b.strip()+"\n\n")
    for b in new: out.write(b.strip()+"\n\n")
print(f"mirti68.m3u {len(new)} kayit")
