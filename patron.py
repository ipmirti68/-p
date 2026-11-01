
import requests
import urllib3
import re
import os
from urllib.parse import urlparse, urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================================================
# KAYNAKLAR
# ==================================================

REDIRECT_SOURCE_URL = (
    "http://raw.githack.com/eniyiyayinci/redirect-cdn/main/inattv.html"
)

DOMAIN_API_URL = "https://patronsports2.cfd/domain.php"
MATCHES_API_URL = "https://patronsports2.cfd/matches.php"

OUTPUT_FILE = "mirti68.m3u"
GROUP_NAME = "🖥beINSPORTS"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
    )
}

# ==================================================
# SABİT KANALLAR
# ==================================================

STATIC_CHANNELS = [
    ("patron", "BEIN SPORTS 1", "beinsports1.png"),
    ("b2", "BEIN SPORTS 2", "beinsports2.png"),
    ("b3", "BEIN SPORTS 3", "beinsports3.png"),
    ("b4", "BEIN SPORTS 4", "beinsports4.png"),
    ("b5", "BEIN SPORTS 5", "beinsports5.png"),
    ("bm1", "BEIN SPORTS MAX 1", "beinsportsmax1.png"),
    ("bm2", "BEIN SPORTS MAX 2", "beinsportsmax2.png"),
    ("ss", "S SPORT", "ssport1.png"),
    ("ss2", "S SPORT 2", "ssport2.png"),
    ("smarts", "SMART SPOR", "smartspor.png"),
    ("smarts2", "SMART SPOR 2", "smartspor2.png"),
    ("t1", "TİVİBU SPOR 1", "tivibu1.png"),
    ("t2", "TİVİBU SPOR 2", "tivibu2.png"),
    ("t3", "TİVİBU SPOR 3", "tivibu3.png"),
    ("t4", "TİVİBU SPOR 4", "tivibu4.png"),
    ("trtspor", "TRT SPOR", "trtspornew.png"),
    ("trtyildiz", "TRT SPOR YILDIZ", "trtspor2.png"),
]

# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def get_base_url():
    try:
        response = requests.get(
            DOMAIN_API_URL,
            headers=HEADERS,
            timeout=15,
            verify=False
        )
        response.raise_for_status()

        data = response.json()
        base_url = data.get("baseurl", "").strip()

        if base_url:
            base_url = base_url.replace("\\", "").rstrip("/") + "/"
            print("Base URL:", base_url)
            return base_url

    except Exception as error:
        print("Domain API hatası:", error)

    parsed = urlparse(MATCHES_API_URL)
    return f"{parsed.scheme}://{parsed.netloc}/"


def get_referrer():
    try:
        response = requests.get(
            REDIRECT_SOURCE_URL,
            headers=HEADERS,
            timeout=15
        )
        response.raise_for_status()

        matches = re.findall(
            r'''href=["'](https?://[^"']+\.cfd(?:/[^"']*)?)["']''',
            response.text,
            re.IGNORECASE
        )

        if matches:
            return matches[0].rstrip("/")

    except Exception as error:
        print("Redirect kaynağı hatası:", error)

    parsed = urlparse(MATCHES_API_URL)
    return f"{parsed.scheme}://{parsed.netloc}"


def make_stream_url(base_url, channel_id):
    return urljoin(
        base_url,
        f"ch.html?id={channel_id}"
    )


def clean(value):
    return str(value or "").strip()


def make_extinf(name, logo, group=GROUP_NAME):
    return (
        f'#EXTINF:-1 group-title="{group}" '
        f'tvg-logo="{logo}",{name}'
    )


# ==================================================
# MAÇLARI AL
# ==================================================

def get_matches():
    matches_list = []

    try:
        print("Maç API'sine bağlanılıyor...")

        response = requests.get(
            MATCHES_API_URL,
            headers=HEADERS,
            timeout=20,
            verify=False
        )
        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            data = data.get("matches", [])

        print("API maç sayısı:", len(data))

        for match in data:
            url_path = clean(match.get("URL"))

            id_match = re.search(r"[?&]id=([^&]+)", url_path)

            if not id_match:
                continue

            channel_id = id_match.group(1)

            home = clean(match.get("HomeTeam"))
            away = clean(match.get("AwayTeam"))

            if not home and not away:
                continue

            league = clean(match.get("league")) or "Spor"
            match_time = clean(match.get("Time"))

            home_logo = clean(match.get("HomeLogo"))
            away_logo = clean(match.get("AwayLogo"))

            logo = home_logo or away_logo

            name = f"{home} - {away}"

            if match_time:
                name += f" [{match_time}]"

            matches_list.append({
                "id": channel_id,
                "name": name,
                "logo": logo,
                "league": league
            })

            if home_logo and away_logo:
                print(f"✓ {name}: İki logo mevcut")
            elif logo:
                print(f"✓ {name}: Tek logo mevcut")
            else:
                print(f"✓ {name}: Logo yok")

    except Exception as error:
        print("Maç API hatası:", error)

    return matches_list


