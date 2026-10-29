import os

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

# SENIN VERDIGIN EN GUNCEL TOKENLI LINKLER - HEPSI 2026'ya kadar
links = {
    "TRT 1": "https://tv-trt1.medya.trt.com.tr/master.m3u8",
    "ATV": "https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app=d5eb593f-39d9-4b01-9cfd-4748e8332cf0&st=DEuWHVDFai9dO1g8iqkc0A&e=1793322513&ppid=3bcab250e6c871de99a1664e01d1966e&dfp_paln=AQzzBGQEokseIW9wga6Og8jpp6CXWR59g2FgB_mCui4xnULW3DrQuChjwFcdPfj0ZjvBXJ1fJOexEf9POiG3fvAF7uSgk8JWsEV2LdtGWyIS1Pf9HyOx0h0BTnX_XOj4LWIxGHqtFu8KleG3CoQN4N3nFK8uEv3Rt1sK1Bv-v5y6oFB04HodcpzsePwGyO5eYOkkXpp3QEPKi3VUK5E0ILCiGPu6OOSk-AfJ2E0-H5LNz92PVDmFkorsdDX9PQiHff_shGBOFRSQaMM8svNx_QS5w4cmTIOS9xYyRZcwfZ76IBFMObrcbjwA98e7VJF0JnMzFkbzZGSrGuu9zxk7hQ4DK9T-SttkxBYXQCsIcOKjF-898E64P9neucBYrfFM0xZ6JCVmtph-49gHJOpMCiyVCfEYpBvdxfxm03aANWyXQxVoyyBY6KEBHN_V51QMRYFVMjipbNroUPhMpfF5XGULswQnP9QpvgSQiJQq69VH_d8MIFaOMvWH_7xakN7Iqo9noRA-VvIpls8zGrCq4nnnlX_zBTLq2fvi5yF_12khjjjjj4qwL9GbyLxgS6cIPfHHJKUzppGQrrASO-Jrdi2EV7_f3SgmT7KANEhT8SfSSGCtyS-lfYN_-Tc_jeIj8weipEEHYSUYW1z_1cT98hDx3dx24_6pyCPoDhmwPmyP4qYdRXcyu2lWp1B3tiG36egvZkE6JtV4Q0hV0-ZtXDFoX8IxilAtdQMWVEcoY-Tl7T89Bbeh8_PbXfzhebbG86XjPfiLPnd9unMnfldQR7-ViXM3Z7LsRaKdVzqqA4ml2eS96jQhy8cXjA1nPOV6wAmxavHkJpiD9HMINzKJpDtL-2ZUu9PjfH9KDgVIvNzbUblkAJIONAZuEX9nrmM1v2HQTzD7-U40uR7_amLTM571xgFeyBw3nDDg4KwRIlsfiiUXvbU-B9MCFCxYeMpu1wJQdqXOIzWAPaVLrXFFlR3O_Et9CLx1Lt4uSw4_IvrmM9gkvOj64LPXIXFY9Ysyy5ojYwYGfJqcWk3tVXfrDdLlWnzqDiDgTZws8dF2IZzhA95i_ZQjul_NofwkNwFsqEXWPgIRM3FhPkbUBUKAV1NUZbBXg-2U9Y0mvACR5tzITM-asWZYLhAFbAmoLyn8vJLj0SFSQYX_kJZ-Ad1KhkVSjFos4YfxMoU9C7GlOa2e1bsyBl4YrIKbk2bnabsfOfLklqKfVo7X00rKbNimk090nuO3lFxkLRY917YdUfT2INy7RURU0FV0sGqYEN2dQ0IZnOi5CNeqz9RLub2x_VhopMhHGUIfibcbuda",
    "KANAL D": "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3&ppid=f9fbf59814ca71a045d91069567bc196&dfp_paln=AQzzBGQEKN2iBR47hnFWuLC4M0UrY08ad_uf-pP9B7HDvZOf1iwiKzv_lgibiP0PB-1z87FDw8aAiWAgzsqFSVHlkXdgqzuEZybfRW24KsRKAJZUZoZllGzjHJpeEI6QXaCxzQDXWoGvetBrgjROHM7Wn7PXW1tW5tzdNTEsalRWr8ssVgoACDboUHmln3GaClBSVjBi_sSUi4xQ4EEVFL_ioTPgGIpoLBbbMGJZx-qjD0m6oyocgy4rlMew_swLAg8I-WgGgw0QZ45FpcmYVgZf4uzciSUSZStZa5jL-joa1_6MffR1EbPzzf1Xa0aZHcQlpNUKtxKQFx2b0goUKmYRqfurmqZbI9nvEXySk9iQaeq0eNlbn8FbdQCqJUUDK3sq6dmguxhs5WPQemUkKo2u9FoFvooRR8gZSOSDmvsH04j-5NPazs2zYZygvne5O4UcIXRkEJQ01NjTJ-SAaBWxmj0pP0jIsnf4MFUa0ilkiicUzHrfz6kmfGsRGtZFrCQPU5dVDBvwYxeAU_3QNUkC_bdzLieZVwrQz-qk0ajyX3F0FwLu_E5ejs8z2b7qxTYjbGd1R2G3_7lCXr9aMFboQOLiDUcmnZ0glPXSzP2aTToUIqrtfnbXM3PBYNJ2Zx4rK_IGa96zz7UdEH-9l8T6yGW9uTrp99wER1UrVjIFM4oc3Pi0mY5UgKQTTR3tgeDA332r58zQJoQEvCcP2IX8zP5uuedATQdc9S8JsIkVSbd1wGIB5d4HbiIkatiEWXRzGlpFhl6Zuh9kJd1I8PweTwjJO6IomQINa0OyooZ8o2WDPmj37Jaq6yptPtiDri-rvl9l0XG_MLI9td38CZqjCmCyRPqM1gUIbDcnDXgCrzK2vmMhvOPepcyRdG2dWbv3jxKIlM_sxaZ21NLFKz7xr-4O96-8Wd6d4YrRME9wTqmj0ZZ5Qf5zvHwHXztWyGLvTSH0ax8CmIIxACtroYBN-0idGa_q46xCxtDkfM_DHT8daS2jwOINvqlk0MwWl5Yx0zI3MuLMdVD-bjvH4JksKFnuC98hxiILCqGFZHt74rxy1ZhuScJ3zWjsZtZJG26lJrbzsyRVFw",
    "SHOW TV": "https://ciner.daioncdn.net/showtv/showtv.m3u8?ce=3&app=4bc856ef-4c68-4a94-bc87-37dfaaa66558&st=RBzhSuGauna0OGld-DJUVA&e=1664766175&tv=1nov",
    "STAR TV": "https://dogus.daioncdn.net/startv/startv.m3u8?ce=3&app=a20ac41e-bdc3-4aa1-934d-26b484480ac9&ppid=f707dc99c764a453381be07886dd1b57&dfp_paln=AQzzBGQEwFbg1aigh_2CiKHaecXQCgCNflbYsG7XwuOhiqEiAYrJ77DzWEPEOqEcLBnBJtSjlAlksbX9CjbXG-yBhAHLzQOPhhlugiek4sprEYMWfN03yQV619HV7QCi09hiFjGvRNTanxYkPopAQNPdVLvld6KNS0bzhA2l5jF6aydyPIIGZeE0Q_HSoFNqDYrA-7nlweSKdg768SGdhomM6cfmPHRV2HxkA-8lSDfbKRaaV4AOrBHIVPRG_fqIBxClNpKVVKafLC340MvB1hDr8W12_Ex29ZIqhRXLYNj-KtYUWIDfmsPiBrtxP-x7TE5ggnzBzHaR2swTk55uUP1C8QXCeR4HW-s00-O6Sq6WyalLucmRjJTgOxMrSmyPSIZ15wfshUfQVHo7lrT3_RZSl-qJD105fu2htaRIj08tTJVjB5uBZVneFt8EY8nj_ORNn1T_hLHo8y7tg8NzGd2wE1uHU0Yvw6XBuZ7lNR-FMEuS05sJTQ98DwbYeqlOFLJti-6ey3WkBgyM_aWSCI1YOeYvCH4tZmVmLUUwaKk7T_KRoHvEemVDK6iFVXwcpWYEeUio_N68r_Ke0ze9FEPlyUhQfkEsGtV4cIdLRUxJX7e6-2jM0h8O-KoXBPHudLBDTBWDXcQy3O1BObOIU1gqUNYb6ZTOjx8Q16nTcExOb0Cevm3QD-c9899kQHvrKv3oPL37o0mDUr0WbsVAp58ZuN8kHoT3bylbNSjKSwIS6gdrhAa2oq2pta8m76G-yb49xQ53C87E5X0zxNlovIl_K6AabkMcwhhj3nXHZR782ovxuLz-w12JR8Pp5HV2uXREOrOoXENvrPFc7a_1g60KPU5UNPKncD16H6VXhGjFUR4iiD2Eta0NIWWRSfdy71n2Ct4MYN1ispjr6-NXmMnA6vjehADF0JObI0cKKOpKbBspnffTo75_vcFmVD8BR6yesGODQSPe59yiIRvS-qEHIxiXydFSNIFuuWp8EUciIACyrbAWpGdAKS3gJnPRcSFU1kmNFkDGgIWFAaFpsykfcMEVxcJRAT3MR89ssvIu1ueiOVOeBB2cFgOyM1D7aXnqyArTBuKzWd_PwcCXM14Gue1Vtl6k2Zd1B-hWH5LKfl4_NYE84kDYgUYqv7DecRNiGV0Rh7iBy-_7j_YjYThoAG2ZhzKY4zdcJH9AGhfR7tkKb2_uZQCq_5lhYeZv99VDb_vZiw7IfkCDHn_BEsd7B1Gq82UhL_sIE9q0-nJEf0PCqfq9ESwZzAwAvng9orC2eLjyNSrFpmFwXp7QVlRVqX1t3PUkQChqr0NIZMbbmmbPpeHG",
    "NOW TV": "https://nowtv-live-ad.ercdn.net/nowtv/playlist.m3u8?st=70w5DbQKtpXA39iFdH8w-g&e=1793292773",
    "KANAL 7": "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
    "TV8": "https://tv8.daioncdn.net/tv8/tv8.m3u8?app=7ddc255a-ef47-4e81-ab14-c0e5f2949788&ce=3&ppid=2fa25e38651fb8e365593e24038bcaba&dfp_paln=AQzzBGQEJOZaDPVN7SdwD7Jmfp9Ww34hoHP_XyMPrZFpwD_GH3_pvwc7v2C28aBKfVv3O0jT-g-TjMYjJbOSj1ZG9rZ2nyZOJbaILLsGb3eMieqUak9zYHoYzON1WDguUObe04OFRoUx9CTxlkBRpfd_-JNCaqqgvxJxSYR_LatDWJywoa-2TUEfoNsc0M3kUpSaLQ7baX7EMsjDB-AV24WuOCs0Jwy2Q2m9trTRtNFKa67bIcIVEgXfAE_T6XrreWdnIsDCcQTq5s7wD7CifmN8QxPWrHhUPo1rvB7W1yxYNHDJHBcxI87Ixfg7UQ98-Ccgx7vj-jrKkpdok7loXL98wyqkUEHj_tdoZn-UhBjaJu3o_BNjDi6nwLSKRYMpesoFiFSqmE2H8jXsIQuzOvZPtzee97ii2HLVMdjBKq-qxY44PJezHxMQ9ba6pCfPS8mc88AP4fFKANqw0j42oObzJHxk7-_kz8t9E0gOO-DizAKAXEEvM8IKxPSLpjPGu_J-b_0wGKXwjiWnPJhtwZhrusWn8YqLgZ9qF0z8Yk6lgb_a6jUHuedMKbu3_2nXaD9vrgl1okzUMVnKNqqhab3Yj3YJZYfwHsv2Um6SEO53qxvOq_CyTG3nuOzBkJ79LA7bVJNrToz2vYCthZyj01krO6I40ONoq1ttul4B-r1_Pyrh0F8NbkuoC1GKxsR2l_I5Wc_S5689NodDeHzg2bDcrnDKNx7XdXHBEu0gaExPukjekDEfU50jxqmHVkc7_kPt5fu7fCb_nKHTkBSaTBPGhUiuRio2DW5aRYahLVNvXYx8RuW-W61QI2RCRPxk_GAuTixZ0GQikm_Bf1S_j5IarLN8SY-7YktPhjcVQt6FpnEipj7ABcDWUso7nBx3DA071sJxKRxH5Pc3C9Wz-NPVqK8QgPmCCKiEUbF8CzJ9devbIEZ7G0WUQ9Nzu3uhAGvBBTh_dYcpjMZzZMv5HrIuXQPZYugQAxThbttpv5NJ1FiDJXqrnfi_mFVN7wqwix26N7MXzxJJirc"
}

