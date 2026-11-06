
from playwright.sync_api import sync_playwright
import re
import os

# ==========================================
# ATV CANLI YAYIN - MIRTI68
# ==========================================

OUTPUT_FILE = "mirti68.m3u"
MARKER = "# MIRTI68_ATV_AUTO"

GROUP = "📺 ULUSAL"
NAME = "ATV 🔴"

LOGO = (
    "https://raw.githubusercontent.com/"
    "ipmirti68/Logo/refs/heads/main/atv.png"
)

PAGE_URL = "https://www.atv.com.tr/canli-yayin"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

M3U8_RE = re.compile(
    r"""https?://[^\s"'<>\\]+\.m3u8(?:\?[^\s"'<>\\]*)?""",
    re.IGNORECASE
)


# ==========================================
# YAYIN ADRESİNİ BUL
# ==========================================

def get_atv_link():

    found = []

    def add_url(url, source=""):

        url = url.strip().rstrip("),;]}")

        if ".m3u8" not in url.lower():
            return

        if url not in found:
            found.append(url)
            print(f"[{source}] {url}")

    def on_dialog(dialog):

        try:
            print("[DIALOG]", dialog.message[:300])
            dialog.accept()
        except Exception:
            pass

    def on_response(response):

        try:
            url = response.url

            # Doğrudan M3U8 adresi
            if ".m3u8" in url.lower():
                add_url(url, "URL")

            # ATV / player / yayın sunucusu yanıtları
            keywords = (
                "atv",
                "player",
                "token",
                "live",
                "ercdn",
                "daioncdn",
                "trkvz"
            )

            if any(word in url.lower() for word in keywords):

                try:
                    body = response.text()

                    for match in M3U8_RE.findall(body):
                        add_url(match, "BODY")

                except Exception:
                    pass

        except Exception as error:
            print("[RESPONSE HATASI]", error)

    def on_request_failed(request):

        try:
            print(
                "[REQUEST FAILED]",
                request.url[:180],
                request.failure
            )
        except Exception:
            pass

      with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        page = context.new_page()

        page.on("dialog", on_dialog)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

        print("[*] ATV sayfası açılıyor...")

        try:
            page.goto(
                PAGE_URL,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            print("[+] Sayfa açıldı.")
            page.wait_for_timeout(10000)

        except Exception as error:
            print("[!] SAYFA HATASI:", error)

        finally:
            browser.close()
    # ======================================
    # ADRES SEÇİMİ
    # ======================================

    print()
    print("[*] Bulunan toplam M3U8:", len(found))

    # Önce ATV 1080p Daion CDN
    for url in found:

        lower = url.lower()

        if (
            "trkvz.daioncdn.net/atv" in lower
            and "1080p" in lower
        ):

            print("[SECILDI - DAION 1080P]")
            return url

    # Sonra ATV Daion CDN
    for url in found:

        lower = url.lower()

        if "trkvz.daioncdn.net/atv" in lower:

            print("[SECILDI - DAION]")
            return url

    # Sonra ATV ERCdn
    for url in found:

        lower = url.lower()

        if (
            "trkvz-live.ercdn.net" in lower
            and "atv" in lower
        ):

            print("[SECILDI - ERCDN]")
            return url

    # Son çare: bulunan ilk M3U8
    if found:

        print("[SECILDI - ILK M3U8]")
        return found[0]

    return None


# ==========================================
# M3U DOSYASINI GÜNCELLE
# ==========================================

def update_m3u(new_url):

    new_block = (
        f"{MARKER}\n"
        f'#EXTINF:-1 tvg-name="{NAME}" '
        f'tvg-logo="{LOGO}" '
        f'group-title="{GROUP}",{NAME}\n'
        "#EXTVLCOPT:http-referrer=https://www.atv.com.tr/\n"
        f"#EXTVLCOPT:http-user-agent={USER_AGENT}\n"
        f"{new_url}\n"
    )

    # Dosya yoksa oluştur
    if not os.path.exists(OUTPUT_FILE):

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "#EXTM3U\n"
                "\n"
                + new_block
            )

        print("[OK] Yeni M3U dosyası oluşturuldu.")
        return

    # Mevcut dosyayı oku
    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        old = file.read()

    # Eski ATV kaydını değiştir
    pattern = (
        r"(?ms)^"
        + re.escape(MARKER)
        + r"\s*\n.*?"
        + r"(?=^# MIRTI68_|\Z)"
    )

    if re.search(pattern, old):

        final = re.sub(
            pattern,
            lambda match: new_block,
            old,
            count=1
        )

        print("[OK] Eski ATV kaydı güncellendi.")

    else:

        final = old.rstrip() + "\n\n" + new_block

        print("[OK] ATV listeye eklendi.")

    # Dosyaya kaydet
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(final)

    print()
    print("[OK]", OUTPUT_FILE)
    print("[OK] Dosya boyutu:", len(final), "karakter")


# ==========================================
# ANA PROGRAM
# ==========================================

def main():

    print("=" * 45)
    print("       MIRTI68 - ATV CANLI YAYIN")
    print("=" * 45)

    url = get_atv_link()

    if not url:

        print()
        print("[!] ATV YAYIN ADRESİ BULUNAMADI")
        print("[!] Tarayıcı ağ yanıtlarını kontrol et.")
        return

    print()
    print("[+] ATV ADRESİ BULUNDU:")
    print(url)

    update_m3u(url)

    print()
    print("=" * 45)
    print("          İŞLEM TAMAMLANDI")
    print("=" * 45)


if __name__ == "__main__":
    main()
