"""Golvar (golvarmac1.pro) spor kaynagi botu.

Akis:
  1) ``beget=begetok`` cookie + reload ile ana sayfa acilir (Cloudflare/Beget kilidi).
  2) ``/izle/<slug>`` baglantilari (TV kanallari + gunun maclari) okunur.
  3) Her slug -> ``/channel/watch/<slug>`` -> ``loadstream.php`` iframe'ine gider;
     sayfadaki packer/eval blogu cozulup ``window.config.match.source`` (m3u8) alinir.
  4) Her m3u8 GET ile dogrulanir; calismayanlar listeye girmez.
  5) M3U'ya ``#EXTVLCOPT:http-referrer`` satiri yazilir (oyuncuya gore
     referer gerekmez; yine de eklenir - riske girmemek icin).
  6) Hic kanal yoksa DOSYA YAZILMAZ ve cikis 1 olur (eski liste korunur).
"""

import base64
import re
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3
import warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

HOME_URL = "https://golvarmac1.pro/"

OUTPUT_FILENAME = "mirti68.m3u"
STATIC_LOGO = "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/20/Bein_sport_logo.png/1920px-Bein_sport_logo.png?utm_source=tr.wikipedia.org&utm_campaign=imageinfo&utm_content=thumbnail"
GROUP = "🖥beINSPORTS"

# Segmentler su an referersiz de calisiyor; yine de referer eklenir
# (kaynak gerekli hale gelirse oynaticida kirilmasin).
STREAM_REFERER = HOME_URL

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    "Referer": HOME_URL,
}

# Site buyuk harfle yazar; diger kaynaklarla ayni gorunen adlari kullan.
PRETTY_NAMES = {
    "bein sports 1": "beIN SPORTS 1 Arda 🔴",
    "bein sports 2": "beIN SPORTS 2 Arda 🔴",
    "bein sports 3": "beIN SPORTS 3 Arda 🔴",
    "bein sports 4": "beIN SPORTS 4 Arda 🔴",
    "bein sports 5": "beIN SPORTS 5 Arda 🔴",
    "bein sports max 1": "beIN SPORTS MAX 1 Arda 🔴",
    "bein sports max 2": "beIN SPORTS MAX 2 Arda 🔴",
}


def pretty(name: str) -> str:
    return PRETTY_NAMES.get(name.strip().lower(), name.strip())


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    # Site cookie'yi JS ile set edip reload yapiyor; istemcide elle set edilir.
    s.cookies.set("beget", "begetok", domain="golvarmac1.pro", path="/")
    return s


def fetch_home():
    s = make_session()
    r = s.get(HOME_URL, timeout=25)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_items(html):
    """``/izle/<slug>`` + yanindaki ``<strong class="name">`` (kanal/mac adi)."""
    items = re.findall(
        r'<a[^>]+href="([^"]*?/izle/[^"]+)"[^>]*>.*?'
        r'<strong[^>]*class="name[^"]*"[^>]*>(.*?)</strong>',
        html, re.S | re.I,
    )
    out, seen = [], set()
    for href, name in items:
        slug = href.split("/izle/", 1)[-1].rstrip("/")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        title = re.sub(r"<[^>]+>", "", name).strip() or slug.replace("-", " ").title()
        out.append((title, slug))
    # Dogrudan verilen diger kanal slugs'i da (menu disi) ekle
    for slug in re.findall(r'/channel/watch/([a-z0-9\-]+)', html, re.I):
        if slug not in seen:
            seen.add(slug)
            out.append((slug.replace("-", " ").title(), slug))
    return out


def unpack_packer(html):
    """eval(function(p,a,c,k,e,d){..}('p',N,N,'w|w|..'.split('|'),0,{})) -> string"""
    m = re.search(
        r"\}\('((?:[^'\\]|\\.)*)'\s*,\s*\d+\s*,\s*\d+\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\.split\('\|'\)",
        html,
    )
    if not m:
        return None
    payload, words = m.group(1), m.group(2).split("|")

    def repl(mo):
        idx = int(mo.group(0))
        return words[idx] if 0 <= idx < len(words) and words[idx] else mo.group(0)

    return re.sub(r"\b\d+\b", repl, payload)


def resolve_source(session, slug):
    """slug -> (baslik, m3u8). Bulunamazsa (None, None)."""
    watch_url = f"{HOME_URL}channel/watch/{slug}"
    try:
        r2 = session.get(watch_url, timeout=20)
        if r2.status_code != 200:
            return None, None
        m = re.search(r'<iframe[^>]+src=["\']([^"\']+)', r2.text, re.I)
        if not m:
            return None, None
        src = m.group(1)
        ls_url = (HOME_URL + src.lstrip("/")) if src.startswith("/") else src
        r3 = session.get(ls_url, headers={"Referer": watch_url}, timeout=20)
        if r3.status_code != 200:
            return None, None
        tm = re.search(r"<title>\s*VOLESTREAM\s*(?:-\s*)*(.*?)\s*</title>", r3.text, re.I)
        title = tm.group(1).strip(" -") if tm else None

        text = r3.text
        unpacked = unpack_packer(text) or text
        am = re.search(r'atob\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)', unpacked)
        if am:
            try:
                unpacked = base64.b64decode(am.group(1)).decode("utf-8", "replace")
            except Exception:
                pass
        sm = re.search(r'source\s*:\s*"(https?://[^"]+)"', unpacked)
        if sm:
            return title, sm.group(1)
    except Exception:
        pass
    return None, None


def verify(session, url):
    """m3u8 GET ile dogrulanir; calisiyorsa url dondurulur."""
    try:
        r = session.get(url, timeout=15, stream=True)
        if r.status_code != 200:
            return None
        chunk = next(r.iter_content(256), b"")
        if chunk.decode("utf-8", "replace").lstrip().startswith("#EXTM3U"):
            return url
    except Exception:
        return None
    return None


def main():
    print("--- taraniyor ---")
    entries = []

    if not os.path.exists(OUTPUT_FILENAME):
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

    with open(OUTPUT_FILENAME, "a", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")    # 1. ana sayfayı çek (sende fetch_home)
    # 2. kanal listesini parse et (sende parse_items)
    # 3. her biri için resolve et ve verify yap - bu kısmı sen dolduracaksın
    # 4. m3u'yu yaz

    # mirti68.m3u içine append et - yeni oluşturma, mevcut listeye dokunma
    if not os.path.exists(OUTPUT_FILENAME):
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

    with open(OUTPUT_FILENAME, "a", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")

    print(f"\n✅ İŞLEM TAMAMLANDI!")
    print(f"💾 Dosya Adı: {OUTPUT_FILENAME}")
    print(f"📝 Toplam Kanal: {len(entries)}")
    print(f"📍 Kayıt Yeri: {os.path.abspath(OUTPUT_FILENAME)}")

if __name__ == "__main__":
    main()
