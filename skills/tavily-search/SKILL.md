---
name: tavily-search
description: 用 Tavily API 搜索网络实时信息。使用场景：需要今日新闻、历史上的今天、月相/天文、最新事件、实时数据等任何需要网络搜索的情况。TAVILY_API_KEY 需在环境变量中设置（存于 .env）。脚本路径：skills/tavily-search/scripts/tavily_search.py。
---

# Tavily Search

## 快速用法

```bash
source .env
python3 skills/tavily-search/scripts/tavily_search.py "查询内容" [--topic news] [--time_range day]
```

返回 JSON，关键字段：
- `answer`：LLM 生成的摘要答案（最有用）
- `results[].title` / `.url` / `.content`：原始结果列表

## 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--topic` | `general` | `general` / `news` / `finance` |
| `--time_range` | `day` | `day` / `week` / `month` / `year` |
| `--max` | `5` | 最多返回几条结果（1-20）|
| `--no-answer` | 关闭 | 不要 LLM 摘要（省 API 费）|

## 在 Python 脚本中调用

```python
import sys, os
sys.path.insert(0, "skills/tavily-search/scripts")
from tavily_search import search

r = search("March 15 moon phase 2026", time_range="day")
print(r["answer"])
```

## 典型搜索模式（theme 生成用）

```bash
# 今日新闻
python3 skills/tavily-search/scripts/tavily_search.py \
  "$(date +%Y-%m-%d) world news today" --topic news --time_range day --max 5

# 历史上的今天 + 节日
python3 skills/tavily-search/scripts/tavily_search.py \
  "March $(date +%d) anniversary holiday history today"

# 月相
python3 skills/tavily-search/scripts/tavily_search.py \
  "moon phase today $(date +%Y-%m-%d)"
```

## 环境变量

`TAVILY_API_KEY` — tvly-dev-xxx 格式，存于工作区 `.env`，免费额度每月 1000 次。
