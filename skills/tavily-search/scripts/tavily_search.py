#!/usr/bin/env python3
"""
tavily_search.py — Tavily Search CLI wrapper
Usage:
  python3 tavily_search.py "query" [--topic general|news] [--time_range day|week|month] [--max 5]
Returns JSON to stdout.
TAVILY_API_KEY must be set in environment.
"""
import os, sys, json, argparse
import urllib.request, urllib.error
from pathlib import Path

# 自动加载工作区 .env（支持直接运行和 import 两种场景）
def _load_env():
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        # 手动解析 .env
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

_load_env()

def search(query, topic="general", time_range="day", max_results=5, include_answer=True):
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        return {"error": "TAVILY_API_KEY not set", "answer": "", "results": []}
    payload = json.dumps({
        "query": query,
        "topic": topic,
        "time_range": time_range,
        "max_results": max_results,
        "include_answer": include_answer,
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}", "answer": "", "results": []}
    except Exception as e:
        return {"error": str(e), "answer": "", "results": []}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--topic", default="general", choices=["general", "news", "finance"])
    parser.add_argument("--time_range", default="day", choices=["day", "week", "month", "year"])
    parser.add_argument("--max", type=int, default=5, dest="max_results")
    parser.add_argument("--no-answer", action="store_true")
    args = parser.parse_args()
    result = search(args.query, args.topic, args.time_range, args.max_results,
                    include_answer=not args.no_answer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
