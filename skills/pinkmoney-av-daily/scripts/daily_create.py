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
            timeout=2)
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

def _fix_sc_hf_clipping(sc_path) -> bool:
    """
    检测 SC 代码中的高频过载来源，自动修复：
    1. WhiteNoise → PinkNoise（激励源降频）
    2. Mix.ar([...]) 后添加 * 0.3 限幅
    3. 增加 RLPF/LPF 截止频率降低
    4. 添加 Limiter.ar
    返回 True 表示代码有修改。
    """
    code = Path(sc_path).read_text()
    original = code

    # 1. WhiteNoise → PinkNoise（高频能量减半）
    code = re.sub(r'\bWhiteNoise\.ar\(([^)]+)\)', r'PinkNoise.ar(\1)', code)

    # 2. Klank 激励振幅缩小（0.006 → 0.003，0.01 → 0.005 等）
    def scale_klank_amp(m):
        val = float(m.group(1))
        return f'PinkNoise.ar({val * 0.5:.4f})'
    code = re.sub(r'PinkNoise\.ar\((0\.\d+)\)', scale_klank_amp, code)

    # 3. 在 SynthDef 内 Mix.ar([...]) 后没有乘系数的，加 * 0.35
    #    匹配 ]) 结尾、后面接 * env 但没有先乘比例系数的情况
    code = re.sub(
        r'(\]) \* 0\.\d+\);',   # 已有乘系数，跳过
        lambda m: m.group(0),
        code
    )
    # 找 Mix.ar([...]) 紧接 * env 的，在中间插 * 0.35
    code = re.sub(
        r'(Mix\.ar\(\[.*?\]\))(;\s*\n\s*var sig)',
        r'\1 * 0.35\2',
        code, flags=re.DOTALL
    )

    # 4. RLPF/LPF 截止频率超过 1000Hz 的降低到 700Hz
    def lower_lpf(m):
        freq = float(m.group(2))
        if freq > 1000:
            return f'{m.group(1)}{700}'
        return m.group(0)
    code = re.sub(r'(RLPF\.ar\(sig,\s*)([\d.]+)', lower_lpf, code)
    code = re.sub(r'(LPF\.ar\(sig,\s*)([\d.]+)', lower_lpf, code)

    # 5. 在 Out.ar 前没有 Limiter 的 SynthDef 里加 Limiter
    #    匹配 sig = FreeVerb... 或最后一个 sig = ... 后、Out.ar 前
    code = re.sub(
        r'(sig = (?:FreeVerb|RLPF|LPF|Limiter)\.ar\([^;]+\);)(\s*Out\.ar)',
        lambda m: m.group(0) if 'Limiter' in m.group(1) else
                  m.group(1) + '\n    sig = Limiter.ar(sig, 0.6);' + m.group(2),
        code
    )

    changed = code != original
    if changed:
        Path(sc_path).write_text(code)
        log("SC高频修复", "✅ WhiteNoise→PinkNoise + 振幅缩减 + Limiter")
    else:
        log("SC高频修复", "⚠️ 未找到可自动修复的高频过载来源")
    return changed


def fix_sc_nrt(sc_path):
    code = Path(sc_path).read_text()
    changed = False
    if '.add;' in code:
        def to_d_recv(m):
            block = re.sub(r'\s*\}\s*\)\s*\.add\s*;$', '}).asBytes', m.group(1).rstrip())
            return f'score.add([0.0, ["/d_recv", {block}]]);'
        code = re.sub(r'(SynthDef\(.*?\}\s*\)\s*\.add\s*;)', to_d_recv, code, flags=re.DOTALL)
        changed = True
        log("SC修复", "SynthDef .add → d_recv 自动转换完成")
    if '0.exit;' not in code:
        code = code.rstrip() + '\n0.exit;\n'
        changed = True
    if changed:
        Path(sc_path).write_text(code)

