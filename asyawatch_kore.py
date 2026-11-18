import re
import time
import html
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

# ==========================================
# HANIM KORE DIZILERI - DOGRU VIDEO URL TESTI
# ==========================================

BASE = "https://dizican.cc"
CATEGORY = "https://dizican.cc/ulke/kore-dizileri-izle-hd/"

OUTPUT = "hanim_kore_test.m3u"
REPORT = "hanim_kore_rapor.txt"
GROUP = "🩷◆ HANIM KORE DİZİLERİ ⭕"

MAX_CATEGORY_PAGES = 8
MAX_SHOWS = 250
DELAY = 0.6
MAX_IFRAME_DEPTH = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)

MEDIA_RE = re.compile(
    r"""https?://[^\s"'<>\\]+?\.(?:m3u8|mp4)(?:\?[^\s"'<>\\]*)?""",
    re.I,
)


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def get_response(url):
    response = session.get(url, timeout=25)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response


def get_soup(url):
    return BeautifulSoup(get_response(url).text, "html.parser")


def absolute_http_url(href, base):
    if not href:
        return ""
    url = urljoin(base, html.unescape(href.strip()))
    url, _fragment = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return ""
    return url


def same_site_url(href, base):
    url = absolute_http_url(href, base)
    if not url:
        return ""
    host = (urlparse(url).hostname or "").lower()
    if host not in ("dizican.cc", "www.dizican.cc"):
        return ""
    return url


def is_episode_anchor(a):
    text = clean(a.get_text(" ", strip=True)).lower()
    href = a.get("href") or ""
    return bool(href) and (
        "bölüm" in text
        or "bolum" in text
        or re.search(r"\b\d+\s*[x.]\s*\d+\b", text)
    )


def get_show_links():
    found = {}

    for page in range(1, MAX_CATEGORY_PAGES + 1):
        url = CATEGORY if page == 1 else urljoin(CATEGORY, f"page/{page}/")
        print(f"[KATEGORİ] {page}: {url}")

        try:
            soup = get_soup(url)
        except Exception as exc:
            print(f"[UYARI] Kategori okunamadı: {exc}")
            break

        before = len(found)

        for a in soup.select("a[href]"):
            href = same_site_url(a.get("href"), url)
            if not href:
                continue

            path = urlparse(href).path.lower()
            if "/dizi/" not in path or any(x in path for x in ("/bolum/", "/kategori/")):
                continue

            title = clean(a.get_text(" ", strip=True))
            if title and len(title) > 1:
                found[href] = title

        if len(found) == before and page > 1:
            print("[BİLGİ] Yeni dizi bulunmadı; kategori taraması durdu.")
            break

        time.sleep(DELAY)

    return list(found.items())[:MAX_SHOWS]


def extract_show_info(show_url, fallback_title):
    soup = get_soup(show_url)

    heading = soup.select_one("h1") or soup.select_one("title")
    title = clean(heading.get_text(" ", strip=True)) if heading else fallback_title
    title = re.sub(r"\s*[-|].*$", "", title).strip() or fallback_title

    poster = ""
    for selector in ("meta[property='og:image']", "meta[name='twitter:image']"):
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            poster = absolute_http_url(tag["content"], show_url)
            break

    if not poster:
        img = soup.select_one("img")
        if img:
            poster = absolute_http_url(img.get("data-src") or img.get("src"), show_url)

    desc = ""
    for selector in ("meta[property='og:description']", "meta[name='description']"):
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            desc = clean(tag["content"])
            break

    episodes = {}
    for a in soup.select("a[href]"):
        if is_episode_anchor(a):
            ep_url = same_site_url(a.get("href"), show_url)
            ep_title = clean(a.get_text(" ", strip=True))
            if ep_url and ep_url != show_url:
                episodes[ep_url] = ep_title or "Bölüm"

    for a in soup.select("a[href]"):
        text = clean(a.get_text(" ", strip=True))
        href = same_site_url(a.get("href"), show_url)
        if (
            href
            and href != show_url
            and re.search(r"(sezon|season).*(\d+)", text, re.I)
        ):
            episodes.setdefault(href, text)

    return title, poster, desc, list(episodes.items())


