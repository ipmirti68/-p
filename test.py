
import asyncio
import os
import re
import tempfile
from playwright.async_api import async_playwright

# ==========================================
# KANAL LİSTESİ
# ==========================================

channelsMap = {
    "Bein Sports 1-BS": "https://elif.eromaxe.com/zeynep/bein1tr",
    "Bein Sports 2-BS": "https://elif.eromaxe.com/zeynep/bein2tr",
    "Bein Sports 3-BS": "https://elif.eromaxe.com/zeynep/bein3tr",
    "Bein Sports 4-BS": "https://elif.eromaxe.com/zeynep/bein4tr",
    "Bein Sports 5-BS": "https://elif.eromaxe.com/zeynep/bein5tr",
    "Bein Sports Max 1-BS": "https://elif.eromaxe.com/zeynep/beinmax1tr",
    "Bein Sports Max 2-BS": "https://elif.eromaxe.com/zeynep/beinmax2tr",
    "Bein Haber": "https://elif.eromaxe.com/zeynep/beinhabertr",
    "S Sport 1-BS": "https://elif.eromaxe.com/zeynep/ssport1tr",
    "S Sport 2-BS": "https://elif.eromaxe.com/zeynep/ssport2tr",
    "A Sport-BS": "https://elif.eromaxe.com/zeynep/asport",
    "TRT Spor-BS": "https://elif.eromaxe.com/zeynep/trtsport",
    "Eurosport 1-BS": "https://elif.eromaxe.com/zeynep/eruosport1",
    "Eurosport 2-BS": "https://elif.eromaxe.com/zeynep/eruosport2",
    "Smart Spor-BS": "https://elif.eromaxe.com/zeynep/sportsmart",
    "Smart Spor 2-BS": "https://elif.eromaxe.com/zeynep/sportsmart2",
    "ATV-BS": "https://elif.eromaxe.com/zeynep/atv",
    "Tabii Spor": "https://elif.eromaxe.com/zeynep/tabiisport",
    "Tabii Spor 1": "https://elif.eromaxe.com/zeynep/tabiisport1",
    "Tabii Spor 2": "https://elif.eromaxe.com/zeynep/tabiisport2",
    "Tabii Spor 3": "https://elif.eromaxe.com/zeynep/tabiisport3",
    "Tabii Spor 4": "https://elif.eromaxe.com/zeynep/tabiisport4",
}

OUTPUT_FILE = "spor.m3u"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

UA_SUFFIX = f"|{USER_AGENT}"

# ==========================================
# YAYIN ADRESİNİ BUL
# ==========================================

async def get_stream_url(page, full_url):

    stream_urls = []

    def handle_request(request):
        url = request.url

        if ".m3u8" in url.lower():
            if url not in stream_urls:
                stream_urls.append(url)

    page.on("request", handle_request)

    try:
        print(f"Yükleniyor: {full_url}")

        await page.goto(
            full_url,
            wait_until="domcontentloaded",
            timeout=45000
        )

        await page.wait_for_timeout(8000)

    except Exception as e:
        print(f"[YÜKLEME HATASI] {e}")

    finally:
        page.remove_listener("request", handle_request)

    if stream_urls:
        return stream_urls[0]

    return None


# ==========================================
# M3U DOSYASINI OKU
# ==========================================