def render_audio(osc_path, sc_path, wav_path, duration=30):
    fix_sc_nrt(sc_path)
    check(Path(sc_path).exists(), f"SC文件存在: {sc_path}")
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    log("STEP - sclang生成OSC", str(sc_path))
    result = subprocess.run(["sclang", str(sc_path)], env=env, timeout=180,
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

    # ── 检测 true peak & loudness ──
    tp_result = subprocess.run(
        ["ffmpeg", "-i", str(wav_path), "-af", "loudnorm=print_format=json", "-f", "null", "/dev/null"],
        capture_output=True, text=True
    )
    tp_match = re.search(r'"input_tp"\s*:\s*"([-\d.]+)"', tp_result.stderr + tp_result.stdout)
    li_match = re.search(r'"input_i"\s*:\s*"([-\d.]+)"',  tp_result.stderr + tp_result.stdout)
    true_peak = float(tp_match.group(1)) if tp_match else max_db
    loudness  = float(li_match.group(1)) if li_match else -99

    # ── 检测高频 clipping（4kHz 以上 mean > -20dB 视为高频过载）──
    hf_result = subprocess.run(
        ["ffmpeg", "-i", str(wav_path), "-af", "highpass=f=4000,volumedetect", "-f", "null", "/dev/null"],
        capture_output=True, text=True
    )
    hf_mean_m = re.search(r"mean_volume:\s*([-\d.]+)", hf_result.stderr)
    hf_max_m  = re.search(r"max_volume:\s*([-\d.]+)",  hf_result.stderr)
    hf_mean = float(hf_mean_m.group(1)) if hf_mean_m else -99
    hf_max  = float(hf_max_m.group(1))  if hf_max_m  else -99
    log("STEP - 高频电平检测", f"4kHz+ mean={hf_mean}dB  max={hf_max}dB  true_peak={true_peak}dB  LUFS={loudness}")

    hf_clipping = hf_mean > -20.0   # 高频均值 > -20dB 判定为高频过载/clipping

    if hf_clipping:
        # 高频 clipping：SC 渲染已 clip，需重新修复 SC 代码并重渲染
        log("STEP - 高频过载检测", f"⚠️ 4kHz+ mean={hf_mean}dB，尝试修复 SC 代码并重渲染")
        fixed = _fix_sc_hf_clipping(sc_path)
        if fixed:
            # 重新生成 OSC
            env2 = os.environ.copy(); env2["QT_QPA_PLATFORM"] = "offscreen"
            subprocess.run(["sclang", str(sc_path)], env=env2, timeout=180, capture_output=True)
            if Path(osc_path).exists():
                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                                "anullsrc=r=44100:cl=stereo", "-t", str(duration + 0.5),
                                "/tmp/pm_silent.wav"], capture_output=True)
                subprocess.run(["scsynth", "-N", str(osc_path), "/tmp/pm_silent.wav", str(wav_path),
                                "44100", "wav", "int16", "-o", "2"],
                               timeout=120, capture_output=True)
                # 重新检测
                hf2 = subprocess.run(
                    ["ffmpeg", "-i", str(wav_path), "-af", "highpass=f=4000,volumedetect", "-f", "null", "/dev/null"],
                    capture_output=True, text=True)
                hf2_mean_m = re.search(r"mean_volume:\s*([-\d.]+)", hf2.stderr)
                hf2_mean = float(hf2_mean_m.group(1)) if hf2_mean_m else -99
                log("STEP - 高频重渲染结果", f"4kHz+ mean={hf2_mean}dB")
                hf_clipping = hf2_mean > -20.0
            else:
                log("STEP - 高频修复失败", "重新生成 OSC 失败，跳过重渲染")

    if hf_clipping:
        # 重渲染仍不达标，或修复失败：降噪后处理兜底
        log("STEP - 高频兜底处理", f"⚠️ 重渲染后仍 mean={hf_mean}dB，执行后处理降噪")
        rescue_path = Path(str(wav_path).replace(".wav", "_rescue.wav"))
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path),
             "-af", "equalizer=f=5000:t=h:w=2000:g=-14,equalizer=f=8000:t=h:w=3000:g=-24,"
                    "lowpass=f=10000:poles=2,loudnorm=I=-14:TP=-1:LRA=11",
             "-ar", "44100", "-ac", "2", str(rescue_path)],
            capture_output=True, timeout=60)
        if rescue_path.exists() and rescue_path.stat().st_size > 10000:
            import shutil; shutil.move(str(rescue_path), str(wav_path))
            log("STEP - 高频兜底完成", "✅ EQ 降噪后处理完成")
        _tg_alert(f"⚠️ 音频高频过载（4kHz+ mean={hf_mean}dB），已兜底处理\n日期:{DATE}\n建议检查 SC 代码中的 WhiteNoise/Klank 组合")

    if true_peak > -1.0:
        # 整体超载，normalize
        log("STEP - 音频超载修复", f"⚠️ true_peak={true_peak}dB LUFS={loudness} → 自动 normalize")
        norm_path = Path(str(wav_path).replace(".wav", "_norm.wav"))
        norm_result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path),
             "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=quiet",
             str(norm_path)],
            capture_output=True, text=True, timeout=60
        )
        if norm_path.exists() and norm_path.stat().st_size > 10000:
            import shutil
            shutil.move(str(norm_path), str(wav_path))
            log("STEP - 音频修复完成", f"✅ normalize 完成 → -14 LUFS / -1 dBTP")
        else:
            log("STEP - 音频修复失败", norm_result.stderr[-200:])
            _tg_alert(f"⚠️ 音频超载且 normalize 失败\n日期:{DATE}\ntrue_peak={true_peak}dB")
    elif not hf_clipping:
        log("STEP - 音频电平正常", f"true_peak={true_peak}dB  LUFS={loudness}")

    log("STEP - 音频完成", f"✅  大小:{Path(wav_path).stat().st_size//1024}KB  max:{max_db}dB  peak:{true_peak}dB  hf_mean:{hf_mean}dB  耗时:{time.time()-t0:.0f}s")

