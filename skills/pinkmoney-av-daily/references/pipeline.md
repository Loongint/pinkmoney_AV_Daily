# pink;money AV Daily 每日流程参考

## 环境依赖

- Python 3：`moderngl` `moderngl-window` `Pillow` `numpy` `requests`
- SuperCollider：`sclang` `scsynth`（sc3-plugins 已安装）
- ffmpeg 6+
- 字体：`/mnt/c/Windows/Fonts/consola.ttf`（Consolas）

安装 Python 依赖：
```bash
pip install moderngl moderngl-window Pillow numpy requests
```

## 目录结构

```
workspace/
├── YYYY-MM-DD/
│   ├── YYYY-MM-DD.frag   # GLSL shader
│   ├── YYYY-MM-DD.scd    # SuperCollider score
│   ├── YYYY-MM-DD.wav    # 渲染音频
│   ├── YYYY-MM-DD.mp4    # 最终视频
│   └── run.log           # 每步日志
├── .env                  # 环境变量（不进 git）
└── skills/pinkmoney-av-daily/scripts/
    ├── daily_create.py   # 主控：音频+视频+存档
    └── pinkmoney_render.py  # GLSL渲染工具
```

## .env 内容

```
GITHUB_TOKEN=<github_pat>
NOTION_TOKEN=<notion_token>
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

## 运行命令

```bash
cd /path/to/workspace
source .env
python3 skills/pinkmoney-av-daily/scripts/daily_create.py \
  --theme "主题文字" \
  --glsl YYYY-MM-DD/YYYY-MM-DD.frag \
  --sc   YYYY-MM-DD/YYYY-MM-DD.scd \
  --duration 30
```

## Check 机制

每步都会 check，失败立刻发 Telegram 通知并退出：
1. GLSL / SC 代码不为空
2. OSC score 生成成功
3. WAV 文件存在
4. 音频有声音（max > -80dB）
5. MP4 视频生成
6. 合并后音频有声
7. GitHub push 成功

## 渲染性能参考

| 时长 | 分辨率 | 帧数 | 耗时（CPU） |
|------|--------|------|------------|
| 10s  | 1920×1080 | 300 | ~60s |
| 30s  | 1920×1080 | 900 | ~500s |

## Telegram 通知

Bot Token 和 Chat ID 已 hardcode 在 `daily_create.py`，每步完成自动推送。
