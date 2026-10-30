import os
import re
import requests
import urllib3

# SSL uyarılarını gizler
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def generate_iptv_list():
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    headers = {
        "User-Agent": user_agent,
        "Referer": "https://birazcikspor.com/",
    }

    # SADECE beIN kanalları
    channels = [
        ("androstreamlivebiraz1", "BeIN Sports 1"),
        ("androstreamlivebs1", "BeIN Sports 1"),
        ("androstreamlivebs2", "BeIN Sports 2"),
        ("androstreamlivebs3", "BeIN Sports 3"),
        ("androstreamlivebs4", "BeIN Sports 4"),
        ("androstreamlivebs5", "BeIN Sports 5"),
        ("androstreamlivebsm1", "BeIN Sports Max 1"),
        ("androstreamlivebsm2", "BeIN Sports Max 2"),
    ]

    try:
        # verify=False eklendi
        main_res = requests.get(
            "https://birazcikspor.com",
            headers=headers,
            timeout=15,
            verify=False,
        )
        active_site_match = re.search(
            r'href="(https?://birazcikspor[^"]+\.xyz)"', main_res.text
        )
        active_domain = (
            active_site_match.group(1).rstrip("/")
            if active_site_match
            else "https://birazcikspor44.xyz"
        )

        sample_url = f"{active_domain}/event.html?id=androstreamlivebiraz1"
        # verify=False eklendi
        sample_res = requests.get(
            sample_url, headers=headers, timeout=15, verify=False
        ).text
        base_urls = re.findall(
            r'["\'](https?://[^"\']+/checklist/)["\']', sample_res
        )

        if not base_urls:
            print("Base URL bulunamadı.")
            return

        final_base = base_urls[0]

        # mirti68.m3u içine ekle
        if not os.path.exists("mirti68.m3u"):
            with open("mirti68.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")

        with open("mirti68.m3u", "a", encoding="utf-8") as f:
            for cid, cname in channels:
                stream_url = f"{final_base}{cid}.m3u8"
                f.write(f'#EXTINF:-1 group-title="🖥beINSPORTS",{cname}\n')
                f.write(f"#EXTVLCOPT:http-referrer={active_domain}/\n")
                f.write(f"#EXTVLCOPT:http-user-agent={user_agent}\n")
                f.write(f"{stream_url}\n\n")

        print(f"Liste güncellendi: {len(channels)} beIN kanalı mirti68.m3u içine eklendi.")

    except Exception as e:
        print(f"Hata: {str(e)}")

if __name__ == "__main__":
    generate_iptv_list()
