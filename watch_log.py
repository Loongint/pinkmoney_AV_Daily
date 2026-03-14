#!/usr/bin/env python3
"""
实时监控 run.log 并推送到 Telegram
用法: python3 watch_log.py [log_path]
默认监控今天的 run.log
"""
import os, sys, time, requests
from pathlib import Path
from datetime import datetime

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TG_BOT_TOKEN = "8627190890:AAG5jJ8WjlaFdVJnWbgAFzB98GUoi4mQQ04"
TG_CHAT_ID   = "5390091587"
DATE         = datetime.now().strftime("%Y-%m-%d")

log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
           Path(__file__).parent / DATE / "run.log"

def send(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": f"📡 pink;money log\n{text}"},
            timeout=10)
    except Exception as e:
        print(f"[watch] TG failed: {e}")

print(f"[watch] 监控: {log_path}")
send(f"▶️ 开始监控 {DATE}/run.log")

# 等 log 文件出现
while not log_path.exists():
    time.sleep(1)

pos = 0
buf = ""
last_send = time.time()

while True:
    log_path.stat()  # 确保文件还在
    with open(log_path, "r") as f:
        f.seek(pos)
        new = f.read()
        pos = f.tell()

    if new:
        buf += new
        # 按空行分块，每块是一个 step
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            block = block.strip()
            if block:
                print(f"[watch] → {block[:80]}")
                send(block[:400])
                time.sleep(0.3)  # 避免 TG 限速

    # 检测渲染进程是否结束
    import subprocess
    r = subprocess.run(["pgrep", "-f", "pinkmoney_render"], capture_output=True)
    if r.returncode != 0:
        # 渲染结束，再读一次剩余内容
        with open(log_path, "r") as f:
            f.seek(pos)
            remainder = f.read().strip()
        if remainder:
            send(remainder[:400])
        send("✅ 渲染进程结束，watch_log 退出")
        break

    time.sleep(2)
