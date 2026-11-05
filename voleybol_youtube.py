import os, re, json, tempfile
from yt_dlp import YoutubeDL

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"
CHANNEL_URL = "https://www.youtube.com/channel/UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
GROUP_LIVE = "🏐 VOLEYBOL HLS"
GROUP_REPLAY = "🏐 SULTANLAR LİGİ TEKRAR"
MAX_VIDEOS = 40

OPTIONS = {
    "quiet": True, "ignoreerrors": True,
    "extract_flat": "in_playlist", "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}
DETAIL = {
    "quiet": True, "ignoreerrors": True,
    "skip_download": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}

def get_id(v):
    import re
    m=re.search(r"([A-Za-z0-9_-]{11})", str(v.get("id") or ""))
    return m.group(1) if m else ""

def get_hls(info):
    for f in (info or {}).get("formats") or []:
        u=f.get("url") or ""
        if "m3u8" in u.lower(): return u
    return ""

def scan():
    print("MIRTI68 - Son hafta TEKRAR + Canli tarama")
    vids=[]
    entries=[]
    try:
        with YoutubeDL(OPTIONS) as ydl:
            pl=ydl.extract_info(CHANNEL_URL, download=False)
            entries=pl.get("entries") or []
            for e in entries:
                vid=get_id(e)
                if vid: vids.append((vid,e))
    except Exception as e:
        print(f"Kanal hatasi {e}")
        return []

    res=[]
    with YoutubeDL(DETAIL) as ydl:
        for vid, entry in vids:
            status=entry.get("live_status") or ""
            # YAKLAŞAN olanları atla, log kirletmesin
            if status=="is_upcoming":
                continue
            url=f"https://www.youtube.com/watch?v={vid}"
            try:
                info=ydl.extract_info(url, download=False) or {}
            except:
                continue
            title=info.get("title") or entry.get("title") or vid
            # Sadece Sultanlar Ligi ve Kuzeyboru
            low=title.lower()
            if "sultanlar" not in low and "kuzeyboru" not in low:
                continue
            hls=get_hls(info)
            if not hls: continue
            is_replay = status=="was_live" or info.get("live_status")=="was_live"
            print(f"{'TEKRAR' if is_replay else 'CANLI'}: {title}")
            res.append({"name":title,"stream_url":hls,"is_replay":is_replay})
    return res

def save(items):
    live=[i for i in items if not i.get("is_replay")]
    replay=[i for i in items if i.get("is_replay")]
    print(f"Bulunan: {len(live)} canli, {len(replay)} tekrar")
    if os.path.isfile(MASTER_FILE):
        with open(MASTER_FILE,"r",encoding="utf-8-sig") as f: old=f.read()
    else: old="#EXTM3U\n"
    # Sadece voleybol gruplarini temizle, MAHSUN'u silme
    lines=[]
    for l in old.splitlines(True):
        if GROUP_LIVE in l or GROUP_REPLAY in l: continue
        lines.append(l)
    if not lines: lines=["#EXTM3U\n"]
    # Eski URL satirlarini da temizle (basit yontem)
    # En temizi: mirti68.m3u zaten mahsun tarafindan yazildi, biz sadece ekleme yapalim
    for it in live[:5]:
        lines.append(f'#EXTINF:-1 group-title="{GROUP_LIVE}",{it["name"]} | CANLI\n')
        lines.append(it["stream_url"]+"\n")
    for it in replay[:10]:
        lines.append(f'#EXTINF:-1 group-title="{GROUP_REPLAY}",{it["name"]} | TEKRAR\n')
        lines.append(it["stream_url"]+"\n")
    with open(MASTER_FILE,"w",encoding="utf-8",newline="\n") as f: f.writelines(lines)
    with open(RESULT_FILE,"w",encoding="utf-8") as f: json.dump({"total":len(items),"matches":items}, f, ensure_ascii=False, indent=2)
    print(f"M3U guncellendi: {MASTER_FILE}")

if __name__=="__main__":
    items=scan()
    save(items)
