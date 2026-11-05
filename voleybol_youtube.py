import os
import re
import json
import tempfile
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from yt_dlp import YoutubeDL

MASTER_FILE = "mirti68.m3u"
RESULT_FILE = "voleybol_youtube.json"
TAKVIM_FILE = "mac_takvimi.json"

CHANNEL_URL = "https://www.youtube.com/channel/UCTgQ8Bfq3AUuo1vWULdvRKw/streams"
CHANNEL_ID = "UCTgQ8Bfq3AUuo1vWULdvRKw"
GROUP_LIVE = "🏐 VOLEYBOL HLS"
GROUP_REPLAY = "🏐 SULTANLAR LİGİ TEKRAR"
OLD_GROUPS = ("🏐 VOLEYBOL CANLI", "🏐 KUZEYBORU", "🏐 VOLEYBOL HLS", GROUP_LIVE, GROUP_REPLAY)
ISTANBUL = ZoneInfo("Europe/Istanbul")
MAX_VIDEOS = 50

SEED_VIDEO_URLS = ["https://www.youtube.com/watch?v=cMM1VRfJlpI"]

OPTIONS = {
    "quiet": True, "no_warnings": True, "ignoreerrors": True,
    "extract_flat": "in_playlist", "playlistend": MAX_VIDEOS,
    "skip_download": True, "socket_timeout": 30, "retries": 2,
    "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    "allow_unplayable_formats": True,
}
DETAIL_OPTIONS = {
    "quiet": True, "no_warnings": True, "ignoreerrors": False,
    "skip_download": True, "socket_timeout": 30, "retries": 2,
    "extractor_args": {"youtube": {"player_client": ["android", "web", "mweb"]}},
    "allow_unplayable_formats": True,
}

def clean_title(v): return re.sub(r"\s+", " ", str(v or "TVF Voleybol Yayini")).strip()[:250]
def normalize_text(v):
    v = str(v or "").lower().replace("ı","i")
    v = unicodedata.normalize("NFKD", v)
    return "".join(c for c in v if not unicodedata.combining(c))
def team_priority(t):
    t = normalize_text(t)
    if "kuzeyboru maxi" in t: return 0
    if "kuzeyboru" in t: return 1
    return 2
def get_video_id(value):
    if isinstance(value, dict): value = value.get("id") or value.get("url") or ""
    if not isinstance(value, str): return ""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})", value)
    if m: return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value): return value
    return ""
def get_thumbnail(info, entry, video_id):
    for source in (info or {}, entry or {}):
        thumbs = source.get("thumbnails") or []
        valid = [x for x in thumbs if isinstance(x, dict) and x.get("url")]
        if valid:
            valid.sort(key=lambda x: x.get("width") or 0, reverse=True)
            return valid[0]["url"]
        if source.get("thumbnail"): return source["thumbnail"]
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
def get_match_time(info, entry):
    for source in (info or {}, entry or {}):
        for field in ("scheduled_start_time","release_timestamp","timestamp"):
            val = source.get(field)
            if val:
                try:
                    dt = datetime.fromtimestamp(float(val), timezone.utc)
                    return dt.astimezone(ISTANBUL).strftime("%d.%m.%Y %H:%M")
                except: pass
    return "Tarih bekleniyor"
def get_state(info, entry):
    info=info or {}; entry=entry or {}
    status = info.get("live_status") or entry.get("live_status") or ""
    if info.get("is_live") or status=="is_live": return "CANLI"
    if info.get("is_upcoming") or status=="is_upcoming": return "YAKLAŞAN"
    if status=="was_live": return "TAMAMLANDI"
    return "YAYIN"
def get_hls_url(info):
    info=info or {}; cands=[]
    for item in info.get("formats") or []:
        if not isinstance(item, dict): continue
        url=item.get("url") or ""; proto=str(item.get("protocol") or "").lower()
        if "m3u8" in url.lower() or "m3u8" in proto or "hls" in proto: cands.append(item)
    if cands:
        cands.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)
        return cands[0].get("url","")
    for k in ("manifest_url","hls_manifest_url","url"):
        v=info.get(k) or ""
        if "m3u8" in v.lower(): return v
    return ""
