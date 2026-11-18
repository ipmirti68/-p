count_before = len(found)
        for a in soup.select("a[href]"):
            href = abs_url(a.get("href"), url)
            if not href or href.rstrip("/") == CATEGORY.rstrip("/"):
                continue
            path = urlparse(href).path.lower()
            # Dizi detay sayfaları genellikle /dizi/slug/ biçiminde.
            if "/dizi/" in path and not any(x in path for x in ("/bolum/", "/kategori/")):
                title = clean(a.get_text(" ", strip=True))
                if title and len(title) > 1:
                    found[href] = title
        if len(found) == count_before and page > 1:
            print("[BİLGİ] Yeni dizi bulunmadı; kategori taraması durdu.")
            break
        time.sleep(DELAY)
    return list(found.items())[:MAX_SHOWS]

def extract_show_info(show_url, fallback_title):
    soup = get_soup(show_url)
    title = clean((soup.select_one("h1") or soup.select_one("title")).get_text(" ", strip=True)) if (soup.select_one("h1") or soup.select_one("title")) else fallback_title
    title = re.sub(r"\s*[-|].*$", "", title).strip() or fallback_title

    poster = ""
    for sel in ("meta[property='og:image']", "meta[name='twitter:image']"):
        tag = soup.select_one(sel)
        if tag and tag.get("content"):
            poster = urljoin(show_url, tag["content"])
            break
    if not poster:
        img = soup.select_one("img")
        if img:
            poster = urljoin(show_url, img.get("data-src") or img.get("src") or "")

    desc = ""
    for sel in ("meta[property='og:description']", "meta[name='description']"):
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

    # Bazı sayfalarda bölüm bağlantısı metninde sezon bilgisi var ama "bölüm" yazmayabilir.
    for a in soup.select("a[href]"):
        txt = clean(a.get_text(" ", strip=True))
        href = abs_url(a.get("href"), show_url)
        if href and href != show_url and re.search(r"(sezon|season).*(\d+)", txt, re.I) and re.search(r"\d+", txt):
            episodes.setdefault(href, txt)

    return title, poster, desc, list(episodes.items())

def main():
    print("=" * 58)
    print("HANIM KORE DİZİLERİ - DIZICAN TEST")
    print("=" * 58)
    shows = get_show_links()
    if not shows:
        raise RuntimeError("Kore dizisi bulunamadı; kaynak sayfa veya site yapısı değişmiş olabilir.")

    entries = []
    total_eps = 0
    for i, (show_url, fallback) in enumerate(shows, 1):
        print(f"[DİZİ {i}/{len(shows)}] {fallback}")
        try:
            title, poster, desc, episodes = extract_show_info(show_url, fallback)
            if episodes:
                for ep_url, ep_title in episodes:
                    display = f"{title} - {ep_title}"
                    info = f'#EXTINF:-1 tvg-name="{display}" tvg-logo="{poster}" group-title="{GROUP}",{display}'
                    if desc:
                        info += f"\n#EXTVLCOPT:description={desc[:350]}"
                    entries.append(info + "\n" + ep_url)
                total_eps += len(episodes)
                print(f"  [OK] {len(episodes)} bölüm bulundu")
            else:
                # Bölüm bağlantısı bulunamayan diziyi de ayrı göster; bölüm sayfası değildir.
                display = f"{title} [DİZİ SAYFASI]"
                entries.append(f'#EXTINF:-1 tvg-name="{display}" tvg-logo="{poster}" group-title="{GROUP}",{display}\n{show_url}')
                print("  [UYARI] Bölüm bağlantısı bulunamadı; dizi sayfası eklendi.")
        except Exception as e:
            print(f"  [HATA] {fallback}: {e}")
        time.sleep(DELAY)

    if not entries:
        raise RuntimeError("M3U girdisi üretilemedi; mevcut listeye dokunulmadı.")

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("#EXTM3U\n")
        f.write("\n".join(entries) + "\n")

    print("-" * 58)
    print(f"[TAMAM] Dizi sayısı: {len(shows)}")
    print(f"[TAMAM] Bulunan bölüm bağlantısı: {total_eps}")
    print(f"[DOSYA] {OUTPUT}")
    print("[NOT] Bunlar web bölüm sayfalarıdır; doğrudan video akışı oldukları garanti edilmez.")
    print("[KORUMA] mirti68.m3u dosyasına kesinlikle dokunulmadı.")

if __name__ == "__main__":
    main()
