
import json
import os
from urllib.parse import urlparse

# ==========================================
# HANIM VIKI KORE DIZILERI
# MIRTITV M3U ENTEGRASYONU
# ==========================================

M3U_DOSYA = "mirti.m3u"
JSON_DOSYA = "viki_kore_katalog.json"

GRUP = "🇰🇷 HANIM VIKI DİZİLERİ ⭕"


def katalog_sablonu():
    if not os.path.exists(JSON_DOSYA):
        sablon = {
            "series": [
                {
                    "name": "ÖRNEK KORE DİZİSİ",
                    "poster": "https://example.com/poster.jpg",
                    "episodes": [
                        {
                            "title": "1. BÖLÜM",
                            "stream_url": "",
                            "authorized": False
                        }
                    ]
                }
            ]
        }
        with open(JSON_DOSYA, "w", encoding="utf-8") as f:
            json.dump(sablon, f, ensure_ascii=False, indent=4)
        print("[BILGI] Katalog şablonu oluşturuldu.")
        return None
    return True


def gecerli_yayin(url):
    try:
        p = urlparse(url)
        uzanti = p.path.lower()
        return (
            p.scheme in ("http", "https")
            and (
                uzanti.endswith(".m3u8")
                or uzanti.endswith(".mp4")
                or uzanti.endswith(".mpd")
            )
        )
    except Exception:
        return False


def liste_oku():
    if not os.path.exists(M3U_DOSYA):
        with open(M3U_DOSYA, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
    with open(M3U_DOSYA, encoding="utf-8-sig") as f:
        return f.read()


def m3u_guncelle():
    if not katalog_sablonu():
        return

    with open(JSON_DOSYA, encoding="utf-8") as f:
        katalog = json.load(f)

    mevcut = liste_oku()
    satirlar = []

    for dizi in katalog.get("series", []):
        ad = dizi.get("name", "").strip()
        afis = dizi.get("poster", "")

        if not ad:
            continue

        for bolum in dizi.get("episodes", []):
            baslik = bolum.get("title", "").strip()
            url = bolum.get("stream_url", "").strip()

            if not bolum.get("authorized", False):
                continue

            if not baslik or not gecerli_yayin(url):
                continue

            if url in mevcut:
                continue

            tam_ad = f"{ad} - {baslik}"

            satirlar.extend([
                f'#EXTINF:-1 tvg-logo="{afis}" group-title="{GRUP}",{tam_ad}',
                url
            ])

    if not satirlar:
        print("[BILGI] Eklenecek yeni ve doğrulanmış yayın yok.")
        return

    with open(M3U_DOSYA, "a", encoding="utf-8") as f:
        f.write("\n")
        f.write("\n".join(satirlar))
        f.write("\n")

    print(f"[OK] {len(satirlar)//2} yeni bölüm eklendi.")
    print(f"[OK] Dosya: {M3U_DOSYA}")


if __name__ == "__main__":
    print("🇰🇷 HANIM VIKI KORE DIZILERI")
    print("--------------------------------")
    m3u_guncelle()