def find_media_in_html(page_html, page_url):
    """Yalnızca sayfada açıkça bulunan m3u8/mp4/video kaynaklarını alır."""
    soup = BeautifulSoup(page_html, "html.parser")
    found = []

    # HTML video/source etiketleri
    for tag in soup.select("video[src], video source[src], source[src]"):
        media_url = absolute_http_url(tag.get("src"), page_url)
        if media_url and re.search(r"\.(m3u8|mp4)(?:$|\?)", media_url, re.I):
            found.append(media_url)

    # Sayfa kaynak kodunda açıkça yazılmış m3u8/mp4 adresleri
    normalized = (
        page_html.replace("\\/", "/")
        .replace("&amp;", "&")
        .replace("\\u0026", "&")
    )
    for match in MEDIA_RE.findall(normalized):
        media_url = absolute_http_url(match.rstrip("),;"), page_url)
        if media_url:
            found.append(media_url)

    # Tekrarlananları sırayı koruyarak temizle
    unique = []
    seen = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def find_media_recursive(page_url, depth=0, visited=None):
    """
    Bölüm sayfasında veya herkese açık iframe içeriğinde açıkça bulunan
    m3u8/mp4 adreslerini arar. Koruma/şifre aşma veya oturum atlatma yapmaz.
    """
    if visited is None:
        visited = set()

    if depth > MAX_IFRAME_DEPTH or page_url in visited:
        return []

    visited.add(page_url)

    try:
        response = get_response(page_url)
    except Exception as exc:
        print(f"    [OKUNAMADI] {page_url}: {exc}")
        return []

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "mpegurl" in content_type or re.search(r"\.m3u8(?:$|\?)", response.url, re.I):
        return [response.url]
    if "video/mp4" in content_type or re.search(r"\.mp4(?:$|\?)", response.url, re.I):
        return [response.url]

    media = find_media_in_html(response.text, response.url)
    if media:
        return media

    # Sayfada iframe varsa herkese açık iframe sayfasını kontrol et.
    soup = BeautifulSoup(response.text, "html.parser")
    for frame in soup.select("iframe[src]"):
        frame_url = absolute_http_url(frame.get("src"), response.url)
        if not frame_url:
            continue

        # javascript:, boş veya sayfa içi adresleri zaten absolute_http_url eler.
        print(f"    [IFRAME] {urlparse(frame_url).hostname}")
        nested = find_media_recursive(frame_url, depth + 1, visited)
        if nested:
            return nested

    return []


def m3u_quote(value):
    return clean(value).replace('"', "'").replace("\r", " ").replace("\n", " ")


def main():
    print("=" * 60)
    print("HANIM KORE DİZİLERİ - VIDEO URL KONTROLÜ")
    print("=" * 60)

    shows = get_show_links()
    if not shows:
        raise RuntimeError("Kore dizisi bulunamadı.")

    entries = []
    report_lines = []
    total_episode_pages = 0
    playable_count = 0
    no_stream_count = 0

    for index, (show_url, fallback_title) in enumerate(shows, 1):
        print(f"[DİZİ {index}/{len(shows)}] {fallback_title}")

        try:
            title, poster, desc, episodes = extract_show_info(show_url, fallback_title)
        except Exception as exc:
            print(f"  [DİZİ HATASI] {exc}")
            report_lines.append(f"DİZİ HATASI | {fallback_title} | {show_url} | {exc}")
            continue

        if not episodes:
            report_lines.append(f"BÖLÜM BULUNAMADI | {title} | {show_url}")
            print("  [UYARI] Bölüm sayfası bulunamadı.")
            continue

        for episode_url, episode_title in episodes:
            total_episode_pages += 1
            display = f"{title} - {episode_title}"
            print(f"  [BÖLÜM] {episode_title}")

            try:
                media_urls = find_media_recursive(episode_url)
            except Exception as exc:
                media_urls = []
                print(f"    [HATA] Video adresi kontrol edilemedi: {exc}")

            if media_urls:
                for media_url in media_urls:
                    info = (
                        f'#EXTINF:-1 tvg-name="{m3u_quote(display)}" '
                        f'tvg-logo="{m3u_quote(poster)}" '
                        f'group-title="{GROUP}",{m3u_quote(display)}'
                    )
                    entries.append(info + "\n" + media_url)
                    playable_count += 1

                report_lines.append(
                    f"VIDEO BULUNDU | {display} | " + " ; ".join(media_urls)
                )
                print(f"    [VIDEO] {len(media_urls)} doğrudan medya adresi bulundu.")
            else:
                no_stream_count += 1
                report_lines.append(
                    f"AKIŞ BULUNAMADI | {display} | Bölüm sayfası: {episode_url}"
                )
                print("    [AKIŞ YOK] Sayfada açık m3u8/mp4 adresi bulunamadı.")

            time.sleep(DELAY)

    # M3U her çalışmada yeniden oluşturulur. Yalnızca açıkça bulunan medya
    # adresleri eklenir; web sayfası adresleri video gibi gösterilmez.
    with open(OUTPUT, "w", encoding="utf-8-sig", newline="\n") as file:
        file.write("#EXTM3U\n")
        if entries:
            file.write("\n".join(entries) + "\n")

    with open(REPORT, "w", encoding="utf-8", newline="\n") as file:
        file.write("\n".join(report_lines) + "\n")

    print("=" * 60)
    print(f"[TAMAM] Taranan dizi: {len(shows)}")
    print(f"[TAMAM] Bölüm sayfası: {total_episode_pages}")
    print(f"[TAMAM] Doğrudan video URL: {playable_count}")
    print(f"[BİLGİ] Akış bulunamayan bölüm: {no_stream_count}")
    print(f"[M3U] {OUTPUT}")
    print(f"[RAPOR] {REPORT}")
    print("[KORUMA] mirti68.m3u dosyasına dokunulmadı.")
    print("[NOT] Koruma/şifre aşılmaz; yalnızca sayfada açıkça yayınlanan medya URL'leri alınır.")


if __name__ == "__main__":
    main()
