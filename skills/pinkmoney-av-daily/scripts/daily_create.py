#!/usr/bin/env python3
import os, sys, time, subprocess, re
from datetime import datetime
from pathlib import Path
import requests

WORKSPACE    = Path(__file__).resolve().parent
RENDER_PY    = WORKSPACE / "pinkmoney_render.py"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
TAVILY_KEY   = os.environ.get("TAVILY_API_KEY", "")
TG_BOT_TOKEN = "8627190890:AAG5jJ8WjlaFdVJnWbgAFzB98GUoi4mQQ04"
TG_CHAT_ID   = "5390091587"
GITHUB_REPO  = "https://github.com/Loongint/pinkmoney_AV_Daily"

DATE    = datetime.now().strftime("%Y-%m-%d")
OUT_DIR = WORKSPACE / DATE
LOG     = OUT_DIR / "run.log"

# ─── 基础工具 ─────────────────────────────────────────────────

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

def check(condition, step, detail=""):
    if not condition:
        msg = f"❌ FAILED: {step}"
        if detail:
            msg += f"\n{detail}"
        log("CHECK FAILED", msg)
        notify(f"🚨 pink;money 流程中断\n{msg}")
        sys.exit(1)
    log("CHECK ✅", step)

# ─── 信息收集 ──────────────────────────────────────────────────

def tavily_search(query, topic="general", time_range="day", max_results=5):
    if not TAVILY_KEY:
        return {"answer": "", "results": []}
    resp = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
        json={"query": query, "topic": topic, "time_range": time_range,
              "max_results": max_results, "include_answer": True},
        timeout=15)
    if resp.status_code == 200:
        return resp.json()
    return {"answer": "", "results": []}

def read_user_state():
    mem_path = WORKSPACE / "memory" / f"{DATE}.md"
    if not mem_path.exists():
        return ""
    return mem_path.read_text(encoding="utf-8")[:1500]

def gather_world_signals():
    log("STEP - 信息收集", f"Tavily search: {DATE}")
    month_day = f"March {DATE.split('-')[2]}"
    results = {}

    r_news = tavily_search(
        f"{DATE} world news today politics technology science economy environment",
        topic="news", time_range="day", max_results=10)
    results["news_answer"] = r_news.get("answer") or ""
    results["news_items"]  = "\n".join(
        f"- {r['title']}: {r['content'][:120]}" for r in r_news.get("results", []))

    r_culture = tavily_search(
        f"{DATE} art music film culture entertainment exhibition concert release today",
        topic="news", time_range="day", max_results=5)
    results["culture_answer"] = r_culture.get("answer") or ""
    results["culture_items"]  = "\n".join(
        f"- {r['title']}: {r['content'][:120]}" for r in r_culture.get("results", []))

    r_hist = tavily_search(
        f"{month_day} history anniversary national holiday commemorations on this day",
        time_range="week", max_results=7)
    results["history_answer"] = r_hist.get("answer", "")
    results["history_items"]  = "\n".join(
        f"- {r['title']}: {r['content'][:120]}" for r in r_hist.get("results", [])[:5])

    r_taoism   = tavily_search(f"{DATE[:4]}年{int(DATE[5:7])}月{int(DATE[8:])}日 道教 农历 节气 宜忌 传统", max_results=3)
    r_buddhism = tavily_search(f"March 15 2026 Buddhist holiday significance lunar calendar", max_results=3)
    r_catholic = tavily_search(f"March 15 2026 Catholic saint feast day liturgical calendar", max_results=3)
    r_astro    = tavily_search(f"March 15 2026 astrology sun moon Pisces Aries transit energy", max_results=3)
    r_tarot    = tavily_search(f"March 15 2026 tarot card of the day reading energy", max_results=3)

    results["mystic_taoism"]   = r_taoism.get("answer") or ""
    results["mystic_buddhism"] = r_buddhism.get("answer") or ""
    results["mystic_catholic"] = r_catholic.get("answer") or ""
    results["mystic_astro"]    = r_astro.get("answer") or ""
    results["mystic_tarot"]    = r_tarot.get("answer") or ""
    results["user_state"]      = read_user_state()

    summary = (
        f"[新闻] {results['news_answer'][:150]}\n"
        f"[文化] {results['culture_answer'][:150]}\n"
        f"[历史] {results['history_answer'][:150]}\n"
        f"[玄学-道教] {results['mystic_taoism'][:80]}\n"
        f"[玄学-佛教] {results['mystic_buddhism'][:80]}\n"
        f"[玄学-天主教] {results['mystic_catholic'][:80]}\n"
        f"[玄学-占星] {results['mystic_astro'][:80]}\n"
        f"[玄学-塔罗] {results['mystic_tarot'][:80]}\n"
        f"[用户状态] {'有' if results['user_state'] else '无'} memory 记录"
    )
    log("STEP - 信息完成", summary)
    return results