def render_video(glsl_path, sc_path, wav_path, mp4_path, duration=30):
    check(Path(glsl_path).exists(), f"GLSL文件存在: {glsl_path}")
    check(Path(sc_path).exists(),   f"SC文件存在: {sc_path}")
    # wav 必须存在且有声，否则直接 fail，不生成无声视频
    check(wav_path and Path(wav_path).exists(), f"WAV文件存在: {wav_path}")
    log("STEP - 视频渲染", f"1920x1080 {duration}s @ 30fps")
    t0  = time.time()
    cmd = [sys.executable, str(RENDER_PY),
           "--glsl", str(glsl_path), "--sc", str(sc_path),
           "--output", str(mp4_path), "--duration", str(duration), "--no-audio"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    check(Path(mp4_path).exists(), "MP4 视频生成", result.stderr[-500:])

    # 对比度检测：取5帧采样亮度均值，YAVG < 40 或 > 215 判定为异常
    log("STEP - 对比度检测", str(mp4_path))
    probe = subprocess.run([
        "ffmpeg", "-i", str(mp4_path),
        "-vf", "select='eq(n,15)+eq(n,100)+eq(n,300)+eq(n,600)+eq(n,850)',showinfo",
        "-vsync", "0", "-f", "null", "/dev/null"
    ], capture_output=True, text=True)
    yavg_vals = [int(m) for m in re.findall(r"mean:\[(\d+)", probe.stderr)]
    if yavg_vals:
        yavg = sum(yavg_vals) / len(yavg_vals)
        if yavg < 40:
            check(False, f"对比度检测失败：画面过暗 (YAVG={yavg:.1f}，阈值<40)，请重写 GLSL shader")
        elif yavg > 215:
            check(False, f"对比度检测失败：画面过亮 (YAVG={yavg:.1f}，阈值>215)，请重写 GLSL shader")
        else:
            log("STEP - 对比度正常", f"✅ YAVG={yavg:.1f}")
    else:
        log("STEP - 对比度检测跳过", "无法解析亮度数据")

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
    else:
        check(False, "合并音频失败：WAV 文件不存在，中止流程")

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
        "parent": {"type":"page_id","page_id":"18febe880d0280febba4e7865095f44c"},
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

def _tg_alert(msg: str):
    """发 TG 告警，不抛异常"""
    import urllib.request, urllib.parse
    token = os.environ.get("TG_BOT_TOKEN", "")
    chat  = os.environ.get("TG_CHAT_ID", "")
    if not token or not chat:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, timeout=10
        )
    except Exception:
        pass


def _run_publisher(cmd: list, name: str, timeout: int = 300) -> tuple[int, str, str]:
    """运行发布子进程，返回 (returncode, stdout, stderr)"""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def _check_xhs_success(stdout: str) -> bool:
    return "success" in stdout.lower() or "result:" in stdout


def _check_weibo_success(stdout: str) -> tuple[bool, str]:
    url = next((l.replace("result:", "").strip()
                for l in stdout.splitlines() if l.startswith("result:")), "")
    ok = bool(url) and "#done" not in url or "weibo.com" in url
    return ok, url


def _check_ig_success(url: str) -> bool:
    return bool(url) and "instagram.com/reel/" in url


