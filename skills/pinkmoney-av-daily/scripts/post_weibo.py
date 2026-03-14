#!/usr/bin/env python3
"""
微博视频发布脚本 — Playwright headless (upload/channel 页面)
用法: python3 post_weibo.py --video path/to/video.mp4 --title "标题" --text "描述"
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

async def post_video(video_path: str, title: str, text: str, screenshot_dir: str = "/tmp"):
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
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        print("[Weibo] 打开上传页面...")
        await page.goto("https://weibo.com/upload/channel", timeout=30000)
        await asyncio.sleep(3)

        if "login" in page.url:
            print("[Weibo] ERROR: 未登录")
            await browser.close()
            return ""

        await page.screenshot(path=f"{screenshot_dir}/weibo_ch_open.png")

        # STEP 1: 点"上传视频"按钮，触发 file chooser，注入文件
        print("[Weibo] 点击上传视频按钮...")
        async with page.expect_file_chooser(timeout=15000) as fc_info:
            await page.click("button:has-text('上传视频')")
        fc = await fc_info.value
        await fc.set_files(abs_video)
        print("[Weibo] 文件已注入，开始上传...")

        # STEP 2: 立即点"原创" radio（不需要等上传完）
        # 用 JS 直接点，因为元素此时可能还是隐藏的
        await asyncio.sleep(1)
        print("[Weibo] 点击原创 radio...")
        await page.evaluate(r'''() => {
            const labels = [...document.querySelectorAll("label")];
            const orig = labels.find(l => l.textContent.includes("\u539f\u521b"));
            if (orig) {
                const radio = orig.querySelector("input[type=radio]");
                if (radio) { radio.click(); radio.checked = true; radio.dispatchEvent(new Event("change", {bubbles:true})); }
                orig.click();
            }
        }''')
        await asyncio.sleep(1)
        await page.screenshot(path=f"{screenshot_dir}/weibo_ch_uploading.png")
        print("[Weibo] 等待上传完成（按钮变为发布）...")

        # STEP 3: 等待"发布"按钮出现（上传完成的信号）
        publish_ready = False
        for i in range(120):  # 最多 6 分钟
            await asyncio.sleep(3)
            btn_texts = await page.evaluate(r'''() => {
                return [...document.querySelectorAll("button")]
                    .filter(b => b.offsetParent !== null)
                    .map(b => b.textContent.trim());
            }''')
            if "发布" in btn_texts:
                publish_ready = True
                print(f"[Weibo] ✅ 发布按钮出现（{(i+1)*3}s），上传完成")
                break
            if i % 5 == 0 and i > 0:
                print(f"[Weibo]   等待... {(i+1)*3}s | 可见按钮: {btn_texts}")

        if not publish_ready:
            await page.screenshot(path=f"{screenshot_dir}/weibo_ch_timeout.png")
            print("[Weibo] WARNING: 超时未见发布按钮，尝试继续...")

        await page.screenshot(path=f"{screenshot_dir}/weibo_ch_uploaded.png")

        # STEP 4: 填写标题（JS + React 事件）
        print(f"[Weibo] 填写标题: {title[:20]}...")
        await page.evaluate(r'''([t]) => {
            const el = document.querySelector("input[placeholder*='\u6807\u9898']");
            if (!el) return;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(el, t);
            el.dispatchEvent(new Event("input", {bubbles:true}));
            el.dispatchEvent(new Event("change", {bubbles:true}));
        }''', [title[:30]])
        await asyncio.sleep(0.5)

        # STEP 5: 填写描述
        print("[Weibo] 填写描述...")
        await page.evaluate(r'''([t]) => {
            const el = document.querySelector("textarea");
            if (!el) return;
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeSetter.call(el, t);
            el.dispatchEvent(new Event("input", {bubbles:true}));
            el.dispatchEvent(new Event("change", {bubbles:true}));
        }''', [text])
        await asyncio.sleep(0.5)

        await page.screenshot(path=f"{screenshot_dir}/weibo_ch_filled.png")
        print(f"[Weibo] 截图: {screenshot_dir}/weibo_ch_filled.png")

        # STEP 6: 点"发布"按钮
        print("[Weibo] 点击发布按钮...")
        await page.click("button:has-text('发布')")
        await asyncio.sleep(3)

        # STEP 7: 等待结果，处理真正的确认弹窗（排除"再发一条视频"）
        await asyncio.sleep(3)
        await page.screenshot(path=f"{screenshot_dir}/weibo_ch_done.png")
        print(f"[Weibo] 截图: {screenshot_dir}/weibo_ch_done.png")

        # 检查"再发一条视频"是否可见 = 发布成功
        again_visible = await page.evaluate(r'''() => {
            const b = [...document.querySelectorAll("button")].find(b => b.textContent.includes("\u518d\u53d1\u4e00\u6761\u89c6\u9891"));
            return b ? b.offsetParent !== null : false;
        }''')
        if again_visible:
            print("[Weibo] \u2705 \u53d1\u5e03\u6210\u529f\uff01")
            await browser.close()
            return "https://weibo.com/upload/channel#done"

        # 处理其他确认弹窗（不含"再发一条视频"）
        for _ in range(5):
            popup_btns = await page.evaluate(r'''() => {
                return [...document.querySelectorAll("button")]
                    .filter(b => b.offsetParent !== null)
                    .map(b => b.textContent.trim())
                    .filter(t => t.length > 0
                        && t !== "发布"
                        && t !== "上传视频"
                        && t !== "再发一条视频");
            }''')
            if popup_btns:
                print(f"[Weibo] 弹窗: {popup_btns}，点第一个...")
                await page.click(f"button:has-text('{popup_btns[0]}')")
                await asyncio.sleep(2)
                # 再检查一次是否成功
                again = await page.evaluate(r'''() => {
                    const b = [...document.querySelectorAll("button")].find(b => b.textContent.includes("\u518d\u53d1\u4e00\u6761\u89c6\u9891"));
                    return b ? b.offsetParent !== null : false;
                }''')
                if again:
                    print("[Weibo] \u2705 \u53d1\u5e03\u6210\u529f\uff01")
                    await browser.close()
                    return "https://weibo.com/upload/channel#done"
            await asyncio.sleep(1)

        print(f"[Weibo] URL: {page.url}")

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
