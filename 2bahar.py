
import os
import re
import json
import tempfile
from urllib.parse import urlparse

# ==========================================
# AYARLAR
# ==========================================

JSON_DOSYASI = "ikinci_bahar_kaynaklar.json"
CIKTI_DOSYASI = "ikinci_bahar.m3u"

GROUP = "🎬 İKİNCİ BAHAR"

# ==========================================
# ADRES KONTROLÜ
# ==========================================

def adres_kontrol(adres):
    if not isinstance(adres, str) or not adres.strip():
        return False, "Adres boş"

    adres = adres.strip()

    if "BURAYA_" in adres.upper():
        return False, "Örnek adres henüz gerçek adresle değiştirilmemiş"

    try:
        parsed = urlparse(adres)

        if parsed.scheme not in ("http", "https"):
            return False, "HTTP/HTTPS adresi değil"

        if not parsed.netloc:
            return False, "Adresin sunucu bölümü eksik"

        if not parsed.path.lower().endswith(".m3u8"):
            return False, "Adres doğrudan M3U8 uzantılı değil"

        return True, "Geçerli adres biçimi"

    except Exception as hata:
        return False, f"Adres kontrol hatası: {hata}"


# ==========================================
# JSON OKU
# ==========================================

def kaynaklari_oku():
    if not os.path.exists(JSON_DOSYASI):
        print(f"❌ Kaynak dosyası bulunamadı: {JSON_DOSYASI}")
        return []

    try:
        with open(JSON_DOSYASI, "r", encoding="utf-8") as dosya:
            veri = json.load(dosya)

        bolumler = veri.get("episodes", [])

        if not isinstance(bolumler, list):
            print("❌ JSON içindeki episodes alanı liste değil.")
            return []

        return bolumler

    except json.JSONDecodeError as hata:
        print(f"❌ JSON format hatası: {hata}")
        return []

    except Exception as hata:
        print(f"❌ Dosya okuma hatası: {hata}")
        return []


# ==========================================
# M3U OLUŞTUR
# ==========================================

def m3u_olustur():
    print("=" * 45)
    print("       İKİNCİ BAHAR M3U GÜNCELLEME")
    print("=" * 45)

    bolumler = kaynaklari_oku()

    if not bolumler:
        print("❌ Kaynak listesinde bölüm bulunamadı.")
        print("⚠️ Eski M3U dosyası korundu.")
        return

    gecerli = {}
    hatali = 0

    for kayit in bolumler:
        if not isinstance(kayit, dict):
            print("❌ Hatalı kayıt: Bölüm bilgisi nesne değil.")
            hatali += 1
            continue

        numara = kayit.get("episode")
        adres = kayit.get("url", "")

        try:
            numara = int(numara)
            if numara < 1:
                raise ValueError
        except (ValueError, TypeError):
            print(f"❌ Geçersiz bölüm numarası: {numara}")
            hatali += 1
            continue

        uygun, aciklama = adres_kontrol(adres)

        if not uygun:
            print(f"❌ {numara}. bölüm: {aciklama}")
            hatali += 1
            continue

        if numara in gecerli:
            print(f"⚠️ {numara}. bölüm: Tekrarlanan kayıt, atlandı.")
            continue

        gecerli[numara] = adres.strip()
        print(f"✅ {numara}. bölüm: Adres biçimi uygun")

    if not gecerli:
        print("-" * 45)
        print("❌ Geçerli M3U8 adresi bulunamadı.")
        print("⚠️ Eski M3U dosyası silinmedi veya değiştirilmedi.")
        return

    # ======================================
    # M3U SATIRLARINI HAZIRLA
    # ======================================

    satirlar = ["#EXTM3U"]

    for numara in sorted(gecerli):
        satirlar.append(
            f'#EXTINF:-1 group-title="{GROUP}",'
            f'İKİNCİ BAHAR S01 E{numara:02d}'
        )
        satirlar.append(gecerli[numara])

    icerik = "\n".join(satirlar) + "\n"

    # ======================================
    # GÜVENLİ DOSYA YAZIMI
    # ======================================

    hedef = os.path.abspath(CIKTI_DOSYASI)
    klasor = os.path.dirname(hedef)

    gecici_yol = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=klasor,
            suffix=".tmp",
            delete=False
        ) as gecici:
            gecici.write(icerik)
            gecici_yol = gecici.name

        os.replace(gecici_yol, hedef)

        print("-" * 45)
        print(f"✅ M3U başarıyla güncellendi: {CIKTI_DOSYASI}")
        print(f"📺 Geçerli bölüm: {len(gecerli)}")
        print(f"⚠️ Hatalı kayıt: {hatali}")

    except Exception as hata:
        print(f"❌ M3U yazma hatası: {hata}")

        if gecici_yol and os.path.exists(gecici_yol):
            os.remove(gecici_yol)

        print("⚠️ Eski M3U dosyası korunmaya çalışıldı.")


# ==========================================
# BAŞLAT
# ==========================================

if __name__ == "__main__":
    m3u_olustur()