def load_takvim():
    try:
        with open(TAKVIM_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return []
def takvimden_tarih_bul(title, takvim):
    tn=normalize_text(title)
    for mac in takvim:
        hn=normalize_text(mac.get("home") or ""); an=normalize_text(mac.get("away") or "")
        if hn and an and hn in tn and an in tn: return f"{mac['date']} {mac['time']}"
    return None

TAKVIM = load_takvim()

def scan_video(ydl, video_id, entry=None):
    entry=entry or {}
    youtube_url=f"https://www.youtube.com/watch?v={video_id}"
    print(f"\nVideo: {youtube_url}")
    try: info=ydl.extract_info(youtube_url, download=False) or {}
    except Exception as e:
        print(f"Bilgi alınamadı: {e}"); info={}
    title=clean_title(info.get("title") or entry.get("title") or video_id)
    state=get_state(info, entry)
    hls_url=get_hls_url(info)
    match_time=get_match_time(info, entry)
    if match_time=="Tarih bekleniyor":
        tb=takvimden_tarih_bul(title, TAKVIM)
        if tb: match_time=tb
    if not hls_url and state=="YAKLAŞAN":
        print(f"⏳ YAKLAŞAN: {title} | {match_time}")
        return {"video_id":video_id,"name":title,"title":title,"youtube_url":youtube_url,"stream_url":"","thumbnail":get_thumbnail(info,entry,video_id),"match_time":match_time,"state":state,"hls_status":"YAKLAŞAN","priority":team_priority(title),"is_replay":False,"checked_at":datetime.now(timezone.utc).isoformat()}
    if not hls_url:
        print(f"⏳ HLS yok: {title}")
        return None
    is_replay = state=="TAMAMLANDI"
    print(f"{'🔁 TEKRAR' if is_replay else '🔴 CANLI'} HLS bulundu: {title}")
    return {"video_id":video_id,"name":title,"title":title,"youtube_url":youtube_url,"stream_url":hls_url,"thumbnail":get_thumbnail(info,entry,video_id),"match_time":match_time,"state":state,"hls_status":"HLS_BULUNDU","priority":team_priority(title),"is_replay":is_replay,"channel_id":CHANNEL_ID,"checked_at":datetime.now(timezone.utc).isoformat()}

def scan_channel():
    print("MIRTI68 - TÜM VOLEYBOL HLS TARAMA")
    entries=[]; video_ids=[]; seen=set()
    for url in SEED_VIDEO_URLS:
        vid=get_video_id(url)
        if vid and vid not in seen: seen.add(vid); video_ids.append(vid)
    co=dict(OPTIONS)
    if os.path.isfile("cookies.txt"): co["cookiefile"]="cookies.txt"
    try:
        with YoutubeDL(co) as ydl:
            pl=ydl.extract_info(CHANNEL_URL, download=False)
            if pl:
                entries=pl.get("entries") or []
                print(f"Kanal kayıt: {len(entries)}")
                for e in entries:
                    if not e: continue
                    vid=get_video_id(e)
                    if vid and vid not in seen: seen.add(vid); video_ids.append(vid)
    except Exception as e: print(f"Kanal hatası: {e}")
    print(f"Kontrol edilecek: {len(video_ids)}")
    results=[]
    det=dict(DETAIL_OPTIONS)
    if os.path.isfile("cookies.txt"): det["cookiefile"]="cookies.txt"
    with YoutubeDL(det) as d_ydl:
        for idx, vid in enumerate(video_ids,1):
            print(f"[{idx}/{len(video_ids)}] {vid}")
            ent=next((x for x in entries if get_video_id(x)==vid), {})
            try:
                it=scan_video(d_ydl, vid, ent)
                if it: results.append(it)
            except Exception as e: print(f"Hata: {e}")
    results.sort(key=lambda x: (x["priority"], 0 if x["state"]=="CANLI" else 1, x["match_time"]))
    return results

def remove_old_groups(lines):
    out=[]; skip=False
    markers=[f'group-title="{g}"' for g in OLD_GROUPS]
    for line in lines:
        s=line.strip()
        if s.startswith("#EXTINF:"):
            if any(m in s for m in markers): skip=True; continue
            skip=False; out.append(line); continue
        if skip:
            if s and not s.startswith("#"): skip=False; continue
            if s.startswith("#"): continue
        out.append(line)
    return out

def atomic_write(path, content):
    d=os.path.dirname(path) or "."
    fd, tp = tempfile.mkstemp(prefix="mirti68_", dir=d)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as f: f.write(content)
        os.replace(tp, path)
    except:
        if os.path.exists(tp): os.remove(tp)
        raise

def save_files(items):
    json_content=json.dumps({"channel":"TVF Voleybol TV","channel_id":CHANNEL_ID,"channel_url":CHANNEL_URL,"updated_at":datetime.now(timezone.utc).isoformat(),"total":len(items),"hls_total":sum(1 for i in items if i.get("stream_url")),"matches":items}, ensure_ascii=False, indent=2)
    atomic_write(RESULT_FILE, json_content)
    hls_live=[i for i in items if i.get("stream_url") and not i.get("is_replay")]
    hls_replay=[i for i in items if i.get("stream_url") and i.get("is_replay")]
    # En azından tekrarlar için M3U oluşsun
    target_items = hls_live + hls_replay[:15]
    if not target_items:
        print("⚠️ HLS bulunamadı, M3U değiştirilmedi")
        return
    if os.path.isfile(MASTER_FILE):
        with open(MASTER_FILE,"r",encoding="utf-8-sig") as f: old=f.readlines()
    else: old=["#EXTM3U\n"]
    base=remove_old_groups(old)
    if not any(l.strip()=="#EXTM3U" for l in base): base.insert(0,"#EXTM3U\n")
    new=list(base)
    if new and not new[-1].endswith("\n"): new[-1]+="\n"
    for item in hls_live:
        logo=item.get("thumbnail","").replace('"',"%22")
        lt=f' tvg-logo="{logo}"' if logo else ""
        new.append(f'#EXTINF:-1{lt} group-title="{GROUP_LIVE}",{item["name"]} | {item["match_time"]} | CANLI\n')
        new.append(item["stream_url"]+"\n")
    for item in hls_replay:
        logo=item.get("thumbnail","").replace('"',"%22")
        lt=f' tvg-logo="{logo}"' if logo else ""
        # Sultanlar Ligi öncelikli ekle
        if "sultanlar" in normalize_text(item["name"]) or "kuzeyboru" in normalize_text(item["name"]):
            new.append(f'#EXTINF:-1{lt} group-title="{GROUP_REPLAY}",{item["name"]} | {item["match_time"]} | TEKRAR\n')
            new.append(item["stream_url"]+"\n")
    atomic_write(MASTER_FILE, "".join(new))
    print(f"✅ M3U: {len(hls_live)} canlı + {len([i for i in hls_replay if 'kuzeyboru' in normalize_text(i['name']) or 'sultanlar' in normalize_text(i['name'])])} tekrar")

def main():
    print("MIRTI68 VOLEYBOL HLS BOT")
    items=scan_channel()
    if not items: print("Video yok, boş JSON yazılıyor"); items=[]
    save_files(items)
    print("BİTTİ")

if __name__=="__main__": main()