logos = {
    "TRT 1": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png",
    "ATV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png",
    "KANAL D": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png",
    "SHOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/showtv.png",
    "STAR TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png",
    "NOW TV": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png",
    "KANAL 7": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png",
    "TV8": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png",
}

epg_header = "#EXTM3U"
old_blocks = []

if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            first = content.splitlines()[0] if content else "#EXTM3U"
            if "#EXTM3U" in first:
                epg_header = first.strip()
            parts = content.split("#EXTINF")
            for p in parts[1:]:
                block = "#EXTINF" + p.strip()
                if YENI_GRUP in block:
                    continue
                if "http" in block:
                    old_blocks.append(block)
    except:
        pass

with open(output_file, "w", encoding="utf-8") as out:
    out.write(epg_header + "\n")
    for name in ["TRT 1","ATV","KANAL D","SHOW TV","STAR TV","NOW TV","KANAL 7","TV8"]:
        url = links[name]
        logo = logos.get(name, "")
        ref_map = {
            "ATV": "https://www.atv.com.tr/",
            "KANAL D": "https://www.kanald.com.tr/",
            "SHOW TV": "https://www.showtv.com.tr/",
            "STAR TV": "https://www.startv.com.tr/",
            "NOW TV": "https://www.nowtv.com.tr/",
            "KANAL 7": "https://www.kanal7.com/",
            "TV8": "https://www.tv8.com.tr/",
            "TRT 1": "https://www.trt1.com.tr/",
        }
        ref = ref_map.get(name, "https://www.google.com/")
        out.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{YENI_GRUP}",{name}\n')
        out.write(f'#EXTVLCOPT:http-referrer={ref}\n')
        out.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
        out.write(f'{url}\n\n')
    for b in old_blocks:
        out.write(b + "\n\n")

print("Bitti - 8 kanal ULUSAL + eski liste korundu")
