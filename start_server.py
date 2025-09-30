# start_server.py
from deribit_webhook.app import create_app

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Deribit Webhook Service...")
    print(f"📁 Working directory: {src_dir}")
    print(f"🐍 Python path: {sys.path[:3]}")

    uvicorn.run(
        create_app(),          # 直接传入实例
        host="0.0.0.0",
        port=3001,
        log_level="info",
    )
