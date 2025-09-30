Ubuntu 部署指南（systemd + Nginx，无 Docker）
===============================================

本文档介绍如何在一台干净的 Ubuntu 20.04/22.04 服务器上部署 tiger-webhook 服务，不依赖 Docker，使用 `systemd` 管理进程，以 Nginx 作为反向代理。

前置条件
--------

- 具备 sudo 权限的 Ubuntu 服务器
- 已解析好的域名（如需通过 HTTPS 暴露服务）
- 访问 Git 仓库的权限

1. 系统准备
-------------

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git python3.11 python3.11-venv python3.11-dev nginx
```

> 若系统默认没有 python3.11，可使用 `ppa:deadsnakes/ppa` 安装：
>
> ```bash
> sudo add-apt-repository ppa:deadsnakes/ppa -y
> sudo apt update
> sudo apt install -y python3.11 python3.11-venv python3.11-dev
> ```

2. 拉取代码
-----------

```bash
sudo mkdir -p /opt/tiger-webhook
sudo chown "$USER":"$USER" /opt/tiger-webhook
cd /opt/tiger-webhook
git clone https://<your-git-server>/tiger-webhook.git .
```

3. 创建虚拟环境并安装依赖
----------------------------

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install tigeropen structlog  # requirements.txt 中未固定或可能缺失的依赖
```

4. 配置环境变量
---------------

```bash
cp .env.example .env
vi .env  # 根据实际情况修改 API Key、轮询间隔、日志配置等

# 示例：
# POSITION_POLLING_INTERVAL_MINUTES=2
# ORDER_POLLING_INTERVAL_MINUTES=2
# LOG_LEVEL=INFO
# LOG_FORMAT=json
```

建议将敏感信息保存在 `/opt/tiger-webhook/.env`，并确保仅部署用户可读：

```bash
chmod 600 /opt/tiger-webhook/.env
```

5. 手动验证
-----------

```bash
source /opt/tiger-webhook/venv/bin/activate
python start_server.py
```

浏览器打开 `http://服务器IP:3001/health` 验证是否返回 `"status": "ok"`。确认成功后按 `Ctrl+C` 停止服务。

6. 配置 systemd 服务
---------------------

创建 `/etc/systemd/system/tiger-webhook.service`：

```ini
[Unit]
Description=Tiger Webhook Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/tiger-webhook
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/tiger-webhook/.env
ExecStart=/opt/tiger-webhook/venv/bin/python /opt/tiger-webhook/start_server.py
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

> 如果 `.env` 中的变量名称与程序读取的环境变量一致，`EnvironmentFile` 会自动导入。若 `.env` 使用 Pydantic 加载也可直接引用；若需额外变量，可在此文件中补充。

生效并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tiger-webhook.service
sudo systemctl status tiger-webhook.service
```

日志查看：

```bash
journalctl -u tiger-webhook.service -f
```

7. 配置 Nginx 反向代理
----------------------

创建 `/etc/nginx/sites-available/tiger-webhook`：

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点并测试配置：

```bash
sudo ln -s /etc/nginx/sites-available/tiger-webhook /etc/nginx/sites-enabled/tiger-webhook
sudo nginx -t
sudo systemctl reload nginx
```

7.1 启用 HTTPS（可选）
-----------------------

可使用 Let’s Encrypt 自动签发证书：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

certbot 会更新 Nginx 配置，并设置自动续签（systemd timer 默认启用）。可通过 `sudo certbot renew --dry-run` 验证续期流程。

8. 目录与权限建议
-----------------

- 代码目录：`/opt/tiger-webhook`
- 虚拟环境：`/opt/tiger-webhook/venv`
- 日志目录（默认）：`/opt/tiger-webhook/logs`
- 日志文件可使用内置滚动（`LOG_MAX_SIZE`, `LOG_BACKUP_COUNT`），如需系统级 logrotate，可编写 `/etc/logrotate.d/tiger-webhook`

示例 logrotate 配置：

```conf
/opt/tiger-webhook/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}
```

9. 常见问题
-----------

1. **`ModuleNotFoundError: No module named 'deribit_webhook'`**
   - 确认 systemd 服务中 `WorkingDirectory` 与 `ExecStart` 使用的路径正确。
2. **`allow_population_by_field_name` 警告**
   - Pydantic v2 的提醒，可忽略或在 settings 配置中使用 `populate_by_name`。
3. **轮询间隔未生效**
   - 调整 `.env` 后需重启服务，`settings` 在进程启动时只加载一次。
4. **TigerOpen 依赖缺失**
   - 确保 `pip install tigeropen` 已执行，并存在相应证书文件。

10. 更新流程
-------------

```bash
cd /opt/tiger-webhook
sudo systemctl stop tiger-webhook.service
git pull
source venv/bin/activate
pip install -r requirements.txt
pip install tigeropen structlog
sudo systemctl start tiger-webhook.service
```

如有数据库迁移或配置变更，按项目文档执行。

附录：手工运行 main.py
------------------------

若需使用原始 `main.py`（内含启动/关闭轮询的逻辑），可执行：

```bash
source /opt/tiger-webhook/venv/bin/activate
PYTHONPATH=src python -m deribit_webhook.main
```

此方法不依赖 systemd，适用于调试环境。线上建议保持 systemd 管理以便监控与自动重启。