def read_existing_file():

    if not os.path.exists(OUTPUT_FILE):
        print("[BİLGİ] spor.m3u bulunamadı. Yeni dosya oluşturulacak.")
        return ["#EXTM3U\n"]

    with open(OUTPUT_FILE, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    if not lines or not any(line.strip().startswith("#EXTINF") for line in lines):
        print("[UYARI] spor.m3u boş veya geçersiz. Yeni liste hazırlanacak.")
        return ["#EXTM3U\n"]

    if not any(line.strip() == "#EXTM3U" for line in lines):
        lines.insert(0, "#EXTM3U\n")

    return lines


# ==========================================
# KANAL ADINI BUL
# ==========================================

def get_channel_name(line):

    match = re.search(r",\s*(.+)$", line.strip())

    if match:
        return match.group(1).strip()

    return None


# ==========================================
# M3U LİSTESİNİ GÜNCELLE
# ==========================================

def update_m3u(updated_links):

    lines = read_existing_file()

    new_lines = []
    existing_names = set()
    updated_names = set()

    i = 0

    while i < len(lines):

        line = lines[i]

        if line.strip().startswith("#EXTINF"):

            channel_name = get_channel_name(line)

            new_lines.append(line)

            if channel_name:
                existing_names.add(channel_name)

            # EXTINF sonrasındaki yayın adresini bul
            j = i + 1

            while j < len(lines):
                candidate = lines[j].strip()

                if candidate and not candidate.startswith("#"):
                    break

                new_lines.append(lines[j])
                j += 1

            if (
                channel_name in updated_links
                and j < len(lines)
            ):
                new_lines.append(
                    updated_links[channel_name] + "\n"
                )

                updated_names.add(channel_name)

                print(
                    f"[GÜNCELLENDİ] {channel_name}"
                )

                i = j + 1
                continue

            # Yeni bağlantı bulunamadıysa eski bağlantıyı koru
            if j < len(lines):
                new_lines.append(lines[j])
                i = j + 1
            else:
                i = j

            continue

        new_lines.append(line)
        i += 1

    # ======================================
    # LİSTEDE OLMAYAN KANALLARI EKLE
    # ======================================

    added_names = set()

    for name, url in updated_links.items():

        if name not in existing_names:

            new_lines.append(
                f'#EXTINF:-1 tvg-name="{name}" '
                f'group-title="🟩◆ TABii SPOR ⚽",{name}\n'
            )

            new_lines.append(url + "\n")

            added_names.add(name)

            print(f"[YENİ EKLENDİ] {name}")

    # ======================================
    # BOŞ DOSYA KONTROLÜ
    # ======================================

    extinf_count = sum(
        1 for line in new_lines
        if line.strip().startswith("#EXTINF")
    )

    if extinf_count == 0:
        raise RuntimeError(
            "M3U dosyasında kanal kaydı yok. Dosya yazılmadı."
        )

    # ======================================
    # GEÇİCİ DOSYAYA YAZ VE KONTROL ET
    # ======================================

    directory = os.path.dirname(os.path.abspath(OUTPUT_FILE))

    fd, temp_path = tempfile.mkstemp(
        prefix="spor_",
        suffix=".m3u",
        dir=directory
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        with open(temp_path, "r", encoding="utf-8") as f:
            check_lines = f.readlines()

        check_text = "".join(check_lines)

        if "#EXTM3U" not in check_text:
            raise RuntimeError("M3U başlığı doğrulanamadı.")

        for name in updated_names | added_names:
            if name not in check_text:
                raise RuntimeError(
                    f"{name} dosyada doğrulanamadı."
                )

        # Kontrol başarılıysa asıl dosyayı değiştir
        os.replace(temp_path, OUTPUT_FILE)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    file_size = os.path.getsize(OUTPUT_FILE)

    print("\n========== DOSYA KONTROLÜ ==========")
    print(f"Dosya: {OUTPUT_FILE}")
    print(f"Boyut: {file_size} byte")
    print(f"Mevcut bağlantısı güncellenen: {len(updated_names)}")
    print(f"Yeni eklenen kanal: {len(added_names)}")
    print(f"Toplam kanal kaydı: {extinf_count}")

    return updated_names, added_names


# ==========================================
# ANA İŞLEM
# ==========================================

async def main():

    updated_links = {}

    print("========== MIRTİ68 SPOR GÜNCELLEME ==========")

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            user_agent=USER_AGENT
        )

        for name, target_url in channelsMap.items():

            print(f"\nTaranıyor: {name} ({target_url})")

            raw_m3u8 = await get_stream_url(
                page,
                target_url
            )

            if raw_m3u8:

                final_url = raw_m3u8 + UA_SUFFIX

                updated_links[name] = final_url

                print(f"[BAĞLANTI BULUNDU] {name}")

            else:

                print(
                    f"[BULUNAMADI] {name} - "
                    "Mevcut yayın korunacak."
                )

        await browser.close()

    # Hiç bağlantı bulunamadıysa dosyaya dokunma
    if not updated_links:
        print("\n[HATA] Hiçbir yayın bağlantısı bulunamadı.")
        print("Mevcut spor.m3u dosyası korunmuştur.")
        raise RuntimeError("Güncellenecek yayın bulunamadı.")

    # M3U dosyasını gerçekten güncelle
    updated_names, added_names = update_m3u(updated_links)

    print("\n========== SONUÇ ==========")
    print(f"Bulunan bağlantı: {len(updated_links)}")
    print(f"Güncellenen kanal: {len(updated_names)}")
    print(f"Yeni eklenen kanal: {len(added_names)}")

    print(
        f"\n[BAŞARILI] {OUTPUT_FILE} "
        "dosyası yazıldı ve doğrulandı."
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except Exception as e:
        print(f"\n[HATA] İşlem tamamlanamadı: {e}")
        raise
