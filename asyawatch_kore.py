
import re
import time
import html
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ==========================================
# HANIM KORE DİZİLERİ AYARLARI
# ==========================================

BASE = "https://dizican.cc"
CATEGORY = "https://dizican.cc/ulke/kore-dizileri-izle-hd/"

OUTPUT = "hanim_kore_test.m3u"
GROUP = "🩷◆ HANIM KORE DİZİLERİ ⭕"

MAX_CATEGORY_PAGES = 8
MAX_SHOWS = 250
DELAY = 0.6

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"
}

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    response = session.get(url, timeout=25)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def clean(value):
    return re.sub(
        r"\s+", " ",
        html.unescape(value or "")
    ).strip()


def abs_url(href, base):
    url = urljoin(base, href or "")
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return ""

    if parsed.netloc.lower() not in (
        "dizican.cc", "www.dizican.cc"
    ):
        return ""

    return url.split("#")[0]


def is_episode_anchor(a):
    text = clean(a.get_text(" ", strip=True)).lower()
    href = a.get("href") or ""

    return (
        ("bölüm" in text or "bolum" in text
         or re.search(r"\b\d+\s*[x.]\s*\d+\b", text))
        and bool(href)
    )




def get_show_links():
    found = {}

    for page in range(1, MAX_CATEGORY_PAGES + 1):
        url = CATEGORY if page == 1 else urljoin(
            CATEGORY, f"page/{page}/"
        )

        print(f"[KATEGORİ] {page}: {url}")

        try:
            soup = get_soup(url)
        except Exception as e:
            print(f"[UYARI] Kategori okunamadı: {e}")
            break

        count_before = len(found)

        for a in soup.select("a[href]"):
            href = abs_url(a.get("href"), url)

            if not href or href.rstrip("/") == CATEGORY.rstrip("/"):
                continue

            path = urlparse(href).path.lower()

            if "/dizi/" in path and not any(
                x in path for x in ("/bolum/", "/kategori/")
            ):
                title = clean(a.get_text(" ", strip=True))

                if title and len(title) > 1:
                    found[href] = title

        if len(found) == count_before and page > 1:
            print("[BİLGİ] Yeni dizi bulunmadı.")
            break

        time.sleep(DELAY)

    return list(found.items())[:MAX_SHOWS]


def extract_show_info(show_url, fallback_title):
    soup = get_soup(show_url)

    heading = soup.select_one("h1") or soup.select_one("title")

    if heading:
        title = clean(heading.get_text(" ", strip=True))
    else:
        title = fallback_title

    title = re.sub(r"\s*[-|].*$", "", title).strip()
    title = title or fallback_title

    poster = ""

    for sel in (
        "meta[property='og:image']",
        "meta[name='twitter:image']"
    ):
        tag = soup.select_one(sel)

        if tag and tag.get("content"):
            poster = urljoin(show_url, tag["content"])
            break

    if not poster:
        img = soup.select_one("img")

        if img:
            poster = urljoin(
                show_url,
                img.get("data-src") or img.get("src") or ""
            )

    desc = ""

    for sel in (
        "meta[property='og:description']",
        "meta[name='description']"
    ):
        tag = soup.select_one(sel)

        if tag and tag.get("content"):
            desc = clean(tag["content"])
            break

    episodes = {}

    for a in soup.select("a[href]"):
        if not is_episode_anchor(a):
            continue

        ep_url = abs_url(a.get("href"), show_url)
        ep_title = clean(a.get_text(" ", strip=True))

        if ep_url and ep_url != show_url:
            episodes[ep_url] = ep_title or "Bölüm"

    for a in soup.select("a[href]"):
        txt = clean(a.get_text(" ", strip=True))
        href = abs_url(a.get("href"), show_url)

        if (
            href
            and href != show_url
            and re.search(r"(sezon|season).*(\d+)", txt, re.I)
            and re.search(r"\d+", txt)
        ):
            episodes.setdefault(href, txt)

    return title, poster, desc, list(episodes.items())


def main():
    print("=" * 58)
    print("HANIM KORE DİZİLERİ - DIZICAN TEST")
    print("=" * 58)

    shows = get_show_links()

    if not shows:
        raise RuntimeError(
            "Kore dizisi bulunamadı. Kaynak sayfa kontrol edilmeli."
        )

    entries = []
    total_eps = 0

    for i, (show_url, fallback) in enumerate(shows, 1):
        print(f"[DİZİ {i}/{len(shows)}] {fallback}")

        try:
            title, poster, desc, episodes = extract_show_info(
                show_url, fallback
            )

            if episodes:
                for ep_url, ep_title in episodes:
                    display = f"{title} - {ep_title}"

                    info = (
                        f'#EXTINF:-1 tvg-name="{display}" '
                        f'tvg-logo="{poster}" '
                        f'group-title="{GROUP}",{display}'
                    )

                    if desc:
                        info += (
                            f"\n#EXTVLCOPT:description={desc[:350]}"
                        )

                    entries.append(info + "\n" + ep_url)

                total_eps += len(episodes)
                print(f"  [OK] {len(episodes)} bölüm bulundu")

            else:
                display = f"{title} [DİZİ SAYFASI]"

                entries.append(
                    f'#EXTINF:-1 tvg-name="{display}" '
                    f'tvg-logo="{poster}" '
                    f'group-title="{GROUP}",{display}\n{show_url}'
                )

                print("  [UYARI] Bölüm bağlantısı bulunamadı.")

        except Exception as e:
            print(f"  [HATA] {fallback}: {e}")

        time.sleep(DELAY)

    if not entries:
        raise RuntimeError(
            "M3U girdisi üretilemedi. Mevcut liste korunuyor."
        )

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("#EXTM3U\n")
        f.write("\n".join(entries) + "\n")

    print("=" * 58)
    print(f"[TAMAM] Dizi sayısı: {len(shows)}")
    print(f"[TAMAM] Bölüm bağlantısı: {total_eps}")
    print(f"[DOSYA] {OUTPUT}")
    print("[KORUMA] mirti68.m3u dosyasına dokunulmadı.")
    print("[BİLGİ] Bölüm sayfaları doğrudan video akışı olmayabilir.")


if __name__ == "__main__":
    main()