# ─── 渲染 ──────────────────────────────────────────────────────

def fix_sc_nrt(sc_path):
    code = Path(sc_path).read_text()
    if '.add;' not in code:
        return
    def to_d_recv(m):
        block = re.sub(r'\s*\}\s*\)\s*\.add\s*;$', '}).asBytes', m.group(1).rstrip())
        return f'score.add([0.0, ["/d_recv", {block}]]);'
    fixed = re.sub(r'(SynthDef\(.*?\}\s*\)\s*\.add\s*;)', to_d_recv, code, flags=re.DOTALL)
    Path(sc_path).write_text(fixed)
    log("SC修复", "SynthDef .add → d_recv 自动转换完成")

def render_audio(osc_path, sc_path, wav_path, duration=30):
    fix_sc_nrt(sc_path)
    check(Path(sc_path).exists(), f"SC文件存在: {sc_path}")
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    log("STEP - sclang生成OSC", str(sc_path))
    result = subprocess.run(["sclang", str(sc_path)], env=env, timeout=60,
                            capture_output=True, text=True)
    check(Path(osc_path).exists(), "OSC score 生成", result.stderr[-300:])

    log("STEP - 音频渲染", f"scsynth NRT  osc={osc_path}")
    t0 = time.time()
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", str(duration + 0.5),
                    "/tmp/pm_silent.wav"], capture_output=True)
    subprocess.run(["scsynth", "-N", str(osc_path), "/tmp/pm_silent.wav", str(wav_path),
                    "44100", "wav", "int16", "-o", "2"],
                   timeout=120, capture_output=True)
    check(Path(wav_path).exists(), "WAV 文件生成")

    vol = subprocess.run(["ffmpeg", "-i", str(wav_path), "-af", "volumedetect",
                          "-f", "null", "/dev/null"], capture_output=True, text=True)
    max_vol = re.search(r"max_volume:\s*([-\d.]+)", vol.stderr)
    max_db  = float(max_vol.group(1)) if max_vol else -99
    check(max_db > -80, f"音频有声音 (max: {max_db}dB)", "scsynth 渲染出静音，检查 SynthDef")
    log("STEP - 音频完成", f"✅  大小:{Path(wav_path).stat().st_size//1024}KB  max:{max_db}dB  耗时:{time.time()-t0:.0f}s")

