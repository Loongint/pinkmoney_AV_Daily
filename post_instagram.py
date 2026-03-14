#!/usr/bin/env python3
"""
Instagram Reels 发布脚本 — Playwright headless
用法: python3 post_instagram.py --video path/to/video.mp4 --caption "描述"

Session 抓取（首次）：
  playwright codegen --save-storage=/mnt/c/Users/PC/instagram_session.json https://www.instagram.com
  登录后关闭浏览器，session 自动保存。
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

SESSION_FILE = os.environ.get("INSTAGRAM_SESSION_FILE", "/mnt/c/Users/PC/instagram_session.json")
PROXY        = "http://172.27.32.1:7890"

async def post_reel(video_path: str, caption: str, screenshot_dir: str = "/tmp") -> str:
    from playwright.async_api import async_playwright

    abs_video = str(Path(video_path).resolve())
    print(f"[INS] 准备上传: {abs_video}")

    if not Path(SESSION_FILE).exists():
        print(f"[INS] ERROR: session 文件不存在: {SESSION_FILE}")
        print(f"[INS] 请先运行: playwright codegen --save-storage={SESSION_FILE} https://www.instagram.com")
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
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()

        print("[INS] 打开 Instagram 创作页...")
        await page.goto("https://www.instagram.com/", timeout=30000)
        await asyncio.sleep(3)

        if "accounts/login" in page.url:
            print("[INS] ERROR: 未登录，session 可能已过期")
            await browser.close()
            return ""

        await page.screenshot(path=f"{screenshot_dir}/ins_open.png")
        print(f"[INS] 当前 URL: {page.url}")

        # STEP 1: 点「创建」按钮（铅笔/+图标）
        print("[INS] 点击创建按钮...")
        create_btn = await page.query_selector("svg[aria-label='新建帖子'], svg[aria-label='New post'], [aria-label*='Create'], [aria-label*='创建']")
        if create_btn:
            await create_btn.click()
        else:
            # 备选：找导航栏的创建入口
            await page.click("text=创建, text=Create", timeout=5000)
        await asyncio.sleep(2)

        # STEP 2: 点「Reels」选项
        print("[INS] 选择 Reels...")
        reels_btn = await page.query_selector("text=Reels, text=卷轴, button:has-text('Reels')")
        if reels_btn:
            await reels_btn.click()
            await asyncio.sleep(1)

        # STEP 3: 上传视频
        print("[INS] 上传视频...")
        file_input = await page.query_selector("input[type=file]")
        if not file_input:
            print("[INS] ERROR: 找不到 file input")
            await page.screenshot(path=f"{screenshot_dir}/ins_error.png")
            await browser.close()
            return ""
        await file_input.set_input_files(abs_video)
        print("[INS] 文件已注入，等待处理...")
        await asyncio.sleep(5)

        await page.screenshot(path=f"{screenshot_dir}/ins_uploaded.png")

        # STEP 4: 跳过裁剪/滤镜，点「下一步」直到到描述页
        for i in range(3):
            next_btn = await page.query_selector("button:has-text('下一步'), button:has-text('Next')")
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(2)
            else:
                break

        await page.screenshot(path=f"{screenshot_dir}/ins_caption.png")

        # STEP 5: 填写描述
        print("[INS] 填写描述...")
        caption_el = await page.query_selector("div[aria-label*='描述'], div[aria-label*='Caption'], div[contenteditable='true']")
        if caption_el:
            await caption_el.click()
            await asyncio.sleep(0.3)
            await page.keyboard.insert_text(caption)
        await asyncio.sleep(1)

        await page.screenshot(path=f"{screenshot_dir}/ins_filled.png")

        # STEP 6: 点发布
        print("[INS] 点击分享/发布...")
        share_btn = await page.query_selector("button:has-text('分享'), button:has-text('Share')")
        if share_btn:
            await share_btn.click()
        await asyncio.sleep(5)

        await page.screenshot(path=f"{screenshot_dir}/ins_done.png")
        final_url = page.url
        print(f"[INS] 发布后 URL: {final_url}")

        await browser.close()

        if "instagram.com" in final_url:
            print(f"[INS] ✅ 发布成功")
            print(f"result: {final_url}")
            return final_url
        return ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",          required=True)
    parser.add_argument("--caption",        required=True)
    parser.add_argument("--screenshot-dir", default="/tmp")
    args = parser.parse_args()

    if not Path(SESSION_FILE).exists():
        print(f"ERROR: {SESSION_FILE} 不存在")
        print(f"请先运行: playwright codegen --save-storage={SESSION_FILE} https://www.instagram.com")
        sys.exit(1)

    asyncio.run(post_reel(args.video, args.caption, args.screenshot_dir))

if __name__ == "__main__":
    main()
