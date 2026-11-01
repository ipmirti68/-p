import os
import requests
import re

output_file = "mirti68.m3u"
YENI_GRUP = "📺 ULUSAL 🔗"

source_urls = {
    "【entity-ATV¦canonical_name=ATV】": "https://www.atv.com.tr/canli-yayin",
    "【entity-KANAL D¦canonical_name=KANAL D】": "https://www.kanald.com.tr/canli-yayin",
    "【entity-SHOW TV¦canonical_name=SHOW TV】": "https://www.showtv.com.tr/canli-yayin",
    "【entity-STAR TV¦canonical_name=STAR TV】": "https://www.startv.com.tr/canli-yayin",
    "NOW TV": "https://www.nowtv.com.tr/canli-yayin",
    "【entity-KANAL 7¦canonical_name=KANAL 7】": "https://www.kanal7.com/canli-izle",
    "【entity-TV8¦canonical_name=TV8】": "https://www.tv8.com.tr/canli-yayin",
}

# SENİN BULDUĞUN TAZE 【entity-ATV¦canonical_name=ATV】 LİNKİ YEDEĞE KONDU
backup = {
    "【entity-ATV¦canonical_name=ATV】": "https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app=d5eb593f-39d9-4b01-9cfd-4748e8332cf0&st=aHpY5uG0xx5ECKzVhbwyOA&e=1793560183&ppid=b906dadf20123957255ac543c4d7f20e&dfp_paln=AQzzBGQExj45_Z1K1z90s92pl9g3KlYn04ppFzIrUb5OeF38IQtLxVDm0kVChYVgRB-MCvPocnamo7bLlcw9HyE5sJfVSjjzHn45-cEs6WNuLCF4awjnjVCWGbCoZWpG-IFp6xOnrHEZJCI9NQwZFeHwTXlRF1y2yjtcKgmAKzV570ajwOze8Fj4v9H1OygnrGCRr8nJg-3M4_4D22o4vmxqmnWc-cQN-064BkyrbKGytgQq7OfJsIInASST2TWVfG_bf2GHTIKdrLW1vOUtaOb_fDQU9D5DBWsLJSb67-WXDOPk28CuFxmucBLrYqSBtqPKE9foZKpTSD419OFsFklAQnKCLq-FcPk0oheAMa62eySMwlg47zKUg0_JlhLHl2OninlI-jrCmR7j_DpFfYheC10rQuYSkj0vlqAqmR3ZRvvSYGZiSleRa0wA8qh7tNTsdanTPRPHh5rtC7R__2ZpCXo8i1KSCe2oD_I9yPswvdp8XnhVWBD4Rjh0ZcayTFjKpCbQmQ1-34gg6KML8vDuAfkzKtbg1iLi3pWfmShQYGfTQGnYUbrJQexxt4eB_daHb0otSVnkwXx9BYAem0lDf532QDiijLS8EONsYhDHx5OiGkskJPHomAmx0Mn-7711zYy-vH1Yv
