from playwright.sync_api import sync_playwright
import re, os, shutil

OUTPUT_FILE = "mirti68.m3u"
GROUP = "🟨◆  ULUSAL 📺"
EPG_URL = "https://raw.githubusercontent.com/iptv-org/epg/master/guides/turkey.epg.xml"

CHANNELS = {
    "TRT1": {"display": "TRT 1 ⭕", "epg": "TRT 1", "epg_id": "TRT1", "page": "https://www.trt1.com.tr/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/trt1.png", "keyword": "trt", "marker": "# MIRTI68_TRT1_AUTO", "fallback": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
    " ATV": {"display": " ATV ⭕", "epg": " ATV", "epg_id": " ATV", "page": "https://www.atv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/atv.png", "keyword": " atv", "marker": "# MIRTI68_ATV_AUTO", "fallback": "https://rnttwmjcin.turknet.ercdn.net/lcpmvefbyo/atv/atv_720p.m3u8"},
    "SHOW": {"display": "SHOW ⭕", "epg": "Show TV", "epg_id": "ShowTV", "page": "https://www.showtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/show.png", "keyword": "showtv", "marker": "# MIRTI68_SHOWTV_AUTO"},
    "KANALD": {"display": "KANAL D ⭕", "epg": "Kanal D", "epg_id": "KanalD", "page": "https://www.kanald.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanald.png", "keyword": "kanald", "marker": "# MIRTI68_KANALD_AUTO"},
    "STAR": {"display": "STAR ⭕", "epg": "Star TV", "epg_id": "StarTV", "page": "https://www.startv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/star.png", "keyword": "startv", "marker": "# MIRTI68_STARTV_AUTO"},
    "NOW": {"display": "NOW ⭕", "epg": "NOW", "epg_id": "NOW", "page": "https://www.nowtv.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/nowtv.png", "keyword": "nowtv", "marker": "# MIRTI68_NOWTV_AUTO"},
    "KANAL7": {"display": "KANAL 7 ⭕", "epg": "Kanal 7", "epg_id": "Kanal7", "page": "https://www.kanal7.com/canli-izle", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/kanal7.png", "keyword": "kanal7", "marker": "# MIRTI68_KANAL7_AUTO"},
    "TV8": {"display": "TV8 ⭕", "epg": "TV8", "epg_id": "TV8", "page": "https://www.tv8.com.tr/canli-yayin", "logo": "https://raw.githubusercontent.com/ipmirti68/Logo/refs/heads/main/tv8.png", "keyword": "tv8", "marker": "# MIRTI68_TV8_AUTO"},
}

def get_link(page_url, keyword):
    found=[]
    def on_dialog(d):
        urls=re.findall(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*', d.message)
        if urls:
            found.extend(urls)
        try:
            d.accept()
        except:
            pass
    def on_response(resp):
        url=resp.url
        if ".m3u8" in url:
            if keyword in url.lower() or "
