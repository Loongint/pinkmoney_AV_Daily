#!/usr/bin/env python3
import os, sys, time, subprocess, shutil
from datetime import datetime
from pathlib import Path
import requests

WORKSPACE    = Path("/home/pinkmoney/.openclaw/workspace")
RENDER_PY    = WORKSPACE / "pinkmoney_render.py"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
TG_BOT_TOKEN = "8627190890:AAG5jJ8WjlaFdVJnWbgAFzB98GUoi4mQQ04"
TG_CHAT_ID   = "5390091587"

DATE    = datetime.now().strftime("%Y-%m-%d")
OUT_DIR = WORKSPACE / DATE
LOG     = OUT_DIR / "run.log"

def notify(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": f"💜 pink;money\n{text}"},
            timeout=10)
    except Exception:
        pass

def log(step, content):
    ts    = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {step}\n{content}\n\n"
    print(entry, end="")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(entry)
    notify(f"[{ts}] {step}\n{content}")

def render_audio(osc_path, wav_path, duration=30):
    log("STEP - 音频渲染", f"scsynth NRT  osc={osc_path}")
    t0 = time.time()
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         "anullsrc=r=44100:cl=stereo", "-t", str(duration + 0.5),
         "/tmp/pm_silent.wav"],
        capture_output=True)
    subprocess.run(
        ["scsynth", "-N", osc_path, "/tmp/pm_silent.wav", str(wav_path),
         "44100", "wav", "int16", "-o", "2"],
        timeout=120, capture_output=True)
    ok   = Path(wav_path).exists()
    size = Path(wav_path).stat().st_size // 1024 if ok else 0
    log("STEP - 音频完成", f"状态:{'✅' if ok else '❌'}  大小:{size}KB  耗时:{time.time()-t0:.0f}s")
    return ok

def render_video(glsl_path, sc_path, osc_path, wav_path, mp4_path, duration=30):
    log("STEP - 视频渲染", f"1920x1080 {duration}s @ 30fps")
    t0  = time.time()
    cmd = [sys.executable, str(RENDER_PY),
           "--glsl", str(glsl_path),
           "--sc",   str(sc_path),
           "--output", str(mp4_path),
           "--duration", str(duration)]
    if osc_path and Path(osc_path).exists() and Path(wav_path).exists():
        cmd += ["--osc", str(osc_path)]
    else:
        cmd += ["--no-audio"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    ok   = Path(mp4_path).exists()
    size = Path(mp4_path).stat().st_size // 1024 if ok else 0
    log("STEP - 视频完成", f"状态:{'✅' if ok else '❌'}  大小:{size}KB  耗时:{time.time()-t0:.0f}s")
    if not ok:
        log("STEP - 视频错误", result.stderr[-800:])
    return ok

def archive_notion(theme, glsl_code, sc_code):
    log("STEP - Notion存档", f"主题:{theme}")
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    def code_blocks(code, lang):
        return [{"object":"block","type":"code","code":{
            "rich_text":[{"type":"text","text":{"content":c}}],"language":lang}}
            for c in [code[i:i+1900] for i in range(0, len(code), 1900)]]

    body = {
        "parent": {"type":"workspace","workspace":True},
        "properties": {"title":{"title":[{"text":{"content":f"pink;money · {DATE} · {theme}"}}]}},
        "children": [
            {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"主题"}}]}},
            {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":theme}}]}},
            {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"GLSL"}}]}},
            *code_blocks(glsl_code, "glsl"),
            {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"SuperCollider"}}]}},
            *code_blocks(sc_code, "plain text"),
        ]
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=body)
    if r.status_code == 200:
        url = r.json().get("url", "")
        log("STEP - Notion完成", f"✅ {url}")
        return url
    else:
        log("STEP - Notion失败", f"{r.status_code}: {r.text[:300]}")
        return ""

def push_github(theme):
    log("STEP - GitHub push", f"{DATE}/")
    rel_files = [
        f"{DATE}/today.frag",
        f"{DATE}/today.scd",
        f"{DATE}/run.log",
    ]
    existing = [f for f in rel_files if (WORKSPACE / f).exists()]
    if not existing:
        log("STEP - GitHub跳过", "无文件")
        return
    subprocess.run(["git", "-C", str(WORKSPACE), "add"] + existing, capture_output=True)
    subprocess.run(["git", "-C", str(WORKSPACE), "commit", "-m", f"{DATE}: {theme}"],
                   capture_output=True)
    result = subprocess.run(["git", "-C", str(WORKSPACE), "push"],
                            capture_output=True, text=True, timeout=30)
    ok = result.returncode == 0
    log("STEP - GitHub完成", f"{'✅' if ok else '❌'} {result.stderr.strip()[-200:]}")

def run(theme, glsl_code, sc_code, osc_path=None, duration=30):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    log("START", f"date:{DATE}  theme:{theme}  duration:{duration}s")

    glsl_path = OUT_DIR / "today.frag"
    sc_path   = OUT_DIR / "today.scd"
    wav_path  = OUT_DIR / "today.wav"
    mp4_path  = OUT_DIR / "today.mp4"

    glsl_path.write_text(glsl_code)
    sc_path.write_text(sc_code)

    audio_ok = render_audio(osc_path, wav_path, duration) if osc_path else False
    render_video(glsl_path, sc_path,
                 osc_path if audio_ok else None,
                 wav_path if audio_ok else None,
                 mp4_path, duration)
    notion_url = archive_notion(theme, glsl_code, sc_code)
    push_github(theme)

    log("DONE", f"总耗时:{time.time()-t_start:.0f}s  mp4:{mp4_path}  notion:{notion_url}")
    return str(mp4_path)

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme",    required=True)
    parser.add_argument("--glsl",     required=True)
    parser.add_argument("--sc",       required=True)
    parser.add_argument("--osc",      default=None)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()
    run(
        theme     = args.theme,
        glsl_code = open(args.glsl).read(),
        sc_code   = open(args.sc).read(),
        osc_path  = args.osc,
        duration  = args.duration
    )