# ==================================================
# SABİT KANALLARI HAZIRLA
# ==================================================

def get_static_channels(base_url):
    channels = []

    for channel_id, name, logo_file in STATIC_CHANNELS:

        logo_url = (
            f"https://patronsports1.cfd/img/{logo_file}"
        )

        stream_url = make_stream_url(
            base_url,
            channel_id
        )

        channels.append({
            "name": name,
            "logo": logo_url,
            "url": stream_url
        })

    return channels


# ==================================================
# ESKİ M3U DOSYASINI KORU
# ==================================================

def read_old_playlist():
    if not os.path.exists(OUTPUT_FILE):
        return []

    try:
        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            lines = file.readlines()

        preserved = []
        skip = False

        for line in lines:
            if line.startswith("#EXTINF:"):
                skip = GROUP_NAME in line
            elif line.startswith("#EXTM3U"):
                continue

            if not skip:
                preserved.append(line.rstrip("\n"))

        return preserved

    except Exception as error:
        print("Eski liste okunamadı:", error)
        return []


# ==================================================
# M3U OLUŞTUR
# ==================================================

def main():

    print("=" * 45)
    print("SPOR KANALLARI VE MAÇLAR HAZIRLANIYOR")
    print("=" * 45)

    base_url = get_base_url()
    referrer = get_referrer()

    print("Base URL:", base_url)
    print("Referrer:", referrer)

    matches = get_matches()
    static_channels = get_static_channels(base_url)

    old_lines = read_old_playlist()

    output = ["#EXTM3U"]

    # Önce sabit spor kanalları
    for channel in static_channels:

        output.append(
            make_extinf(
                channel["name"],
                channel["logo"]
            )
        )

        output.append(channel["url"])

    # Sonra maç yayınları
    for match in matches:

        stream_url = make_stream_url(
            base_url,
            match["id"]
        )

        output.append(
            make_extinf(
                match["name"],
                match["logo"],
                f"{GROUP_NAME} | {match['league']}"
            )
        )

        output.append(stream_url)

    # Diğer kategorileri koru
    output.extend(old_lines)

    # Dosyayı yeniden oluştur
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        file.write("\n".join(output) + "\n")

    print("=" * 45)
    print("İŞLEM TAMAMLANDI")
    print("Sabit kanal:", len(static_channels))
    print("Maç sayısı:", len(matches))
    print("Dosya:", OUTPUT_FILE)
    print("=" * 45)


if __name__ == "__main__":
    main()
        </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports4.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=b5" data-id="channel_5">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS 5</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports5.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=bm1" data-id="channel_6">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS MAX 1</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsportsmax1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=bm2" data-id="channel_7">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS MAX 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsportsmax2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=ss" data-id="channel_8">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">S SPORT</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/ssport1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=ss2" data-id="channel_9">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">S SPORT 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/ssport2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=smarts" data-id="channel_10">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">SMART SPOR</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/smartspor.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=smarts2" data-id="channel_11">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">SMART SPOR 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/smartspor2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t1" data-id="channel_12">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 1</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t2" data-id="channel_13">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t3" data-id="channel_14">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 3</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu3.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t4" data-id="channel_15">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 4</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu4.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=trtspor" data-id="channel_16">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TRT SPOR</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/trtspornew.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=trtyildiz" data-id="channel_17">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TRT SPOR YILDIZ</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/trtspor2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=trt1" data-id="channel_18">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="timport requests
import urllib3
import json
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# KAYNAKLAR
REDIRECT_SOURCE_URL = "http://raw.githack.com/eniyiyayinci/redirect-cdn/main/inattv.html"
DOMAIN_API_URL = "https://patronsports2.cfd/domain.php"
MATCHES_API_URL = "https://patronsports2.cfd/matches.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def get_base_url_with_fallback():
    """Base URL'i al, başarısız olursa alternatif yöntemler dene"""
    
    # 1. Yöntem: Domain API'si
    try:
        r = requests.get(DOMAIN_API_URL, headers=HEADERS, timeout=10, verify=False)
        data = r.json()
        base_url = data.get("baseurl", "")
        if base_url:
            base_url = base_url.replace("\\", "").rstrip('/')
            print(f"✅ Domain API'den base URL alındı: {base_url}")
            return base_url + "/"
    except Exception as e:
        print(f"⚠️ Domain API hatası: {e}")
    
    # 2. Yöntem: matches.php'den domain çıkarımı
    try:
        from urllib.parse import urlparse
        parsed = urlparse(MATCHES_API_URL)
        base_url = f"{parsed.scheme}://{parsed.netloc}/"
        print(f"⚠️ Matches API domain'i base URL olarak kullanılıyor: {base_url}")
        return base_url
    except:
        pass
    
    print("❌ Base URL alınamadı!")
    return None

