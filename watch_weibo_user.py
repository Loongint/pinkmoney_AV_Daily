#!/usr/bin/env python3
"""
微博用户新帖监控 + 自动评论
用法: python3 watch_weibo_user.py --uid 3383556780
      python3 watch_weibo_user.py --uid 3383556780 --dry-run  # 只生成评论不发
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

# 龙龙的评论风格 prompt
COMMENT_SYSTEM = """你是龙龙（pink;money），深圳音视觉艺术家/livecoder，正在以本人身份给微博好友发评论。

你的风格：
- 简短有力，不废话，不用"哇""太棒了"这类空洞词
- 有自己的视角和感受，直接说
- 喜欢哲学/心理/创作议题，能聊就深聊一句
- 偶尔幽默，但不刻意
- 用中文，语气自然，像朋友圈回复而不是正式评论
- 10-50字，不超过两句
- 不@人，不加话题标签
"""

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


async def fetch_latest_posts(uid: str, count: int = 3) -> list[dict]:
    """抓取用户最新帖子，返回 [{id, url, text, time}]"""
    from playwright.async_api import async_playwright

    storage = json.loads(Path(SESSION_FILE).read_text())
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await ctx.new_page()

        url = f"https://weibo.com/u/{uid}"
        print(f"[Watch] 打开: {url}")
        await page.goto(url, timeout=30000)
        await asyncio.sleep(5)  # 等动态渲染

        # 用微博 API 抓帖子（更稳定）
        api_url = f"https://weibo.com/ajax/statuses/mymblog?uid={uid}&page=1&feature=0"
        print(f"[Watch] 调用 API: {api_url}")
        resp = await page.evaluate(f'''async () => {{
            const r = await fetch("{api_url}", {{credentials: "include"}});
            return r.json();
        }}''')

        statuses = resp.get("data", {}).get("list", [])
        for s in statuses[:count]:
            post_id  = str(s.get("id", ""))
            bid      = s.get("bid", "")
            raw_text = s.get("text_raw", s.get("text", ""))
            # 去掉 HTML 标签
            clean = re.sub(r"<[^>]+>", "", raw_text).strip()
            # 展开转发内容
            retweeted = s.get("retweeted_status")
            if retweeted:
                rt_text = re.sub(r"<[^>]+>", "", retweeted.get("text_raw", "")).strip()
                clean += f"\n[转发] {rt_text[:100]}"
            # 构造帖子 URL：优先用 bid，否则用 id 的 base62 转换
            if bid:
                post_url = f"https://weibo.com/{uid}/{bid}"
            else:
                post_url = f"https://weibo.com/{uid}/detail/{post_id}"
            results.append({
                "id":   post_id,
                "url":  post_url,
                "text": clean[:300],
                "time": s.get("created_at", ""),
            })

        await browser.close()
    return results


def generate_comment(post_text: str) -> str:
    """调用 LLM 生成评论"""
    import urllib.request
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 100,
        "system": COMMENT_SYSTEM,
        "messages": [{"role": "user", "content": f"这条微博内容是：\n\n{post_text}\n\n帮我写一条评论。"}]
    }).encode()

    req = urllib.request.Request(
        "https://api.gpt.ge/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": VAPI_API_KEY,
            "anthropic-version": "2023-06-01",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        return data["content"][0]["text"].strip()
    except Exception as e:
        print(f"[Watch] LLM 失败: {e}，使用默认评论")
        return "👀"


async def post_comment(post_url: str, comment_text: str) -> bool:
    """给指定帖子发评论"""
    from playwright.async_api import async_playwright

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

        print(f"[Watch] 打开帖子: {post_url}")
        await page.goto(post_url, timeout=30000)
        await asyncio.sleep(3)

        if "login" in page.url:
            print("[Watch] ERROR: 未登录")
            await browser.close()
            return False

        # 找评论输入框
        input_el = None
        for sel in ["textarea[placeholder*='评论']", "div[contenteditable='true']", "textarea"]:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el:
                    input_el = el
                    break
            except Exception:
                continue

        if not input_el:
            # 先点"评论"展开
            try:
                await page.click("button:has-text('评论')", timeout=3000)
                await asyncio.sleep(1)
                for sel in ["textarea[placeholder*='评论']", "textarea"]:
                    try:
                        el = await page.wait_for_selector(sel, timeout=3000)
                        if el:
                            input_el = el
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if not input_el:
            print("[Watch] ERROR: 找不到评论输入框")
            await browser.close()
            return False

        await input_el.click()
        await asyncio.sleep(0.3)
        await page.keyboard.insert_text(comment_text)
        await asyncio.sleep(0.5)

        # 提交
        for sel in ["button:has-text('发表')", "button:has-text('评论')"]:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    print(f"[Watch] ✅ 评论已发送")
                    await asyncio.sleep(2)
                    await browser.close()
                    return True
            except Exception:
                continue

        await page.keyboard.press("Control+Enter")
        await asyncio.sleep(2)
        await browser.close()
        return True


async def main_async(uid: str, dry_run: bool = False):
    state   = load_state()
    key     = f"uid_{uid}"
    seen    = set(state.get(key, {}).get("seen_ids", []))
    last_ts = state.get(key, {}).get("last_check", "")

    print(f"[Watch] 检测用户 {uid}，已知帖子数: {len(seen)}")
    posts = await fetch_latest_posts(uid)

    if not posts:
        print("[Watch] 未获取到帖子")
        return

    new_posts = [p for p in posts if p["id"] not in seen]
    print(f"[Watch] 新帖子: {len(new_posts)} 条")

    for post in new_posts:
        print(f"\n[Watch] 新帖: {post['url']}")
        print(f"  内容: {post['text'][:100]}...")

        comment_text = generate_comment(post["text"])
        print(f"  生成评论: {comment_text}")

        if not dry_run:
            ok = await post_comment(post["url"], comment_text)
            status = "✅ 已发送" if ok else "❌ 失败"
        else:
            status = "🔍 dry-run，未发送"
        print(f"  {status}")

        # 记录已处理
        seen.add(post["id"])

    # 更新 state
    state[key] = {
        "seen_ids":   list(seen),
        "last_check": datetime.now().isoformat(),
        "uid":        uid,
    }
    save_state(state)
    print(f"\n[Watch] 完成，state 已保存")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uid",     required=True, help="微博 UID（数字）")
    parser.add_argument("--dry-run", action="store_true", help="只生成评论，不发送")
    args = parser.parse_args()

    if not Path(SESSION_FILE).exists():
        print(f"ERROR: {SESSION_FILE} 不存在")
        sys.exit(1)

    asyncio.run(main_async(args.uid, args.dry_run))


if __name__ == "__main__":
    main()