def render_video(glsl_path, sc_path, wav_path, mp4_path, duration=30):
    check(Path(glsl_path).exists(), f"GLSL文件存在: {glsl_path}")
    check(Path(sc_path).exists(),   f"SC文件存在: {sc_path}")
    log("STEP - 视频渲染", f"1920x1080 {duration}s @ 30fps")
    t0  = time.time()
    cmd = [sys.executable, str(RENDER_PY),
           "--glsl", str(glsl_path), "--sc", str(sc_path),
           "--output", str(mp4_path), "--duration", str(duration), "--no-audio"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    check(Path(mp4_path).exists(), "MP4 视频生成", result.stderr[-500:])

    if wav_path and Path(wav_path).exists():
        log("STEP - 合并音频", "ffmpeg -map")
        merged = str(mp4_path).replace(".mp4", "_final.mp4")
        r = subprocess.run([
            "ffmpeg", "-y", "-i", str(mp4_path), "-i", str(wav_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest",
            merged], capture_output=True, text=True)
        check(Path(merged).exists(), "合并音视频", r.stderr[-300:])
        vol = subprocess.run(["ffmpeg", "-i", merged, "-af", "volumedetect",
                              "-f", "null", "/dev/null"], capture_output=True, text=True)
        max_vol = re.search(r"max_volume:\s*([-\d.]+)", vol.stderr)
        max_db  = float(max_vol.group(1)) if max_vol else -99
        check(max_db > -80, f"合并后音频有声 (max: {max_db}dB)")
        Path(merged).rename(mp4_path)

    log("STEP - 视频完成", f"✅  大小:{Path(mp4_path).stat().st_size//1024}KB  耗时:{time.time()-t0:.0f}s")

# ─── 存档 ──────────────────────────────────────────────────────

def generate_post_text(theme_zh, theme_en, theme_note, glsl_path):
    date_path = Path(glsl_path).parent.name
    glsl_url  = f"{GITHUB_REPO}/blob/main/{date_path}/{Path(glsl_path).name}"
    sc_url    = f"{GITHUB_REPO}/blob/main/{date_path}/{Path(glsl_path).name.replace('.frag', '.scd')}"
    note_clean = theme_note.strip().rstrip(".")
    sentence   = note_clean.split(";")[0].strip()
    sentence   = sentence[0].upper() + sentence[1:] if sentence else note_clean

    post = (
        f"{theme_zh} / {theme_en}\n"
        f"— {sentence}\n\n"
        f"glsl → {glsl_url}\n"
        f"sc   → {sc_url}\n\n"
        f"#generativeart #glsl #supercollider #audiovisual #shader"
    )
    post_path = Path(glsl_path).parent / "post.txt"
    post_path.write_text(post, encoding="utf-8")
    log("STEP - Post文字生成", f"\n{post}")
    return post

def archive_notion(theme, glsl_code, sc_code):
    log("STEP - Notion存档", f"主题:{theme}")
    if not NOTION_TOKEN:
        log("STEP - Notion跳过", "NOTION_TOKEN 未设置")
        return ""
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
    rel_files = [f"{DATE}/{DATE}.frag", f"{DATE}/{DATE}.scd", f"{DATE}/run.log"]
    existing  = [f for f in rel_files if (WORKSPACE / f).exists()]
    if not existing:
        log("STEP - GitHub跳过", "无文件")
        return
    subprocess.run(["git", "-C", str(WORKSPACE), "add"] + existing, capture_output=True)
    subprocess.run(["git", "-C", str(WORKSPACE), "commit", "-m", f"{DATE}: {theme}"],
                   capture_output=True)
    result = subprocess.run(["git", "-C", str(WORKSPACE), "push"],
                            capture_output=True, text=True, timeout=30)
    check(result.returncode == 0, "GitHub push", result.stderr.strip()[-200:])
    log("STEP - GitHub完成", f"✅ pushed {DATE}/")

# ─── 发布（三渠道）─────────────────────────────────────────────

def post_xhs(mp4_path, theme_zh, theme_en, post_text):
    log("STEP - 小红书发布", str(mp4_path))
    title = f"Daily Audiovisual Livecoding - {datetime.now().strftime('%y/%m/%d')}"
    text  = f"{theme_zh} / {theme_en}\n\n{post_text.split(chr(10)*2)[0]}\n\n#audiovisual #livecoding #glsl #supercollider #pinkmoney"
    result = subprocess.run(
        [sys.executable, str(WORKSPACE / "post_xhs.py"),
         "--video", str(mp4_path), "--title", title, "--text", text,
         "--screenshot-dir", str(OUT_DIR)],
        capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        log("STEP - 小红书完成", f"✅\n{result.stdout[-200:]}")
    else:
        log("STEP - 小红书失败", f"returncode={result.returncode}\n{result.stderr[-300:]}")

def post_weibo(mp4_path, post_text):
    log("STEP - 微博发布", str(mp4_path))
    session_file = os.environ.get("WEIBO_SESSION_FILE", "/mnt/c/Users/PC/weibo_session.json")
    if not Path(session_file).exists():
        log("STEP - 微博跳过", f"session 文件不存在: {session_file}")
        return ""
    result = subprocess.run(
        [sys.executable, str(WORKSPACE / "post_weibo.py"),
         "--video", str(mp4_path),
         "--title", post_text.split("\n")[0][:30],
         "--text",  post_text],
        capture_output=True, text=True, timeout=300)
    url = next((l.replace("result:", "").strip()
                for l in result.stdout.splitlines() if l.startswith("result:")), "")
    if url:
        log("STEP - 微博完成", f"✅ {url}")
    else:
        log("STEP - 微博失败", (result.stdout + result.stderr)[-300:])
    return url

def post_instagram(mp4_path, caption):
    log("STEP - Instagram发布", str(mp4_path))
    if not os.environ.get("INSTAGRAM_SESSIONID"):
        log("STEP - Instagram跳过", "INSTAGRAM_SESSIONID 未设置")
        return ""
    result = subprocess.run(
        [sys.executable, str(WORKSPACE / "post_instagram.py"),
         "--video", str(mp4_path), "--caption", caption],
        capture_output=True, text=True, timeout=300)
    url = next((l.replace("result:", "").strip()
                for l in result.stdout.splitlines() if l.startswith("result:")), "")
    if url:
        log("STEP - Instagram完成", f"✅ {url}")
    else:
        log("STEP - Instagram失败", (result.stdout + result.stderr)[-300:])
    return url

# ─── 主流程 ────────────────────────────────────────────────────

def run(theme, glsl_code, sc_code, duration=30):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    log("START", f"date:{DATE}  theme:{theme}  duration:{duration}s")

    glsl_path = OUT_DIR / f"{DATE}.frag"
    sc_path   = OUT_DIR / f"{DATE}.scd"
    osc_path  = Path("/tmp/pm_score.osc")
    wav_path  = OUT_DIR / f"{DATE}.wav"
    mp4_path  = OUT_DIR / f"{DATE}.mp4"

    check(glsl_code.strip(), "GLSL代码不为空")
    check(sc_code.strip(),   "SC代码不为空")
    glsl_path.write_text(glsl_code)
    sc_path.write_text(sc_code)
    log("CHECK ✅", f"代码写入: {glsl_path.name} / {sc_path.name}")

    # 渲染
    render_audio(osc_path, sc_path, wav_path, duration)
    render_video(glsl_path, sc_path, wav_path, mp4_path, duration)

    # 存档
    notion_url = archive_notion(theme, glsl_code, sc_code)
    push_github(theme)

    # 生成 post 文字
    theme_zh = theme.split(" | ")[0].strip() if " | " in theme else theme.split(" / ")[0].strip()
    theme_en = theme.split(" | ")[1].strip() if " | " in theme else (theme.split(" / ")[1].strip() if " / " in theme else theme)
    post_text = generate_post_text(theme_zh, theme_en, theme, str(glsl_path))

    # 发布三渠道
    post_xhs(mp4_path, theme_zh, theme_en, post_text)
    weibo_url = post_weibo(mp4_path, post_text)
    ig_caption = post_text + "\n\n#glsl #supercollider #audiovisual #livecoding #generativeart #shaderart"
    ig_url = post_instagram(mp4_path, ig_caption)

    log("DONE", (
        f"✅ 总耗时:{time.time()-t_start:.0f}s\n"
        f"主题:{theme}\n"
        f"mp4:{mp4_path}\n"
        f"notion:{notion_url}\n"
        f"weibo:{weibo_url}\n"
        f"instagram:{ig_url}"
    ))
    return str(mp4_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme",    required=True)
    parser.add_argument("--glsl",     required=True)
    parser.add_argument("--sc",       required=True)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()
    run(
        theme     = args.theme,
        glsl_code = open(args.glsl).read(),
        sc_code   = open(args.sc).read(),
        duration  = args.duration
    )