def get_referrer_with_fallback():
    """Referrer adresini al, başarısız olursa alternatifler dene"""
    
    # 1. Yöntem: Redirect kaynağı
    try:
        r = requests.get(REDIRECT_SOURCE_URL, headers=HEADERS, timeout=10)
        content = r.text
        
        # .cfd uzantılı linkleri bul
        cfd_matches = re.findall(r'href="(https?://[^"]+\.cfd)[/"]', content)
        if cfd_matches:
            referrer = cfd_matches[0].rstrip('/')
            print(f"✅ Redirect'ten referrer alındı: {referrer}")
            return referrer
    except Exception as e:
        print(f"⚠️ Redirect kaynağı hatası: {e}")
    
    # 2. Yöntem: Varsayılan domain
    try:
        from urllib.parse import urlparse
        parsed = urlparse(MATCHES_API_URL)
        referrer = f"{parsed.scheme}://{parsed.netloc}"
        print(f"⚠️ Varsayılan referrer kullanılıyor: {referrer}")
        return referrer
    except:
        pass
    
    print("❌ Referrer alınamadı!")
    return None

def create_logo_html(home_logo, away_logo):
    """
    İki logoyu birleştiren bir HTML veya özel format oluştur.
    VLC tvg-logo'da sadece tek bir URL gösterir, bu yüzden 
    logoları yan yana göstermek için özel bir servis kullanmak gerekir.
    Şimdilik ev sahibi logosunu kullanıp, away logosunu kanal adında belirtelim.
    """
    if home_logo and away_logo:
        # İleride kullanılmak üzere her iki logoyu da sakla
        return home_logo  # VLC uyumluluğu için tek logo
    return home_logo or away_logo or ""

def extract_static_channels_from_html(html_content):
    """Sabit kanalları HTML'den çıkar"""
    channels = []
    channel_blocks = re.findall(r'<div class="channel-item".*?data-src="/ch\.html\?id=([^"]+)".*?>(.*?)</div>\s*</div>', html_content, re.DOTALL)
    
    for channel_id, block_content in channel_blocks:
        name_match = re.search(r'class="channel-name-text">([^<]+)</span>', block_content)
        if name_match:
            channel_name = name_match.group(1).strip()
            logo_match = re.search(r'<img src="([^"]+)" class="channel-logo-right"', block_content)
            logo_url = logo_match.group(1) if logo_match else ""
            
            channels.append({
                'id': channel_id,
                'name': channel_name,
                'logo': logo_url,
                'type': 'static'
            })
    return channels

