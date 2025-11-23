# T-Playlist-Sports

Auto-update sports playlist from iptv-org (bd.m3u).

This repo fetches `https://iptv-org.github.io/iptv/countries/bd.m3u`,
extracts only sports channels, performs a quick health check, and
writes JSON + M3U outputs.

**Usage (local):**
1. python -m venv .venv
2. . .venv\Scripts\Activate.ps1
3. pip install -r requirements.txt
4. python scripts/fetch_and_build_sports.py
