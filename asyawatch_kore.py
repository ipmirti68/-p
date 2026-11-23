
import asyncio
import re
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

CATEGORY = (
    "https://www.viki.com/categories/"
    "country/korea/genre/all?type=series"
)

OUTPUT = "hanim_viki_kore.m3u"
GROUP = "🇰🇷 HANIM VIKI DİZİLERİ ⭕"


async def main():
    found = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
            )
        )

        print("[SAYFA]", CATEGORY)

        response = await page.goto(
            CATEGORY,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("[HTTP]", response.status if response else "YOK")

        await page.wait_for_timeout(7000)

        # Sayfa bağlantılarını ve görsellerini oku
        cards = await page.locator("a[href]").evaluate_all("""
            links => links.map(a => {
                const img = a.querySelector('img') ||
                    a.parentElement?.querySelector('img');

                return {
                    href: a.href,
                    text: a.innerText || '',
                    title: a.getAttribute('title') || '',
                    aria: a.getAttribute('aria-label') || '',
                    alt: img?.alt || '',
                    poster: img?.currentSrc || img?.src || ''
                };
            })
        """)

        print("[LINK] Toplam bağlantı:", len(cards))

        for item in cards:
            url = item["href"]
            path = urlparse(url).path.lower()

            # Dizi sayfası bağlantılarını filtrele
            if not re.search(r"/tv/[^/]+", path):
                continue

            name = (
                item["text"].strip()
                or item["title"].strip()
                or item["aria"].strip()
                or item["alt"].strip()
            )

            name = " ".join(name.split())

            if not name:
                continue

            if name.lower() in ("view show details", "watch now"):
                continue

            poster = item["poster"]

            found[url] = {
                "name": name,
                "poster": poster
            }

        print("[DIZI] Bulunan:", len(found))

        if not found:
            print("[UYARI] Dizi bulunamadı.")
            print("[DEBUG] İlk 30 bağlantı:")

            for item in cards[:30]:
                print(
                    item["href"],
                    "|",
                    item["text"][:80]
                )

            await browser.close()
            return

        lines = ["#EXTM3U"]

        for url, item in found.items():
            name = item["name"]
            poster = item["poster"]

            lines.append(
                f'#EXTINF:-1 tvg-logo="{poster}" '
                f'group-title="{GROUP}",{name}'
            )
            lines.append(url)

            print("[EKLENDI]", name)

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        print("[OK] M3U oluşturuldu:", OUTPUT)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
