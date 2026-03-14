---
name: pinkmoney-av-daily
description: pink;money 每日 AV 创作自动化流程。生成 GLSL fragment shader + SuperCollider NRT 音频，渲染合成 1920×1080 30s 视频，存档到 Notion 和 GitHub，并通过 Telegram 推送每步状态。使用场景：用户要求运行今日 AV 创作、触发 daily 生成、手动补跑某日创作、调试渲染管线。包含完整脚本：daily_create.py（主控）和 pinkmoney_render.py（GLSL渲染）。
---

# pink;money AV Daily

## 快速开始

**完整流程一条命令：**
```bash
cd /home/pinkmoney/.openclaw/workspace
source .env
python3 skills/pinkmoney-av-daily/scripts/daily_create.py \
  --theme "主题文字" \
  --glsl YYYY-MM-DD/YYYY-MM-DD.frag \
  --sc   YYYY-MM-DD/YYYY-MM-DD.scd \
  --duration 30
```

## 子 agent 每日流程

读 `references/pipeline.md` 了解完整环境要求和规则。子 agent 执行步骤：

1. **web_search** 今日日期 + 世界事件 / 节日 / 月相，定出主题（20字以内中文诗意短句）
2. **生成 GLSL**：写到 `YYYY-MM-DD/YYYY-MM-DD.frag`
   - `#version 330` + `uniform float u_time;` + `in vec2 v_uv;`，无注释
3. **生成 SC**：写到 `YYYY-MM-DD/YYYY-MM-DD.scd`
   - SynthDef 用 `d_recv` 格式（⚠️ 不能用 `.add`），无注释
   - 末尾：`score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5);`
4. **exec 运行** `daily_create.py`，等待完成（约 10 分钟）
5. **汇报**：主题 / mp4 路径 / Notion URL / run.log 摘要

## SC NRT 格式（必须）

```supercollider
score.add([0.0, ["/d_recv", SynthDef(\pm_name, {
    // synth body
}).asBytes]]);
```

`daily_create.py` 会自动检测 `.add` 并修复，但直接写对更保险。

## 脚本说明

- `scripts/daily_create.py`：主控脚本，含 fix_sc_nrt / render_audio / render_video / archive_notion / push_github，每步有 check()，失败发 Telegram 停止
- `scripts/pinkmoney_render.py`：GLSL headless 渲染，moderngl + PIL，分屏语法高亮，scroll 动画

## 详细参考

环境依赖、目录结构、.env 配置、性能数据 → `references/pipeline.md`
