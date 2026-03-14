#!/usr/bin/env python3
"""
Instagram Reels 发布脚本 — instagrapi
用法: python3 post_instagram.py --video path/to/video.mp4 --caption "描述"
"""
import os, sys, argparse
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

PROXY        = "http://172.27.32.1:7890"
SESSION_FILE = Path(__file__).parent / ".instagram_session.json"

def post_reel(video_path: str, caption: str) -> str:
    sessionid = os.environ.get("INSTAGRAM_SESSIONID", "")
    if not sessionid:
        print("[INS] ERROR: INSTAGRAM_SESSIONID 未设置")
        return ""
    try:
        from instagrapi import Client
        cl = Client()
        cl.set_proxy(PROXY)
        if SESSION_FILE.exists():
            cl.load_settings(str(SESSION_FILE))
        cl.login_by_sessionid(sessionid)
        media = cl.clip_upload(str(Path(video_path).resolve()), caption)
        url = f"https://www.instagram.com/reel/{media.code}"
        cl.dump_settings(str(SESSION_FILE))
        print(f"[INS] ✅ 发布成功: {url}")
        print(f"result: {url}")
        return url
    except Exception as e:
        print(f"[INS] ERROR: {e}")
        return ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",   required=True)
    parser.add_argument("--caption", required=True)
    args = parser.parse_args()
    post_reel(args.video, args.caption)

if __name__ == "__main__":
    main()
