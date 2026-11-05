import os, re, json, tempfile, unicodedata
from datetime import datetime, timezone
from yt_dlp import YoutubeDL

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"
CHANNEL_URL = "https://www.youtube.com/channel/UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
GROUP_LIVE = "🏐 VOLEYBOL HLS"
OLD_GROUPS = (GROUP_LIVE, "🏐 VOLEYBOL CANLI", "🏐 KUZEYBORU")
MAX_VIDEOS = 20

OPTIONS = {
    "quiet": True, "ignoreerrors": True,
    "extract_flat": "in_playlist", "playlistend": MAX_VIDEOS,
    "skip_download": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}
DETAIL_OPTIONS = {
    "quiet": True, "ignoreerrors": True,
    "skip_download": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}

def clean_title(v): return re.sub(r"\s+", " ", str(v or "TVF")).strip()[:250]
def normalize_text(v):
    v=str(v or "").lower().replace("ı","i")
    return unicodedata.normalize("NFKD", v)
def get_video_id(value):
    m=re.search(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})", str(value))
    return m.group(1) if m else ""
def get_hls_url(info):
    for f in (info or {}).get("formats") or []:
        u=(f.get("url") or "")
        if "m3u8" in u.lower(): return u
    return ""

def scan_channel():
    vids=[]; seen=set()
    try:
        with YoutubeDL(OPTIONS) as ydl:
            pl=ydl.extract_info(CHANNEL_URL, download=False)
            for e in (pl or {}).get("entries") or []:
                v=get_video_id(e)
                if v and v not in seen: seen.add(v); vids.append(v)
    except: pass
    res=[]
    with YoutubeDL(DETAIL_OPTIONS) as ydl:
        for vid in vids:
            try:
                info=ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False) or {}
                title=clean_title(info.get("title") or vid)
                hls=get_hls_url(info)
                if hls:
                    res.append({"name":title,"stream_url":hls,"is_replay":info.get("live_status")=="was_live"})
            except: pass
    return res

def save_files(items):
    live=[i for i in items if not i.get("is_replay")]
    replay=[i for i in items if i.get("is_replay")]
    if os.path.isfile(MASTER_FILE):
        with open(MASTER_FILE,"r",encoding="utf-8-sig") as f: old=f.read()
    else: old="#EXTM3U\n"
    # Eski voleybol gruplarını temizle ama MAHSUN'u silme
    lines=old.splitlines(True)
    new_lines=[]
    for l in lines:
        if GROUP_LIVE in l: continue
        new_lines.append(l)
    if not new_lines: new_lines=["#EXTM3U\n"]
    for it in live[:5]:
        new_lines.append(f'#EXTINF:-1 group-title="{GROUP_LIVE}",{it["name"]} | CANLI\n')
        new_lines.append(it["stream_url"]+"\n")
    with open(MASTER_FILE,"w",encoding="utf-8",newline="\n") as f: f.writelines(new_lines)
    with open(RESULT_FILE,"w",encoding="utf-8") as f: json.dump({"total":len(items),"matches":items}, f, ensure_ascii=False, indent=2)

if __name__=="__main__":
    items=scan_channel()
    save_files(items)
