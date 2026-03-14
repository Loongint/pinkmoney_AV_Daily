#!/usr/bin/env python3
"""
微博视频发布脚本 — Playwright headless
用法: python3 post_weibo.py --video path/to/video.mp4 --text "发布文字"
"""
import asyncio, os, sys, argparse, json
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SESSION_FILE = os.environ.get("WEIBO_SESSION_FILE", "/mnt/c/Users/PC/weibo_session.json")
PROXY        = "http://172.27.32.1:7890"

async def post_video(video_path: str, text: str):
    from playwright.async_api import async_playwright

    abs_video = str(Path(video_path).resolve())
    print(f"[Weibo] 准备上传: {abs_video}")

    if not Path(SESSION_FILE).exists():
        print(f"[Weibo] ERROR: session 文件不存在: {SESSION_FILE}")
        return ""

    storage = json.loads(Path(SESSION_FILE).read_text(encoding="utf-8"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            storage_state=storage,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        # 拦截 fileplatform init 响应拿 media_id
        media_id_holder = {}
        async def handle_resp(resp):
            if "fileplatform" in resp.url and "init" in resp.url:
                try:
                    d = await resp.json()
                    mid = d.get("media_id", "")
                    if mid:
                        media_id_holder["id"] = mid
                        print(f"[Weibo] media_id: {mid}")
                except:
                    pass
        page.on("response", handle_resp)

        print("[Weibo] 打开首页...")
        await page.goto("https://weibo.com/", timeout=30000)
        await asyncio.sleep(2)

        if "login" in page.url:
            print("[Weibo] ERROR: 未登录，session 可能已过期")
            await browser.close()
            return ""

        print("[Weibo] 上传视频...")
        file_input = page.locator("input[type=file]").first
        await file_input.set_input_files(abs_video)

        # 等待 media_id（最多 3 分钟）
        print("[Weibo] 等待上传完成...")
        for i in range(60):
            await asyncio.sleep(3)
            if media_id_holder.get("id"):
                await asyncio.sleep(5)  # 确保上传完成
                break
            if i % 5 == 0 and i > 0:
                print(f"[Weibo]   已等待 {(i+1)*3}s...")

        media_id = media_id_holder.get("id", "")
        if not media_id:
            print("[Weibo] WARNING: 未拿到 media_id，降级为纯文字发布")

        # 拿 XSRF token
        xsrf = await page.evaluate(
            '() => document.cookie.split(";").find(c=>c.includes("XSRF-TOKEN"))?.split("=")[1] || ""'
        )

        print("[Weibo] 发布...")
        result = await page.evaluate('''async ([xsrf, text, media_id]) => {
            const body = "content=" + encodeURIComponent(text)
                + "&visible=0"
                + (media_id ? "&media_id=" + encodeURIComponent(media_id) : "");
            const r = await fetch("https://weibo.com/ajax/statuses/update", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-XSRF-TOKEN": xsrf,
                    "Referer": "https://weibo.com/"
                },
                body: body
            });
            return await r.json();
        }''', [xsrf, text, media_id])

        mblogid = result.get("data", {}).get("mblogid", "")
        uid     = result.get("data", {}).get("user", {}).get("idstr", "")
        mid2    = result.get("data", {}).get("idstr", "")

        if mid2:
            url = f"https://weibo.com/{uid}/{mblogid}"
            print(f"[Weibo] ✅ 发布成功: {url}")
            await browser.close()
            return url
        else:
            print(f"[Weibo] ERROR: {json.dumps(result, ensure_ascii=False)[:200]}")
            await browser.close()
            return ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--text",  required=True)
    args = parser.parse_args()

    if not Path(SESSION_FILE).exists():
        print(f"ERROR: {SESSION_FILE} 不存在，请先在 Windows 侧运行 weibo_login.py")
        sys.exit(1)

    url = asyncio.run(post_video(args.video, args.text))
    print("result:", url)

if __name__ == "__main__":
    main()
