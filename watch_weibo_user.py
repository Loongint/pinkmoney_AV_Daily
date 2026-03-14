#!/usr/bin/env python3
"""
微博双向互动监控
- 检测目标用户新帖 → 自动生成并发布评论
- 检测对方回复了我的评论但我未回复的 → 自动生成并发布回复

用法:
  python3 watch_weibo_user.py --uid 3383556780 --my-uid 8376189590
  python3 watch_weibo_user.py --uid 3383556780 --my-uid 8376189590 --dry-run
"""
import asyncio, os, sys, json, argparse, re
from pathlib import Path
from datetime import datetime

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SESSION_FILE = os.environ.get("WEIBO_SESSION_FILE", "/mnt/c/Users/PC/weibo_session.json")
PROXY        = "http://172.27.32.1:7890"
STATE_FILE   = Path(__file__).parent / "memory" / "weibo_watch.json"
VAPI_API_KEY = os.environ.get("VAPI_API_KEY", "")
LLM_URL      = "https://api.gpt.ge/v1/messages"

COMMENT_SYSTEM = """你是龙龙（pink;money），深圳音视觉艺术家/livecoder，正在以本人身份给微博好友发评论或回复。

风格：
- 幽默但不刻意，像随手一句让人笑出来的朋友
- 有自己视角，偶尔带哲学或创作感，但不说教
- 10-30字，一句话搞定
- 可以用自嘲、反转、意外角度切入
- 最多一个 emoji，不堆砌
- 不加话题标签，不@人
- 语气像发了条朋友圈神评论
"""

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def llm_generate(prompt: str) -> str:
    import urllib.request
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 80,
        "system": COMMENT_SYSTEM,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(LLM_URL, data=payload, headers={
        "Content-Type": "application/json",
        "x-api-key": VAPI_API_KEY,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["content"][0]["text"].strip()
    except Exception as e:
        print(f"[Watch] LLM 失败: {e}")
        return ""


async def weibo_api(page, url: str) -> dict:
    """通过 Playwright page 调微博 AJAX API"""
    result = await page.evaluate(f'''async () => {{
        const r = await fetch("{url}", {{credentials: "include"}});
        const t = await r.text();
        try {{ return JSON.parse(t); }} catch(e) {{ return {{error: t.slice(0, 100)}}; }}
    }}''')
    return result


async def fetch_latest_posts(page, uid: str, count: int = 5) -> list[dict]:
    """抓取目标用户最新帖子"""
    resp = await weibo_api(page, f"https://weibo.com/ajax/statuses/mymblog?uid={uid}&page=1&feature=0")
    statuses = resp.get("data", {}).get("list", [])
    results = []
    for s in statuses[:count]:
        post_id  = str(s.get("id", ""))
        bid      = s.get("bid", "")
        raw_text = s.get("text_raw", s.get("text", ""))
        clean    = re.sub(r"<[^>]+>", "", raw_text).strip()
        rt = s.get("retweeted_status")
        if rt:
            clean += "\n[转发] " + re.sub(r"<[^>]+>", "", rt.get("text_raw","")).strip()[:100]
        post_url = f"https://weibo.com/{uid}/{bid}" if bid else f"https://weibo.com/{uid}/detail/{post_id}"
        results.append({"id": post_id, "url": post_url, "text": clean[:300], "time": s.get("created_at","")})
    return results


async def fetch_pending_replies(page, my_uid: str, target_uid: str, state: dict) -> list[dict]:
    """
    抓取对方回复了我评论、但我尚未回复的条目。
    策略：遍历我对 target_uid 帖子的评论，找出被 target_uid 回复但我没有继续回复的。
    """
    replied_key = f"replied_{my_uid}_{target_uid}"
    already_replied = set(state.get(replied_key, []))
    pending = []

    # 抓"@我的评论"通知（mentions type=comment）
    resp = await weibo_api(page, "https://weibo.com/ajax/statuses/mentions?type=comment&page=1")
    statuses = resp.get("data", {}).get("statuses", [])

    for s in statuses:
        comment_id = str(s.get("id", ""))
        if comment_id in already_replied:
            continue

        # 判断是否来自 target_uid
        user = s.get("user", {})
        sender_uid = str(user.get("id", ""))
        if sender_uid != target_uid:
            continue

        raw_text = re.sub(r"<[^>]+>", "", s.get("text_raw", s.get("text",""))).strip()
        # 原评论 context
        reply_to = s.get("reply_comment", {}) or {}
        reply_to_text = re.sub(r"<[^>]+>", "", reply_to.get("text","")).strip()

        pending.append({
            "comment_id": comment_id,
            "text":       raw_text,
            "reply_to":   reply_to_text,
            "url":        f"https://weibo.com/{target_uid}/detail/{s.get('rootid','')}",
        })

    return pending


async def post_comment(page, post_id: str, comment_text: str, reply_id: str = "") -> bool:
    """用微博 AJAX API 发评论（不依赖 DOM）"""
    result = await page.evaluate(f'''async () => {{
        const xsrfMatch = document.cookie.match(/XSRF-TOKEN=([^;]+)/);
        if (!xsrfMatch) return {{error: "no XSRF-TOKEN"}};
        const xsrf = decodeURIComponent(xsrfMatch[1]);
        const formData = new FormData();
        formData.append("id", "{post_id}");
        formData.append("comment", {json.dumps(comment_text)});
        formData.append("mid", "{post_id}");
        formData.append("st", xsrf);
        {"formData.append('reply_id', '" + reply_id + "');" if reply_id else ""}
        const r = await fetch("https://weibo.com/ajax/comments/create", {{
            method: "POST",
            credentials: "include",
            headers: {{ "X-XSRF-TOKEN": xsrf }},
            body: formData
        }});
        const t = await r.text();
        try {{ return JSON.parse(t); }} catch(e) {{ return {{raw: t.slice(0,200)}}; }}
    }}''')
    if result.get("ok") == 1:
        return True
    print(f"[Watch] API 返回: {json.dumps(result, ensure_ascii=False)[:200]}")
    return False


async def main_async(target_uid: str, my_uid: str, dry_run: bool = False):
    from playwright.async_api import async_playwright

    state   = load_state()
    post_key   = f"posts_{target_uid}"
    reply_key  = f"replied_{my_uid}_{target_uid}"
    seen_posts = set(state.get(post_key, {}).get("seen_ids", []))
    already_replied = set(state.get(reply_key, []))

    results = {"new_comments": [], "new_replies": []}

    storage = json.loads(Path(SESSION_FILE).read_text())
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await ctx.new_page()

        # 先打开微博主页建立 session
        await page.goto("https://weibo.com", timeout=30000)
        await asyncio.sleep(3)

        # ── 1. 新帖监控 ──────────────────────────────────
        print(f"\n[Watch] ── 检测 {target_uid} 新帖（已知 {len(seen_posts)} 条）")
        posts = await fetch_latest_posts(page, target_uid)
        new_posts = [p for p in posts if p["id"] not in seen_posts]
        print(f"[Watch] 新帖: {len(new_posts)} 条")

        for post in new_posts:
            print(f"\n  帖子: {post['url']}")
            print(f"  内容: {post['text'][:80]}...")
            comment = llm_generate(f"这条微博：\n\n{post['text']}\n\n写一条幽默评论。")
            if not comment:
                continue
            print(f"  评论: {comment}")

            if not dry_run:
                ok = await post_comment(page, post["id"], comment)
                print(f"  {'✅ 已发' if ok else '❌ 失败'}")
                if ok:
                    results["new_comments"].append({"post": post["text"][:50], "comment": comment})
            else:
                print("  🔍 dry-run")
                results["new_comments"].append({"post": post["text"][:50], "comment": comment, "dry": True})

            seen_posts.add(post["id"])

        # ── 2. 回复监控 ──────────────────────────────────
        print(f"\n[Watch] ── 检测对方回复我的评论")
        pending = await fetch_pending_replies(page, my_uid, target_uid, state)
        print(f"[Watch] 待回复: {len(pending)} 条")

        for item in pending:
            print(f"\n  对方回复: {item['text'][:80]}")
            if item["reply_to"]:
                print(f"  (回复我的): {item['reply_to'][:60]}")
            reply = llm_generate(
                f"对方回复了你的评论：\n「{item['text']}」\n"
                + (f"你之前说的是：「{item['reply_to']}」\n" if item['reply_to'] else "")
                + "写一条幽默简短的回复。"
            )
            if not reply:
                continue
            print(f"  回复: {reply}")

            if not dry_run:
                # 用帖子 rootid 发回复
                ok = await post_comment(page, item["comment_id"], reply, reply_id=item["comment_id"])
                print(f"  {'✅ 已发' if ok else '❌ 失败'}")
                if ok:
                    already_replied.add(item["comment_id"])
                    results["new_replies"].append({"their_reply": item["text"][:50], "my_reply": reply})
            else:
                print("  🔍 dry-run")
                results["new_replies"].append({"their_reply": item["text"][:50], "my_reply": reply, "dry": True})

        await browser.close()

    # 更新 state
    state[post_key] = {
        "seen_ids":   list(seen_posts),
        "last_check": datetime.now().isoformat(),
    }
    state[reply_key] = list(already_replied)
    save_state(state)

    print(f"\n[Watch] 完成 — 新评论 {len(results['new_comments'])} 条，新回复 {len(results['new_replies'])} 条")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uid",    required=True, help="目标用户 UID")
    parser.add_argument("--my-uid", default="8376189590", help="我的 UID")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not Path(SESSION_FILE).exists():
        print(f"ERROR: {SESSION_FILE} 不存在")
        sys.exit(1)

    asyncio.run(main_async(args.uid, args.my_uid, args.dry_run))


if __name__ == "__main__":
    main()