def post_xhs(mp4_path, theme_zh, theme_en, post_text):
    log("STEP - 小红书发布", str(mp4_path))
    title = f"Daily Audiovisual Livecoding - {datetime.now().strftime('%y/%m/%d')}"
    body  = "\n\n".join(post_text.split("\n\n")[1:])
    text  = f"{theme_zh} / {theme_en}\n\n{body}\n\n#audiovisual #livecoding #glsl #supercollider #pinkmoney"
    cmd   = [sys.executable, str(WORKSPACE / "post_xhs.py"),
             "--video", str(mp4_path), "--title", title, "--text", text,
             "--screenshot-dir", str(OUT_DIR)]

    for attempt in range(2):
        rc, stdout, stderr = _run_publisher(cmd, "小红书")
        if rc == 0 and _check_xhs_success(stdout):
            log("STEP - 小红书完成", f"✅\n{stdout[-200:]}")
            return
        err = (stdout + stderr)[-300:]
        log("STEP - 小红书失败", f"attempt={attempt+1} rc={rc}\n{err}")
        if attempt == 0:
            log("STEP - 小红书重试", "等待 60s 后重试...")
            time.sleep(60)

    _tg_alert(f"⚠️ 小红书发布失败（2次重试后）\n日期:{DATE}\n错误:{err[-150:]}")


def post_weibo(mp4_path, post_text):
    log("STEP - 微博发布", str(mp4_path))
    session_file = os.environ.get("WEIBO_SESSION_FILE", "/mnt/c/Users/PC/weibo_session.json")
    if not Path(session_file).exists():
        log("STEP - 微博跳过", f"session 文件不存在: {session_file}")
        return ""
    cmd = [sys.executable, str(WORKSPACE / "post_weibo.py"),
           "--video", str(mp4_path),
           "--title", post_text.split("\n")[0][:30],
           "--text",  post_text]

    for attempt in range(2):
        rc, stdout, stderr = _run_publisher(cmd, "微博")
        ok, url = _check_weibo_success(stdout)
        if ok:
            log("STEP - 微博完成", f"✅ {url}")
            return url
        err = (stdout + stderr)[-300:]
        log("STEP - 微博失败", f"attempt={attempt+1} rc={rc}\n{err}")
        if attempt == 0:
            log("STEP - 微博重试", "等待 60s 后重试...")
            time.sleep(60)

    _tg_alert(f"⚠️ 微博发布失败（2次重试后）\n日期:{DATE}\n错误:{err[-150:]}")
    return ""


def post_instagram(mp4_path, caption):
    log("STEP - Instagram发布", str(mp4_path))
    sessionid = os.environ.get("INSTAGRAM_SESSIONID", "")
    if not sessionid:
        log("STEP - Instagram跳过", "INSTAGRAM_SESSIONID 未设置")
        return ""

    for attempt in range(2):
        try:
            from instagrapi import Client
            cl = Client()
            cl.set_proxy("http://172.27.32.1:7890")
            session_file = WORKSPACE / ".instagram_session.json"
            if session_file.exists():
                cl.load_settings(str(session_file))
            else:
                log("STEP - Instagram跳过", "session 文件不存在")
                return ""
            media = cl.clip_upload(str(Path(mp4_path).resolve()), caption)
            url = f"https://www.instagram.com/reel/{media.code}"
            cl.dump_settings(str(session_file))
            if _check_ig_success(url):
                log("STEP - Instagram完成", f"✅ {url}")
                return url
            raise ValueError(f"返回 URL 异常: {url}")
        except Exception as e:
            err = str(e)[:300]
            log("STEP - Instagram失败", f"attempt={attempt+1}\n{err}")
            if attempt == 0:
                log("STEP - Instagram重试", "等待 60s 后重试...")
                time.sleep(60)

    _tg_alert(f"⚠️ Instagram发布失败（2次重试后）\n日期:{DATE}\n错误:{err[-150:]}")
    return ""

# ─── 主流程 ────────────────────────────────────────────────────

def run(theme, glsl_code, sc_code, duration=30, theme_note=""):
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
    post_text = generate_post_text(theme_zh, theme_en, theme_note or theme, str(glsl_path))

    # 发布三渠道
    post_xhs(mp4_path, theme_zh, theme_en, post_text)
    weibo_url = post_weibo(mp4_path, post_text)
    ig_url = post_instagram(mp4_path, post_text)

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
    parser.add_argument("--theme",      required=True)
    parser.add_argument("--glsl",       required=True)
    parser.add_argument("--sc",         required=True)
    parser.add_argument("--duration",   type=int, default=30)
    parser.add_argument("--theme-note", default="", dest="theme_note")
    args = parser.parse_args()
    run(
        theme      = args.theme,
        glsl_code  = open(args.glsl).read(),
        sc_code    = open(args.sc).read(),
        duration   = args.duration,
        theme_note = args.theme_note
    )
