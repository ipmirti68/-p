import os, re, json
from yt_dlp import YoutubeDL

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"
CHANNEL_URL = "https://www.youtube.com/channel/UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
GROUP_LIVE = "🏐 VOLEYBOL HLS"
GROUP_REPLAY = "🏐 SULTANLAR LİGİ TEKRAR"
MAX_VIDEOS = 60

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
    m=re.search(r"([A-Za-z0-9_-]{11})", str(v.get("id") or ""))
    return m.group(1) if m else ""

def get_hls(info):
    for f in (info or {}).get("formats") or []:
        u=f.get("url") or ""
        proto=str(f.get("protocol") or "").lower()
        if "m3u8" in u.lower() or "m3u8" in proto or "hls" in proto:
            return u
    return ""

def scan():
    print("MIRTI68 - Son hafta TEKRAR + Canli")
    vids=[]
    try:
        with YoutubeDL(OPTIONS) as ydl:
            pl=ydl.extract_info(CHANNEL_URL, download=False)
            for e in (pl.get("entries") or []):
                vid=get_id(e)
                if vid: vids.append((vid,e))
    except Exception as e:
        print(f"Kanal hatasi {e}")
        return []
    res=[]
    with YoutubeDL(DETAIL) as ydl:
        for vid, entry in vids:
            status=entry.get("live_status") or ""
            if status=="is_upcoming":
                continue
            url=f"https://www.youtube.com/watch?v={vid}"
            try:
                info=ydl.extract_info(url, download=False) or {}
            except:
                continue
            title=info.get("title") or entry.get("title") or vid
            low=title.lower()
            if "sultanlar" not in low and "kuzeyboru" not in low:
                continue
            hls=get_hls(info)
            if not hls:
                continue
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
    else:
        old="#EXTM3U\n"
    lines=[]
    skip_next=False
    for l in old.splitlines(True):
        if skip_next and l.strip() and not l.strip().startswith("#"):
            skip_next=False
            continue
        if GROUP_LIVE in l or GROUP_REPLAY in l:
            skip_next=True
            continue
        lines.append(l)
    if not lines or "#EXTM3U" not in lines[0]:
        lines=["#EXTM3U\n"]+lines
    for it in live[:5]:
        lines.append(f'#EXTINF:-1 group-title="{GROUP_LIVE}",{it["name"]} | CANLI\n')
        lines.append(it["stream_url"]+"\n")
    for it in
