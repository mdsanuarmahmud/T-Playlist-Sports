#!/usr/bin/env python3
"""
fetch_and_build_sports.py
- Download remote bd.m3u
- Parse into entries
- Filter sports group/title
- Light check each stream (small GET)
- Write JSON and sports_playlists.m3u
"""
import re, requests, time, json, os
from typing import List, Dict

SRC_URL = "https://iptv-org.github.io/iptv/countries/bd.m3u"
OUT_JSON = "data/sports_channels.json"
OUT_M3U = "data/playlists/sports_playlists.m3u"
TIMEOUT = 10  # seconds for HTTP checks
USER_AGENT = "Mozilla/5.0 (compatible; PlaylistBot/1.0)"

def download_m3u(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text

def parse_m3u(text: str) -> List[Dict]:
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            extinf_raw = line
            m = re.match(r'#EXTINF:[^\s]*\s*(.*?)\s*,(.*)', extinf_raw)
            attrs_str = ""
            title = ""
            if m:
                attrs_str = m.group(1).strip()
                title = m.group(2).strip()
            else:
                if ',' in extinf_raw:
                    attrs_str = extinf_raw.split(',',1)[0]
                    title = extinf_raw.split(',',1)[1].strip()
            attrs = {}
            for attr_m in re.finditer(r'([A-Za-z0-9_\-]+)=\"([^\"]*)\"', attrs_str):
                attrs[attr_m.group(1)] = attr_m.group(2)
            extra_lines = []
            url = None
            i += 1
            while i < len(lines):
                ln = lines[i].strip()
                if ln == "" :
                    i += 1
                    continue
                if ln.startswith("#EXTINF"):
                    break
                if ln.startswith("#"):
                    extra_lines.append(ln)
                    i += 1
                    continue
                url = ln
                i += 1
                break
            entries.append({
                "extinf_raw": extinf_raw,
                "attrs": attrs,
                "title": title,
                "extra_lines": extra_lines,
                "url": url
            })
        else:
            i += 1
    return entries

def is_sports_entry(entry: Dict) -> bool:
    keyword = "sport"
    group = entry["attrs"].get("group-title","") or ""
    if keyword in group.lower():
        return True
    tvgid = entry["attrs"].get("tvg-id","")
    if keyword in tvgid.lower():
        return True
    if keyword in (entry["title"] or "").lower():
        return True
    if keyword in (entry["extinf_raw"] or "").lower():
        return True
    return False

def check_stream(url: str, headers: Dict=None, timeout:int=TIMEOUT):
    if not url:
        return False, None, "no-url"
    if not url.lower().startswith(("http://","https://")):
        return False, None, "non-http"
    headers = headers or {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=timeout, stream=True)
        status = r.status_code
        if status != 200:
            return False, None, f"status_{status}"
        try:
            chunk = next(r.iter_content(chunk_size=512), b"")
        except Exception:
            chunk = b""
        alive = bool(chunk and len(chunk) > 0)
        latency_ms = int(r.elapsed.total_seconds() * 1000)
        return alive, latency_ms, None if alive else "no-bytes"
    except Exception as e:
        return False, None, str(e)

def build_json_and_m3u(entries: List[Dict], out_json: str, out_m3u: str):
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(out_m3u) or ".", exist_ok=True)
    json_items = []
    with open(out_m3u, "w", encoding="utf-8") as m3f:
        m3f.write("#EXTM3U\n")
        for e in entries:
            item = {
                "channel_id": e["attrs"].get("tvg-id") or e["title"],
                "name": e["title"],
                "tvg-logo": e["attrs"].get("tvg-logo"),
                "group-title": e["attrs"].get("group-title"),
                "stream": e["url"],
                "extra_lines": e["extra_lines"],
                "fetched_at": int(time.time()),
                "alive": None,
                "latency_ms": None,
                "check_error": None
            }
            json_items.append(item)
            m3f.write(e["extinf_raw"] + "\n")
            for opt in e["extra_lines"]:
                m3f.write(opt + "\n")
            m3f.write((e["url"] or "") + "\n")
    with open(out_json, "w", encoding="utf-8") as jf:
        json.dump(json_items, jf, indent=2, ensure_ascii=False)
    print("Wrote M3U and initial JSON")

def main():
    print("Downloading:", SRC_URL)
    text = download_m3u(SRC_URL)
    print("Parsing...")
    entries = parse_m3u(text)
    print(f"Total entries parsed: {len(entries)}")
    sports = [e for e in entries if is_sports_entry(e)]
    print(f"Sports candidates: {len(sports)}")
    build_json_and_m3u(sports, OUT_JSON, OUT_M3U)
    print("Running health checks (this may take a while)...")
    with open(OUT_JSON, "r", encoding="utf-8") as f:
        items = json.load(f)
    for idx, item in enumerate(items):
        stream_url = item.get("stream")
        alive, latency, err = check_stream(stream_url)
        items[idx]["alive"] = bool(alive)
        items[idx]["latency_ms"] = latency
        items[idx]["check_error"] = err
        print(f"[{idx+1}/{len(items)}] {item.get('name')} -> alive={alive} latency={latency} err={err}")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print("Updated JSON with health checks:", OUT_JSON)
    print("Done.")

if __name__ == "__main__":
    main()