def main():
    print("🔍 Kaynaklardan bilgiler alınıyor...")
    print("-" * 50)
    
    # Base URL'i dene
    base_url = get_base_url_with_fallback()
    if not base_url:
        print("❌ Base URL alınamadı, işlem durduruluyor.")
        return
    
    # Referrer'ı dene
    referrer = get_referrer_with_fallback()
    if not referrer:
        print("❌ Referrer alınamadı, işlem durduruluyor.")
        return
    
    print("-" * 50)
    print(f"📡 Kullanılacak Referrer: {referrer}")
    print(f"🚀 Kullanılacak Base URL: {base_url}")
    print("-" * 50)
    
    m3u_list = ["#EXTM3U"]
    all_matches = []
    
    # Maç API'sinden verileri çek
    try:
        print("\n📡 Maç API'sinden veriler alınıyor...")
        response = requests.get(MATCHES_API_URL, headers=HEADERS, timeout=15)
        matches = response.json()
        print(f"🔍 API'den {len(matches)} maç kaydı alındı.")
        
        for match in matches:
            url_path = match.get('URL', '')
            channel_id = url_path.split('id=')[-1] if 'id=' in url_path else None
            
            if channel_id:
                home = match.get('HomeTeam', '').strip()
                away = match.get('AwayTeam', '').strip()
                league = match.get('league', 'Spor').strip()
                match_type = match.get('type', 'football').strip()
                match_time = match.get('Time', '').strip()
                
                # Her iki takımın logosu
                home_logo = match.get('HomeLogo', '')
                away_logo = match.get('AwayLogo', '')
                
                # Logo için ev sahibi logosunu kullan (VLC uyumluluğu)
                logo_url = home_logo or away_logo or ""
                
                # Kanal adı (her iki takım da görünsün)
                channel_name = f"{home} - {away}"
                if match_time:
                    channel_name += f" [{match_time}]"
                
                # Ek bilgi olarak her iki logoyu da sakla (ileride kullanılmak üzere)
                all_matches.append({
                    'id': channel_id,
                    'name': channel_name,
                    'logo': logo_url,
                    'home_logo': home_logo,
                    'away_logo': away_logo,
                    'league': league,
                    'type': match_type,
                    'time': match_time,
                    'home': home,
                    'away': away
                })
                
                # Logoları kontrol et ve varsa yazdır
                if home_logo and away_logo:
                    print(f"  ✓ {home} - {away}: Her iki logo da mevcut")
                elif home_logo or away_logo:
                    print(f"  ✓ {home} - {away}: Tek logo mevcut")
                else:
                    print(f"  ✓ {home} - {away}: Logo yok")
        
        print(f"✅ {len(all_matches)} maç hazır.")
        
    except Exception as e:
        print(f"⚠️ Maç API'si hatası: {e}")
        print("Devam ediliyor...")
    
    # Sabit kanallar
    print("\n📺 Sabit kanallar hazırlanıyor...")
    
    static_html = """<div id="matchList"><div class="channel-item" data-src="/ch.html?id=patron" data-id="channel_1">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS 1</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-ad-item"><a href="https://t.ly/HepbetSpor" target="_blank"><img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjXWzCfu5DzKQDasl97tLxFdcx05Bcx22a0g8ixY0jVtwzlzHa-n8Rz3rp_y9PL_Wq-NfTfg32ggIYNfgXkRoEJzIcXn9mOpdqGCDmnu62g8RevQf0SD86nuUt56P_BY-LF8kxCyxIfZKkOkktcJzcpfMDi7bt5XGm2WURcvkglqFyAYEZwo_pn_kbbRKk/s1600/gif%20yeni.gif" alt="Reklam"></a></div><div class="channel-item" data-src="/ch.html?id=b2" data-id="channel_2">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-ad-item"><a href="https://t.ly/HepbetSpor" target="_blank"><img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjXWzCfu5DzKQDasl97tLxFdcx05Bcx22a0g8ixY0jVtwzlzHa-n8Rz3rp_y9PL_Wq-NfTfg32ggIYNfgXkRoEJzIcXn9mOpdqGCDmnu62g8RevQf0SD86nuUt56P_BY-LF8kxCyxIfZKkOkktcJzcpfMDi7bt5XGm2WURcvkglqFyAYEZwo_pn_kbbRKk/s1600/gif%20yeni.gif" alt="Reklam"></a></div><div class="channel-item" data-src="/ch.html?id=b3" data-id="channel_3">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS 3</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports3.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=b4" data-id="channel_4">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS 4</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports4.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=b5" data-id="channel_5">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS 5</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsports5.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=bm1" data-id="channel_6">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS MAX 1</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsportsmax1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=bm2" data-id="channel_7">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">BEIN SPORTS MAX 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/beinsportsmax2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=ss" data-id="channel_8">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">S SPORT</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/ssport1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=ss2" data-id="channel_9">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">S SPORT 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/ssport2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=smarts" data-id="channel_10">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">SMART SPOR</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/smartspor.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=smarts2" data-id="channel_11">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">SMART SPOR 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/smartspor2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t1" data-id="channel_12">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 1</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu1.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t2" data-id="channel_13">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 2</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t3" data-id="channel_14">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 3</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu3.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=t4" data-id="channel_15">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TİVİBU SPOR 4</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/tivibu4.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=trtspor" data-id="channel_16">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TRT SPOR</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/trtspornew.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=trtyildiz" data-id="channel_17">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tv-icon-box"></div>
                                <span class="channel-name-text">TRT SPOR YILDIZ</span>
                            </div>
                            <div class="channel-right">
                                <span class="channel-live-badge">CANLI</span>
                                <img src="https://patronsports1.cfd/img/trtspor2.png" class="channel-logo-right" alt="">
                            </div>
                        </div></div><div class="channel-item" data-src="/ch.html?id=trt1" data-id="channel_18">
                        <div class="channel-row" style="flex: 1;">
                            <div class="channel-left">
                                <div class="tt"
