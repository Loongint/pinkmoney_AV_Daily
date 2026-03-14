#!/usr/bin/env python3
"""
定期刷新三平台 session，防止过期。
每次打开平台主页，刷新 cookie 活跃时间后重新保存。

用法: python3 refresh_sessions.py
cron: 每3天 06:50 AM
"""
import asyncio, os, json, sys
from pathlib import Path
from datetime import datetime

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

PROXY = "http://172.27.32.1:7890"
TG_BOT_TOKEN = "8627190890:AAG5jJ8WjlaFdVJnWbgAFzB98GUoi4mQQ04"
TG_CHAT_ID   = "5390091587"

SESSIONS = {
    "weibo":    {
        "file": "/mnt/c/Users/PC/weibo_session.json",
        "url":  "https://weibo.com",
        "check": "weibo.com/u/",  # URL 中出现这个说明已登录（跳转到主页）
    },
    "xhs": {
        "file": "/mnt/c/Users/PC/xhs_session.json",
        "url":  "https://creator.xiaohongshu.com",
        "check": "creator.xiaohongshu.com",
    },
}


def notify(text: str):
    import urllib.request
    try:
        payload = json.dumps({"chat_id": TG_CHAT_ID, "text": f"🔑 Session 刷新\n{text}"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


async def refresh_session(name: str, config: dict) -> bool:
    from playwright.async_api import async_playwright

    session_file = Path(config["file"])
    if not session_file.exists():
        print(f"[{name}] ❌ session 文件不存在: {session_file}")
        return False

    storage = json.loads(session_file.read_text())

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

        print(f"[{name}] 打开: {config['url']}")
        try:
            await page.goto(config["url"], timeout=30000)
            await asyncio.sleep(4)
        except Exception as e:
            print(f"[{name}] ❌ 打开失败: {e}")
            await browser.close()
            return False

        current_url = page.url
        print(f"[{name}] 当前 URL: {current_url}")

        # 检查是否登录
        if "login" in current_url or "signin" in current_url or "passport" in current_url:
            print(f"[{name}] ❌ session 已过期，需要重新登录")
            await browser.close()
            return False

        # 保存刷新后的 cookies
        new_storage = await ctx.storage_state()
        session_file.write_text(json.dumps(new_storage, ensure_ascii=False, indent=2))
        print(f"[{name}] ✅ session 已刷新并保存")

        await browser.close()
        return True


async def refresh_instagram() -> bool:
    """Instagram 用 instagrapi，每次调用自动刷新"""
    session_file = Path(__file__).parent / ".instagram_session.json"
    if not session_file.exists():
        print("[instagram] ❌ session 文件不存在")
        return False

    try:
        from instagrapi import Client
        cl = Client()
        cl.set_proxy(PROXY)
        cl.load_settings(str(session_file))
        cl.get_timeline_feed()  # 简单请求刷新活跃
        cl.dump_settings(str(session_file))
        print("[instagram] ✅ session 已刷新")
        return True
    except Exception as e:
        print(f"[instagram] ❌ 失败: {e}")
        return False


async def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[refresh] 开始刷新 session — {ts}")

    results = {}

    for name, config in SESSIONS.items():
        results[name] = await refresh_session(name, config)

    results["instagram"] = await refresh_instagram()

    # 汇总
    ok  = [k for k, v in results.items() if v]
    bad = [k for k, v in results.items() if not v]

    summary = f"{ts}\n"
    summary += f"✅ 正常: {', '.join(ok) if ok else '无'}\n"
    summary += f"❌ 过期: {', '.join(bad) if bad else '无'}"

    print(f"\n[refresh] {summary}")

    if bad:
        notify(f"⚠️ 以下 session 已过期，请重新登录：\n{', '.join(bad)}\n\n小红书/微博：在 Windows 运行\nplaywright codegen --save-storage=C:\\Users\\PC\\{bad[0]}_session.json https://...")
    else:
        print("[refresh] 全部正常，无需通知")


if __name__ == "__main__":
    asyncio.run(main())
