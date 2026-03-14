# pink;money AV Daily 每日流程参考

## 目录结构

```
workspace/
├── daily_create.py        # 主控脚本（唯一入口）
├── pinkmoney_render.py    # GLSL headless 渲染
├── post_xhs.py            # 小红书发布（Playwright）
├── post_weibo.py          # 微博发布（Playwright）
├── post_instagram.py      # Instagram 发布（instagrapi）
├── .env                   # 环境变量（不进 git）
├── .instagram_session.json
└── YYYY-MM-DD/
    ├── YYYY-MM-DD.frag    # GLSL shader
    ├── YYYY-MM-DD.scd     # SuperCollider score
    ├── YYYY-MM-DD.wav     # 渲染音频
    ├── YYYY-MM-DD.mp4     # 最终视频（含音频）
    ├── post.txt           # 发布文字（自动生成）
    └── run.log            # 每步日志

skills/pinkmoney-av-daily/
├── SKILL.md
└── references/
    ├── DAILY_AGENT_TASK.md
    ├── pipeline.md         ← 本文件
    └── theme_methodology.md
```

## 环境依赖

- Python 3：`moderngl` `moderngl-window` `Pillow` `numpy` `requests` `instagrapi` `playwright`
- SuperCollider：`sclang` `scsynth`（sc3-plugins 已安装）
- ffmpeg 6+
- 字体：`/mnt/c/Windows/Fonts/consola.ttf`（Consolas）

安装依赖：
```bash
pip install moderngl moderngl-window Pillow numpy requests instagrapi playwright
playwright install chromium
```

## .env 内容

```
GITHUB_TOKEN=<github_pat>
NOTION_TOKEN=<notion_token>
TAVILY_API_KEY=<tavily_key>
INSTAGRAM_SESSIONID=<sessionid>
WEIBO_SESSION_FILE=/mnt/c/Users/PC/weibo_session.json
XHS_SESSION_FILE=/mnt/c/Users/PC/xhs_session.json
```

## 运行命令（唯一入口）

```bash
cd /home/pinkmoney/.openclaw/workspace
source .env
python3 daily_create.py \
  --theme "中文标题 | English Title" \
  --glsl YYYY-MM-DD/YYYY-MM-DD.frag \
  --sc   YYYY-MM-DD/YYYY-MM-DD.scd \
  --duration 30
```

## 完整流程

```
渲染
  fix_sc_nrt        → .add 自动修复为 d_recv
  sclang            → /tmp/pm_score.osc
  scsynth NRT       → YYYY-MM-DD.wav
  pinkmoney_render  → YYYY-MM-DD.mp4（无音频）
  ffmpeg merge      → YYYY-MM-DD.mp4（含音频，覆盖）

存档
  Notion            → pink;money · DATE · 主题
  GitHub push       → DATE/ 目录

生成 post 文字
  → post.txt（主题 + 一句话 + 代码链接 + hashtag）

发布（三渠道，失败不中断主流程）
  小红书            → Daily Audiovisual Livecoding - YY/MM/DD
  微博              → 主题 + 一句话 + 链接
  Instagram         → post.txt 内容 + 额外 hashtag
```

## SC NRT 关键规则

SynthDef 在 NRT 模式下**不能用 `.add`**，必须用 d_recv：
```supercollider
score.add([0.0, ["/d_recv", SynthDef(\pm_name, { ... }).asBytes]]);
```
`daily_create.py` 会自动检测并修复这个问题。

## GLSL 必须字段

```glsl
#version 330
uniform float u_time;
in vec2 v_uv;
```

## Check 机制

渲染步骤失败立刻发 Telegram 通知并退出。发布渠道失败只记录 log，不中断流程。

## 渲染性能参考

| 时长 | 分辨率 | 帧数 | 耗时（CPU） |
|------|--------|------|------------|
| 10s  | 1920×1080 | 300 | ~60s |
| 30s  | 1920×1080 | 900 | ~500s |
