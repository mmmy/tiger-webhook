#!/usr/bin/env python3
"""
服务器启动脚本
解决Python模块路径问题
"""

import os
import sys
from pathlib import Path


def main():
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir / "src"

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)

    os.chdir(current_dir)

    print("🚀 Starting Deribit Webhook Service (deribit_webhook.main)...")
    print(f"📁 Working directory: {Path.cwd()}")
    print(f"🐍 PYTHONPATH: {env['PYTHONPATH']}")

    os.execle(
        sys.executable,
        sys.executable,
        "-m",
        "deribit_webhook.main",
        env
    )


if __name__ == "__main__":
    main()
