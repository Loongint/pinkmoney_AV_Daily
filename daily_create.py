#!/usr/bin/env python3
import os, sys, time, json, subprocess, shutil, textwrap
from datetime import datetime
from pathlib import Path
import requests

WORKSPACE   = Path("/home/pinkmoney/.openclaw/workspace")
RENDER_PY   = WORKSPACE / "pinkmoney_render.py"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = "Loongint/pinkmoney_AV_Daily"
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
VAPI_KEY      = os.environ.get("VAPI_API_KEY", "")
VAPI_BASE_URL = "https://api.vapi.ai/v1"

DATE     = datetime.now().strftime("%Y-%m-%d")
OUT_DIR  = WORKSPACE / DATE
LOG_FILE = OUT_DIR / "run.log"

def log(step, content):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"\n[{ts}] {step}\n{content}\n"
    print(entry, end="")
    with open(LOG_FILE, "a") as f:
        f.write(entry)

def ai(prompt):
    r = requests.post(
        f"{VAPI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {VAPI_KEY}", "Content-Type": "application/json"},
        json={"model": "claude-sonnet-4-5", "max_tokens": 4096,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60
    )
    return r.json()["choices"][0]["message"]["content"]

def step1_research():
    log("STEP 1 - 信息收集", "搜索今日信息...")
    try:
        from kimi_search import search
        world   = search(f"{DATE} 今日重大事件 world events")
        culture = search(f"{DATE} 今日文化节日 religious cultural day")
        astro   = search(f"{DATE} 星象 月相 astrology moon phase")
        raw = f"世界事件:\n{world}\n\n文化节日:\n{culture}\n\n星象:\n{astro}"
    except Exception:
        raw = f"日期: {DATE}，无法获取实时数据，基于通识知识推断。"
    log("STEP 1 - 完成", raw[:500])
    return raw

def step2_theme(research):
    prompt = f"""你是 pink;money 创作智能体。
今日信息：
{research}

请根据以上信息，选定今日创作主题，要求：
- 一句诗意的中文短句（20字以内）
- 与新媒体艺术、内观、意识探索的气质吻合
- 背后有具体的文化/天象/事件依据

只输出主题句，不要解释。"""
    theme = ai(prompt).strip()
    log("STEP 2 - 主题确定", theme)
    return theme

def step3_glsl(theme):
    prompt = f"""你是 pink;money 创作智能体，负责生成 GLSL fragment shader。

今日主题：{theme}

要求：
- #version 330 开头
- 必须有 uniform float u_time; 和 in vec2 v_uv;
- 视觉意象与主题强相关
- 30秒内有明显动态变化节奏
- 不写任何注释
- 只输出纯 GLSL 代码，不要 markdown 代码块"""
    code = ai(prompt).strip()
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:-1])
    log("STEP 3a - GLSL生成", f"{len(code.splitlines())} 行")
    return code

def step3_sc(theme):
    prompt = f"""你是 pink;money 创作智能体，负责生成 SuperCollider NRT score。

今日主题：{theme}

要求：
- 使用 SynthDef + Score 结构，可被 scsynth NRT 渲染
- SynthDef 名称用 \\pm_ 前缀（如 \\pm_water）
- 音色、节奏与主题语义对应
- 时长30秒，score.add([30.5, [0]]) 结尾
- score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5) 最后一行
- 不写任何注释
- 只输出纯 SuperCollider 代码，不要 markdown 代码块"""
    code = ai(prompt).strip()
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:-1])
    log("STEP 3b - SC生成", f"{len(code.splitlines())} 行")
    return code

