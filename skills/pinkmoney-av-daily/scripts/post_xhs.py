#!/usr/bin/env python3
"""
小红书视频发布脚本 — Playwright headless
用法: python3 post_xhs.py --video path/to/video.mp4 --title "标题" --text "描述"
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

SESSION_FILE = os.environ.get("XHS_SESSION_FILE", "/mnt/c/Users/PC/xhs_session.json")
PROXY        = "http://172.27.32.1:7890"

async def post_video(video_path: str, title: str, text: str, screenshot_dir: str = "/tmp"):
    from playwright.async_api import async_playwright

    abs_video = str(Path(video_path).resolve())
    print(f"[XHS] 准备上传: {abs_video}")

    if not Path(SESSION_FILE).exists():
        print(f"[XHS] ERROR: session 文件不存在: {SESSION_FILE}")
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
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = await ctx.new_page()

        print("[XHS] 打开创作者发布页...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=video", timeout=30000)
        await asyncio.sleep(3)

        if "login" in page.url:
            print("[XHS] ERROR: 未登录，session 可能已过期")
            await browser.close()
            return ""

        await page.screenshot(path=f"{screenshot_dir}/xhs_open.png")
        print(f"[XHS] 当前 URL: {page.url}")

        # STEP 1: 点"上传视频"tab（如果有）
        tab = await page.query_selector("text=上传视频")
        if tab:
            await tab.click()
            await asyncio.sleep(1)

        # STEP 2: 直接 set_input_files 到 input[type=file].upload-input
        print("[XHS] 上传视频...")
        file_input = await page.query_selector("input[type=file].upload-input, input[type=file]")
        if not file_input:
            print("[XHS] ERROR: 找不到 file input")
            await browser.close()
            return ""
        await file_input.set_input_files(abs_video)
        print("[XHS] 文件已注入，等待上传...")

        # STEP 3: 等待上传完成（标题框出现 or 进度消失）
        upload_done = False
        for i in range(120):
            await asyncio.sleep(3)
            title_visible = await page.evaluate(r'''() => {
                const el = document.querySelector(
                    "input[placeholder*='\u6807\u9898'], textarea[placeholder*='\u6807\u9898'], "
                    + "input[class*='title'], .title-input input"
                );
                return el ? el.offsetParent !== null : false;
            }''')
            if title_visible:
                upload_done = True
                print(f"[XHS] ✅ 上传完成（{(i+1)*3}s）")
                break
            if i % 5 == 0 and i > 0:
                print(f"[XHS]   等待上传... {(i+1)*3}s")

        if not upload_done:
            await page.screenshot(path=f"{screenshot_dir}/xhs_timeout.png")
            print("[XHS] WARNING: 上传超时，尝试继续...")

        await page.screenshot(path=f"{screenshot_dir}/xhs_uploaded.png")

        # STEP 4: 填写标题（fill 可靠）
        print(f"[XHS] 填写标题: {title}...")
        await page.fill("input[placeholder='填写标题会有更多赞哦']", title)
        await asyncio.sleep(0.5)

        # STEP 5: 填写描述（ProseMirror，keyboard.insertText 支持中文，Enter 换行）
        print("[XHS] 填写描述...")
        desc_el = await page.query_selector("div.tiptap.ProseMirror, div.ProseMirror")
        if desc_el:
            await desc_el.click()
            await asyncio.sleep(0.2)
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if line:
                    await page.keyboard.insert_text(line)
                if i < len(lines) - 1:
                    await page.keyboard.press("Enter")
        await asyncio.sleep(0.5)

        await page.screenshot(path=f"{screenshot_dir}/xhs_filled.png")
        print(f"[XHS] 截图: {screenshot_dir}/xhs_filled.png")

        # STEP 6: 等待视频处理完成（发布按钮从 disabled 变为可用）
        print("[XHS] 等待视频处理完成...")
        for i in range(60):
            await asyncio.sleep(3)
            btn_class = await page.evaluate("""() => {
                const b = [...document.querySelectorAll("button")].find(b => b.textContent.trim() === "发布");
                return b ? b.className : "";
            }""")
            if btn_class and "disabled" not in btn_class:
                print(f"[XHS] ✅ 视频处理完成（{(i+1)*3}s），发布按钮可用")
                break
            if i % 5 == 0 and i > 0:
                print(f"[XHS]   处理中... {(i+1)*3}s")

        # STEP 7: 点发布
        print("[XHS] 点击发布按钮...")
        await page.click("button:has-text('发布')")

        await asyncio.sleep(5)
        await page.screenshot(path=f"{screenshot_dir}/xhs_done.png")
        print(f"[XHS] 截图: {screenshot_dir}/xhs_done.png")
        print(f"[XHS] 发布后 URL: {page.url}")

        await browser.close()
        return page.url

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--text",  required=True)
    parser.add_argument("--screenshot-dir", default="/tmp")
    args = parser.parse_args()

    if not Path(SESSION_FILE).exists():
        print(f"ERROR: {SESSION_FILE} 不存在")
        sys.exit(1)

    url = asyncio.run(post_video(args.video, args.title, args.text, args.screenshot_dir))
    print("result:", url)

if __name__ == "__main__":
    main()
