import requests
import re

# --- Ayarlar ---
CHANNELS_API = "https://bosssports1078.com/api/channels"
MATCHES_API = "https://bosssports1078.com/api/matches"
BASE_SITE = "https://bosssports1078.com/"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REFERER = "https://bosssports1078.com/"

CHANNELS_FILE = "boss68.m3u"
MATCHES_FILE = "boss2.m3u"

# Sadece bu kategoriler alınacak (küçük harfle, kısmi eşleşme)
ALLOWED_CATEGORIES = ["football",  "futbol"]

# Maçlar için tek grup adı
MATCH_GROUP = "Canlı Maçlar"


def fetch_json(url):
    """URL'den JSON çeker, hata olursa None döner."""
    headers = {
        "User-Agent": USER_AGENT,
        "referer": BASE_SITE,
        "accept": "application/json",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
    except Exception as e:
        print(f"❌ İstek hatası ({url}): {e}")
        return None

    print(f"[{url}] Status: {r.status_code}, Uzunluk: {len(r.text)}")
    if r.status_code != 200:
        print(f"   Yanıtın başı: {r.text[:300]}")
        return None
    try:
        return r.json()
    except Exception as e:
        print(f"❌ JSON parse hatası ({url}): {e}")
        print(f"   Yanıtın başı: {r.text[:300]}")
        return None


def get_stream_url(item):
    """Bir kayıttan yayın linkini çıkarır: streams[].url (isPlayed öncelikli) -> videoid."""
    streams = item.get("streams", [])
    if streams:
        played = next((s for s in streams if s.get("isPlayed")), None)
        chosen = played or streams[0]
        url = chosen.get("url", "")
        if url:
            return url
    return item.get("videoid", "")


def clean_league(league):
    """'21:00 | | UEFA Şampiyonlar Ligi' -> ('21:00', 'UEFA Şampiyonlar Ligi')"""
    if not league:
        return "", ""
    parts = [p.strip() for p in league.split("|") if p.strip()]
    if not parts:
        return "", league.strip()

    time_val = ""
    if re.match(r"^\d{1,2}:\d{2}$", parts[0]):
        time_val = parts[0]
        league_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    else:
        league_name = " ".join(parts)
    return time_val, league_name


def is_allowed_category(category):
    """Kategori futbol/voleybol/basketbol mu?"""
    cat = (category or "").lower()
    return any(key in cat for key in ALLOWED_CATEGORIES)


def write_m3u(entries, filename):
    """entries: (group_title, title, stream_url) listesi"""
    lines = ["#EXTM3U"]
    for group_title, title, url in entries:
        lines.append(f'#EXTINF:-1 group-title="{group_title}",{title}')
        lines.append(f"#EXTVLCOPT:http-user-agent={USER_AGENT}")
        lines.append(f"#EXTVLCOPT:http-referrer={REFERER}")
        lines.append(url)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_channels():
    """boss.m3u -> 7/24 kanallar"""
    payload = fetch_json(CHANNELS_API)
    if not payload:
        write_m3u([], CHANNELS_FILE)
        print("⚠️  Kanallar çekilemedi, boş boss.m3u yazıldı.")
        return

    channels = payload.get("data", [])
    print(f"Kanal sayısı: {len(channels)}")

    entries = []
    for ch in channels:
        title = (ch.get("home") or "").strip()
        url = get_stream_url(ch)
        if not title or not url:
            continue
        group = ch.get("league") or ch.get("category") or "7/24 Kanallar"
        entries.append((group, title, url))

    write_m3u(entries, CHANNELS_FILE)
    print(f"✅ {len(entries)} kanal -> {CHANNELS_FILE}")


def build_matches():
    """boss2.m3u -> sadece futbol/voleybol/basketbol, tek grup, tekrarsız"""
    payload = fetch_json(MATCHES_API)
    if not payload:
        write_m3u([], MATCHES_FILE)
        print("⚠️  Maçlar çekilemedi, boş boss2.m3u yazıldı.")
        return

    matches = payload.get("data", [])
    print(f"Ham maç kaydı sayısı: {len(matches)}")

    entries = []
    seen = set()
    skipped_category = 0

    for m in matches:
        category = (m.get("category") or "").strip()

        # Kategori filtresi
        if not is_allowed_category(category):
            skipped_category += 1
            continue

        match_id = m.get("id") or m.get("public_id")
        if match_id and match_id in seen:
            continue

        home = (m.get("home") or "").strip()
        away = (m.get("away") or "").strip()
        url = get_stream_url(m)

        if not home or not url:
            continue

        if away and away.lower() != "away":
            title = f"{home} - {away}"
        else:
            title = home

        time_val, league_name = clean_league(m.get("league", ""))
        extra = " | ".join(x for x in [time_val, league_name] if x)
        if extra:
            title = f"{title} ({extra})"

        if match_id:
            seen.add(match_id)
        entries.append((MATCH_GROUP, title, url))

    print(f"Kategori dışı atlanan: {skipped_category}")
    write_m3u(entries, MATCHES_FILE)
    print(f"✅ {len(entries)} maç (futbol/voleybol/basketbol, tekrarsız) -> {MATCHES_FILE}")


def main():
    print("=" * 50)
    print("KANALLAR")
    print("=" * 50)
    build_channels()

    print("=" * 50)
    print("MAÇLAR")
    print("=" * 50)
    build_matches()


if __name__ == "__main__":
    main()