def step4_audio(sc_code, osc_path, wav_path, duration=30):
    scd_path = "/tmp/pm_gen.scd"
    with open(scd_path, "w") as f:
        f.write(sc_code)
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        ["sclang", scd_path], env=env, timeout=60,
        capture_output=True, text=True)
    if not os.path.exists(osc_path):
        log("STEP 4 - 音频", f"sclang 失败:\n{result.stderr[-500:]}")
        return False
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         "anullsrc=r=44100:cl=stereo", "-t", str(duration + 0.5),
         "/tmp/pm_silent.wav"], capture_output=True)
    subprocess.run(
        ["scsynth", "-N", osc_path, "/tmp/pm_silent.wav", wav_path,
         "44100", "wav", "int16", "-o", "2"],
        timeout=120, capture_output=True)
    ok = os.path.exists(wav_path)
    size = os.path.getsize(wav_path) // 1024 if ok else 0
    log("STEP 4 - 音频渲染", f"状态: {'✅' if ok else '❌'}  大小: {size}KB")
    return ok

def step5_video(glsl_path, sc_path, osc_path, wav_path, mp4_path, duration=30):
    t0 = time.time()
    cmd = [sys.executable, str(RENDER_PY),
           "--glsl", str(glsl_path),
           "--sc",   str(sc_path),
           "--output", str(mp4_path),
           "--duration", str(duration)]
    if os.path.exists(wav_path):
        cmd += ["--osc", osc_path]
    else:
        cmd += ["--no-audio"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    ok = os.path.exists(mp4_path)
    size = os.path.getsize(mp4_path) // 1024 if ok else 0
    log("STEP 5 - 视频渲染", f"状态: {'✅' if ok else '❌'}  耗时: {elapsed:.0f}s  大小: {size}KB")
    if not ok:
        print(result.stderr[-1000:])
    return ok

def step6_notion(theme, glsl_code, sc_code):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    def code_blocks(code, lang):
        chunks = [code[i:i+1900] for i in range(0, len(code), 1900)]
        return [{"object":"block","type":"code","code":{"rich_text":[{"type":"text","text":{"content":c}}],"language":lang}} for c in chunks]

    body = {
        "parent": {"type": "workspace", "workspace": True},
        "properties": {
            "title": {"title": [{"text": {"content": f"pink;money · {DATE} · {theme}"}}]}
        },
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
        log("STEP 6 - Notion", f"✅ {url}")
        return url
    else:
        log("STEP 6 - Notion", f"❌ {r.status_code}: {r.text[:200]}")
        return ""

def step7_github(theme):
    repo_dir = WORKSPACE
    files = [
        str(OUT_DIR / "today.frag"),
        str(OUT_DIR / "today.scd"),
        str(OUT_DIR / "run.log"),
    ]
    existing = [f for f in files if os.path.exists(f)]
    if not existing:
        log("STEP 7 - GitHub", "无文件可 push")
        return
    subprocess.run(["git", "-C", str(repo_dir), "add"] + [f.replace(str(repo_dir)+"/", "") for f in existing])
    subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", f"{DATE}: {theme}"],
                   capture_output=True)
    result = subprocess.run(["git", "-C", str(repo_dir), "push"],
                            capture_output=True, text=True)
    ok = result.returncode == 0
    log("STEP 7 - GitHub", f"{'✅' if ok else '❌'} push {DATE}/")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    log("START", f"pink;money daily create  {DATE}")

    research  = step1_research()
    theme     = step2_theme(research)
    glsl_code = step3_glsl(theme)
    sc_code   = step3_sc(theme)

    glsl_path = OUT_DIR / "today.frag"
    sc_path   = OUT_DIR / "today.scd"
    osc_path  = "/tmp/pm_score.osc"
    wav_path  = str(OUT_DIR / "today.wav")
    mp4_path  = str(OUT_DIR / "today.mp4")

    glsl_path.write_text(glsl_code)
    sc_path.write_text(sc_code)

    audio_ok = step4_audio(sc_code, osc_path, wav_path)
    video_ok = step5_video(glsl_path, sc_path, osc_path,
                           wav_path if audio_ok else "", mp4_path)
    notion_url = step6_notion(theme, glsl_code, sc_code)
    step7_github(theme)

    total = time.time() - t_start
    log("DONE", f"总耗时: {total:.0f}s\n主题: {theme}\n视频: {mp4_path}\nNotion: {notion_url}")

if __name__ == "__main__":
    main()
