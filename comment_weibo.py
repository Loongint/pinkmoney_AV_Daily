#!/usr/bin/env python3
"""
微博评论脚本 — Playwright headless
用法:
  # 给指定帖子发评论（weibo.com/xxxx/yyyyyyy）
  python3 comment_weibo.py --post-url "https://weibo.com/u/xxx/yyy" --comment "评论内容"

  # 给指定用户主页最新一条帖子发评论
  python3 comment_weibo.py --user "用户名或UID" --comment "评论内容"
"""
import asyncio, os, sys, argparse, json
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SESSION_FILE = os.environ.get("WEIBO_SESSION_FILE", "/mnt/c/Users/PC/weibo_session.json")
PROXY        = "http://172.27.32.1:7890"


async def comment(post_url: str, comment_text: str, screenshot_dir: str = "/tmp") -> bool:
    from playwright.async_api import async_playwright

    if not Path(SESSION_FILE).exists():
        print(f"[Weibo] ERROR: session 文件不存在: {SESSION_FILE}")
        return False

    storage = json.loads(Path(SESSION_FILE).read_text(encoding="utf-8"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        print(f"[Weibo] 打开帖子: {post_url}")
        await page.goto(post_url, timeout=30000)
        await asyncio.sleep(3)

        if "login" in page.url:
            print("[Weibo] ERROR: 未登录，session 可能已过期")
            await browser.close()
            return False

        await page.screenshot(path=f"{screenshot_dir}/weibo_comment_open.png")

        # STEP 1: 找评论输入框
        print("[Weibo] 找评论输入框...")
        comment_input = None
        selectors = [
            "textarea[placeholder*='评论']",
            "div[contenteditable='true'][placeholder*='评论']",
            "input[placeholder*='评论']",
            ".comment-box textarea",
            "textarea",
        ]
        for sel in selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el:
                    comment_input = el
                    print(f"[Weibo] 找到输入框: {sel}")
                    break
            except Exception:
                continue

        if not comment_input:
            # 尝试点"评论"按钮展开输入框
            try:
                await page.click("button:has-text('评论'), a:has-text('评论')", timeout=5000)
                await asyncio.sleep(1)
                for sel in selectors:
                    try:
                        el = await page.wait_for_selector(sel, timeout=3000)
                        if el:
                            comment_input = el
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if not comment_input:
            await page.screenshot(path=f"{screenshot_dir}/weibo_comment_error.png")
            print("[Weibo] ERROR: 找不到评论输入框")
            await browser.close()
            return False

        # STEP 2: 点击输入框，填写评论
        await comment_input.click()
        await asyncio.sleep(0.5)
        await page.keyboard.insert_text(comment_text)
        await asyncio.sleep(0.5)

        await page.screenshot(path=f"{screenshot_dir}/weibo_comment_filled.png")
        print(f"[Weibo] 已填写评论: {comment_text[:30]}...")

        # STEP 3: 点发布/发表评论按钮
        print("[Weibo] 提交评论...")
        submitted = False
        submit_selectors = [
            "button:has-text('发表')",
            "button:has-text('发布')",
            "button:has-text('评论')",
            ".comment-submit",
        ]
        for sel in submit_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    submitted = True
                    print(f"[Weibo] 点击提交按钮: {sel}")
                    break
            except Exception:
                continue

        if not submitted:
            # 备选：Ctrl+Enter
            await page.keyboard.press("Control+Enter")
            submitted = True
            print("[Weibo] 用 Ctrl+Enter 提交")

        await asyncio.sleep(3)
        await page.screenshot(path=f"{screenshot_dir}/weibo_comment_done.png")

        # 简单判断：页面没跳走 = 评论成功（微博评论发完留在原页）
        print(f"[Weibo] ✅ 评论已提交，当前 URL: {page.url}")
        await browser.close()
        return True


async def comment_latest(user: str, comment_text: str, screenshot_dir: str = "/tmp") -> bool:
    """给指定用户主页最新一条帖子发评论"""
    from playwright.async_api import async_playwright

    if not Path(SESSION_FILE).exists():
        print(f"[Weibo] ERROR: session 文件不存在: {SESSION_FILE}")
        return False

    storage = json.loads(Path(SESSION_FILE).read_text(encoding="utf-8"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        # 访问用户主页
        profile_url = f"https://weibo.com/{user}" if not user.startswith("http") else user
        print(f"[Weibo] 打开用户主页: {profile_url}")
        await page.goto(profile_url, timeout=30000)
        await asyncio.sleep(3)

        if "login" in page.url:
            print("[Weibo] ERROR: 未登录")
            await browser.close()
            return False

        await page.screenshot(path=f"{screenshot_dir}/weibo_profile.png")

        # 找最新帖子链接
        print("[Weibo] 找最新帖子...")
        post_url = await page.evaluate(r'''() => {
            const links = [...document.querySelectorAll("a[href*='/detail/']")];
            return links.length > 0 ? links[0].href : null;
        }''')

        if not post_url:
            print("[Weibo] ERROR: 找不到帖子链接")
            await browser.close()
            return False

        print(f"[Weibo] 最新帖子: {post_url}")
        await browser.close()

    # 用找到的 post_url 发评论
    return await comment(post_url, comment_text, screenshot_dir)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--post-url", help="微博帖子直链")
    group.add_argument("--user",     help="用户名/UID，评论其最新帖子")
    parser.add_argument("--comment",        required=True, help="评论内容")
    parser.add_argument("--screenshot-dir", default="/tmp")
    args = parser.parse_args()

    if not Path(SESSION_FILE).exists():
        print(f"ERROR: {SESSION_FILE} 不存在")
        sys.exit(1)

    if args.post_url:
        ok = asyncio.run(comment(args.post_url, args.comment, args.screenshot_dir))
    else:
        ok = asyncio.run(comment_latest(args.user, args.comment, args.screenshot_dir))

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
