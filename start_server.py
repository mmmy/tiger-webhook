#!/usr/bin/env python3
"""
服务器启动脚本
解决Python模块路径问题
"""

import os
import sys
from pathlib import Path

# 添加src目录到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# 设置工作目录
os.chdir(src_dir)

# 导入并启动应用
if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Deribit Webhook Service...")
    print(f"📁 Working directory: {src_dir}")
    print(f"🐍 Python path: {sys.path[:3]}")

    # 启动uvicorn服务器
    uvicorn.run(
        "deribit_webhook.main:app",
        host="0.0.0.0",
        port=3001,
        workers=1,
        log_level="info"
    )