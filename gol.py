import base64, re, sys, os, requests, urllib3, warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
urllib3.disable_warnings()
warnings.filterwarnings("ignore")

HOME_URL = "https://golvarmac1.pro/"
OUTPUT_FILENAME = "mirti68.m3u"
GROUP = "🖥beINSPORTS"
STREAM_REFERER = HOME_URL
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/122.0.0.0 Safari/537.36", "Referer": HOME_URL}
PRETTY_NAMES = {"bein sports 1": "beIN Sports 1", "bein sports 2": "beIN Sports 2", "bein sports 3": "beIN Sports 3", "bein sports 4": "beIN Sports 4"}

def pretty(name): return PRETTY_NAMES.get(name.strip().lower(), name.strip())
def make_session():
    s=requests.Session(); s.headers.update(HEADERS)
    s.cookies.set("beget", "begetok", domain="golvarmac1.pro", path="/")
    return s
def fetch_home():
    s=make_session()
    try:
        r=s.get(HOME_URL, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Golvar erisilemiyor: {e}")
        return ""
def parse_items(html):
    items=re.findall(r'<a[^>]+href="([^"]*?/izle/[^"]+)"[^>]*>.*?<strong[^>]*class="name[^"]*"[^>]*>(.*?)</strong>', html, re.S | re.I)
    out,seen=[],set()
    for href,name in items:
        slug=href.split("/izle/",1)[-1].rstrip("/")
        if not slug or slug in seen: continue
        seen.add(slug)
        title=re.sub(r"<[^>]+>","",name).strip() or slug.replace("-"," ").title()
        out.append((title,slug))
    return out
def unpack_packer(html):
    m=re.search(r"\}\('((?:[^'\\]|\\.)*)'\s*,\s*\d+\s*,\s*\d+\s*,\s*'((?:[^'\\]|\\.)*)'\.split\('\|'\)", html)
    if not m: return None
    payload,words=m.group(1),m.group(2).split("|")
    def repl(mo):
        idx=int(mo.group(0))
        return words[idx] if 0 <= idx < len(words) else mo.group(0)
    return re.sub(r"\b\d+\b", repl, payload)
def resolve_source(session, slug):
    watch_url=f"{HOME_URL}channel/watch/{slug}"
    try:
        r2=session.get(watch_url, timeout=20)
        if r2.status_code!=200: return None,None
        m=re.search(r'<iframe[^>]+src=["\']([^"\']+)', r2.text, re.I)
        if not m: return None,None
        src=m.group(1)
        ls_url=(HOME_URL+src.lstrip("/")) if src.startswith("/") else src
        r3=session.get(ls_url, headers={"Referer": watch_url}, timeout=20)
        if r3.status_code!=200: return None,None
        tm=re.search(r"<title>\s*VOLESTREAM\s*(?:-\s*)*(.*?)\s*</title>", r3.text, re.I)
        title=tm.group(1).strip(" -") if tm else None
        text=r3.text
        unpacked=unpack_packer(text) or text
        am=re.search(r'atob\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)', unpacked)
        if am:
            try: unpacked=base64.b64decode(am.group(1)).decode("utf-8","replace")
            except: pass
        sm=re.search(r'source\s*:\s*"(https?://[^"]+)"', unpacked)
        if sm: return title, sm.group(1)
    except: pass
    return None,None
def verify(session, url):
    try:
        r=session.get(url, timeout=15, stream=True)
        if r.status_code!=200: return None
        chunk=next(r.iter_content(256), b"")
        if chunk.decode("utf-8","replace").lstrip().startswith("#EXTM3U"): return url
    except: return None
    return None
def main():
    print("--- Golvar taraniyor ---")
    html=fetch_home()
    if not html: print("Site bos"); sys.exit(0)
    items=parse_items(html)
    print(f"{len(items)} kaynak bulundu")
    if not items: sys.exit(0)
    results=[]
    def work(item):
        title,slug=item
        s=make_session()
        stitle,m3u8=resolve_source(s, slug)
        if not m3u8: return None
        final=verify(s, m3u8)
        if not final: return None
        return (pretty(stitle or title), final)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(work,it):it for it in items}
        for fut in as_completed(futures):
            res=fut.result()
            if res: results.append(res); print(f"  ✅ {res[0]}")
    entries=[]
    seen=set()
    for title,url in results:
        if url in seen: continue
        seen.add(url)
        entries.append(f'#EXTINF:-1 group-title="{GROUP}", {title}\n#EXTVLCOPT:http-referrer={STREAM_REFERER}\n{url}')
    if not entries:
        print("Hic yayin yok, dosya korunuyor")
        sys.exit(0)
    # Dosya yoksa header yaz, varsa sadece ekle
    if not os.path.exists(OUTPUT_FILENAME):
        with open(OUTPUT_FILENAME,"w",encoding="utf-8") as f: f.write("#EXTM3U\n")
    with open(OUTPUT_FILENAME,"a",encoding="utf-8") as f:
        f.write("\n".join(entries)+"\n")
    print(f"✅ {len(entries)} yayin -> {OUTPUT_FILENAME}")
if __name__=="__main__": main()
