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

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # 保持工作目录为项目根目录，以便相对路径 (如 ./logs) 正确解析
    os.chdir(current_dir)

    from deribit_webhook.main import cli_main

    print("🚀 Starting Deribit Webhook Service (main.py)...")
    print(f"📁 Working directory: {Path.cwd()}")
    print(f"🐍 Python path (prefix): {sys.path[:3]}")

    cli_main()


if __name__ == "__main__":
    main()
