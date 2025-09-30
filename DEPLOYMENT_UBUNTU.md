# Deribit Options Trading Microservice - Ubuntu Server Deployment Guide

本指南介绍如何在Ubuntu服务器上部署Deribit期权交易微服务，不使用Docker。

## 系统要求

- Ubuntu 20.04 LTS 或更高版本
- Python 3.9 或更高版本
- **最低配置**：
  - CPU: 1 vCPU
  - RAM: 512MB
  - 存储: 5GB SSD
  - 网络: 1Mbps
- **推荐配置**：
  - CPU: 1-2 vCPU
  - RAM: 1GB
  - 存储: 10-20GB SSD
  - 网络: 5Mbps
- 稳定的网络连接

> **说明**：由于只有一个用户且访问量很少，可以使用低配置云服务器（如腾讯云轻量、阿里云ECS共享型、Vultr等，月费用约$5-10）

## 部署步骤

### 1. 更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 安装必要软件

```bash
# 安装Python和相关工具
sudo apt install python3 python3-pip python3-venv -y

# 安装系统依赖 (对于低配服务器可以选择性安装)
sudo apt install curl wget git -y

# 如果需要Nginx反向代理 (单用户可以直接使用应用服务器)
sudo apt install nginx -y

# 进程管理 (对于低配服务器推荐使用systemd而不是supervisor)
sudo apt install supervisor -y

# 安装PostgreSQL (可选，推荐使用SQLite以节省资源)
# sudo apt install postgresql postgresql-contrib -y
```

### 3. 创建应用用户

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash deribit
sudo usermod -aG sudo deribit

# 切换到应用用户
sudo su - deribit
```

### 4. 克隆代码

```bash
# 从Git仓库克隆代码 (替换为实际仓库地址)
git clone https://github.com/your-repo/tiger-webhook.git
cd tiger-webhook

# 或者上传代码包
# scp -r ./tiger-webhook deribit@your-server:/home/deribit/
```

### 5. 创建Python虚拟环境

```bash
cd /home/deribit/tiger-webhook

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip
```

### 6. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 如果requirements.txt有问题，可以手动安装核心依赖
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0 pydantic-settings==2.1.0 python-dotenv==1.0.0
pip install httpx==0.25.2 aiohttp==3.9.1
pip install aiosqlite==0.19.0 sqlalchemy[asyncio]==2.0.23
pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4
pip install PyYAML==6.0.1 python-dateutil==2.8.2
pip install structlog==23.2.0 apscheduler==3.10.4 websockets==12.0
pip install python-multipart==0.0.6 orjson==3.9.10

# 注意：decimal是Python内置模块，无需安装
# Tiger Brokers SDK (可选)
# pip install tigeropen>=2.0.0
```

### 7. 配置环境变量

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
nano .env
```

**重要配置项**:
```env
# 服务器配置
PORT=3001
HOST=0.0.0.0
LOG_LEVEL=INFO

# 环境设置
NODE_ENV=production
USE_MOCK_MODE=false
USE_TEST_ENVIRONMENT=false
AUTO_START_POLLING=true

# 数据库配置 (单用户推荐使用SQLite，节省资源)
DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db

# 安全设置
SECRET_KEY=your-super-secret-key-change-this-in-production

# API配置
API_KEY_FILE=./config/apikeys.yml

# 轮询配置 (单用户可以设置更长间隔减少服务器负载)
POSITION_POLLING_INTERVAL_MINUTES=5
ORDER_POLLING_INTERVAL_MINUTES=10
MAX_POLLING_ERRORS=5

# 日志配置 (低配服务器减少日志大小)
LOG_FORMAT=text
LOG_FILE=./logs/combined.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5

# 性能优化 (低配服务器设置)
UVICORN_WORKERS=1  # 单进程模式
```

### 8. 创建必要目录

```bash
# 创建日志目录
mkdir -p logs

# 创建数据目录
mkdir -p data

# 创建配置目录
mkdir -p config

# 设置权限
chmod 755 logs data config
```

### 9. 配置API密钥

```bash
# 创建API密钥文件
nano config/apikeys.yml
```

**API密钥文件格式**:
```yaml
accounts:
  - name: "main_account"
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    enabled: true
    testnet: false

  - name: "test_account"
    client_id: "your_test_client_id"
    client_secret: "your_test_client_secret"
    enabled: true
    testnet: true
```

### 10. 数据库配置

对于单用户低配服务器，推荐使用SQLite以节省资源：

```bash
# SQLite数据库已通过DATABASE_URL配置，无需额外设置
# 数据库文件将自动创建在 ./data/delta_records.db
```

如果确实需要使用PostgreSQL（不推荐低配服务器）：

```bash
# 切换到root用户
sudo su

# 安装PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# 以postgres用户登录
su - postgres

# 创建数据库和用户
createdb deribit_db
psql -c "CREATE USER deribit_user WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE deribit_db TO deribit_user;"
psql -c "ALTER USER deribit_user CREATEDB;"

# 退出到deribit用户
exit
exit

# 更新.env文件中的DATABASE_URL
DATABASE_URL=postgresql+asyncpg://deribit_user:your_password@localhost/deribit_db
```

### 11. 测试应用

```bash
# 确保在虚拟环境中
source /home/deribit/tiger-webhook/venv/bin/activate
cd /home/deribit/tiger-webhook

# 测试启动应用
python -m uvicorn src.deribit_webhook.main:app --host 0.0.0.0 --port 3001

# 在另一个终端测试API
curl http://localhost:3001/health
```

### 12. 进程管理配置

对于单用户低配服务器，推荐使用更轻量的systemd服务：

#### 方法一：使用systemd（推荐）

```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/deribit-webhook.service
```

**systemd服务配置**:
```ini
[Unit]
Description=Deribit Options Trading Webhook
After=network.target

[Service]
Type=simple
User=deribit
WorkingDirectory=/home/deribit/tiger-webhook
Environment=PATH=/home/deribit/tiger-webhook/venv/bin
ExecStart=/home/deribit/tiger-webhook/venv/bin/python -m uvicorn src.deribit_webhook.main:app --host 0.0.0.0 --port 3001 --workers 1
Restart=always
RestartSec=10

# 日志配置
StandardOutput=append:/home/deribit/tiger-webhook/logs/service.log
StandardError=append:/home/deribit/tiger-webhook/logs/service_error.log

# 资源限制 (低配服务器优化)
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start deribit-webhook

# 设置开机自启
sudo systemctl enable deribit-webhook

# 检查状态
sudo systemctl status deribit-webhook
```

#### 方法二：使用Supervisor（备选）

```bash
# 切换到root用户
sudo su

# 创建Supervisor配置文件
nano /etc/supervisor/conf.d/deribit-webhook.conf
```

**Supervisor配置**:
```ini
[program:deribit-webhook]
command=/home/deribit/tiger-webhook/venv/bin/python -m uvicorn src.deribit_webhook.main:app --host 0.0.0.0 --port 3001 --workers 1
directory=/home/deribit/tiger-webhook
user=deribit
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/deribit/tiger-webhook/logs/supervisor.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="/home/deribit/tiger-webhook/venv/bin"
```

```bash
# 重新加载Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start deribit-webhook

# 检查状态
sudo supervisorctl status
```

### 13. 网络配置 (可选)

对于单用户使用，可以选择以下两种方式：

#### 方式一：直接访问应用 (推荐，节省资源)

直接通过 `http://your-server-ip:3001` 访问应用，无需配置Nginx。

#### 方式二：配置Nginx反向代理

如果需要域名访问或HTTPS：

```bash
# 创建Nginx配置文件
sudo nano /etc/nginx/sites-available/deribit-webhook
```

**Nginx配置**:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为实际域名

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # 替换为实际域名

    # SSL证书配置 (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # 反向代理配置
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 日志配置
    access_log /var/log/nginx/deribit-webhook.access.log;
    error_log /var/log/nginx/deribit-webhook.error.log;
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/deribit-webhook /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 14. 配置SSL证书 (Let's Encrypt)

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 15. 配置防火墙

```bash
# 配置UFW防火墙
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable

# 检查状态
sudo ufw status
```

### 16. 配置日志轮转

```bash
# 创建logrotate配置
sudo nano /etc/logrotate.d/deribit-webhook
```

**Logrotate配置**:
```
/home/deribit/tiger-webhook/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 deribit deribit
    postrotate
        sudo supervisorctl restart deribit-webhook
    endscript
}
```

### 17. 配置监控和告警

#### 安装监控工具 (可选)

```bash
# 安装htop
sudo apt install htop -y

# 安装系统监控脚本
sudo nano /usr/local/bin/monitor-deribit.sh
```

**监控脚本**:
```bash
#!/bin/bash

# 检查服务状态
if ! supervisorctl status deribit-webhook | grep -q "RUNNING"; then
    echo "$(date): Deribit service is not running!" >> /var/log/deribit-monitor.log
    # 发送告警邮件或通知
fi

# 检查端口
if ! netstat -tuln | grep -q ":3001"; then
    echo "$(date): Port 3001 is not listening!" >> /var/log/deribit-monitor.log
fi

# 检查磁盘空间
DISK_USAGE=$(df /home/deribit | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$(date): Disk usage is ${DISK_USAGE}%!" >> /var/log/deribit-monitor.log
fi
```

```bash
# 设置执行权限
sudo chmod +x /usr/local/bin/monitor-deribit.sh

# 添加到crontab (每5分钟检查一次)
sudo crontab -e
# 添加：*/5 * * * * /usr/local/bin/monitor-deribit.sh
```

### 18. 备份配置

```bash
# 创建备份脚本
sudo nano /usr/local/bin/backup-deribit.sh
```

**备份脚本**:
```bash
#!/bin/bash

BACKUP_DIR="/backup/deribit"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/home/deribit/tiger-webhook"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份应用代码
tar -czf $BACKUP_DIR/app_$DATE.tar.gz -C $APP_DIR .

# 备份数据库 (如果使用PostgreSQL)
if command -v pg_dump &> /dev/null; then
    pg_dump deribit_db > $BACKUP_DIR/db_$DATE.sql
    gzip $BACKUP_DIR/db_$DATE.sql
fi

# 删除30天前的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "$(date): Backup completed" >> /var/log/deribit-backup.log
```

```bash
# 设置执行权限和定时备份
sudo chmod +x /usr/local/bin/backup-deribit.sh
sudo crontab -e
# 添加：0 2 * * * /usr/local/bin/backup-deribit.sh
```

## 服务管理

### 如果使用systemd (推荐)
```bash
# 启动服务
sudo systemctl start deribit-webhook

# 停止服务
sudo systemctl stop deribit-webhook

# 重启服务
sudo systemctl restart deribit-webhook

# 查看服务状态
sudo systemctl status deribit-webhook

# 查看实时日志
sudo journalctl -u deribit-webhook -f

# 查看应用日志
tail -f /home/deribit/tiger-webhook/logs/combined.log
```

### 如果使用Supervisor
```bash
# 启动服务
sudo supervisorctl start deribit-webhook

# 停止服务
sudo supervisorctl stop deribit-webhook

# 重启服务
sudo supervisorctl restart deribit-webhook

# 查看服务状态
sudo supervisorctl status deribit-webhook

# 查看实时日志
sudo supervisorctl tail -f deribit-webhook

# 查看应用日志
tail -f /home/deribit/tiger-webhook/logs/combined.log
```

## 故障排除

### 1. 服务无法启动
```bash
# 检查Supervisor状态
sudo supervisorctl status

# 查看详细错误信息
sudo supervisorctl tail deribit-webhook

# 检查端口占用
sudo netstat -tuln | grep 3001
```

### 2. 数据库连接问题
```bash
# 检查数据库状态
sudo systemctl status postgresql

# 测试数据库连接
psql -h localhost -U deribit_user -d deribit_db
```

### 3. 权限问题
```bash
# 检查文件权限
ls -la /home/deribit/tiger-webhook/

# 修复权限
sudo chown -R deribit:deribit /home/deribit/tiger-webhook/
sudo chmod -R 755 /home/deribit/tiger-webhook/
```

### 4. 网络问题
```bash
# 检查防火墙状态
sudo ufw status

# 检查Nginx配置
sudo nginx -t

# 查看Nginx日志
sudo tail -f /var/log/nginx/error.log
```

## 低配服务器优化建议

### 1. 系统资源优化
```bash
# 禁用不必要的服务
sudo systemctl disable bluetooth
sudo systemctl disable cups
sudo systemctl disable avahi-daemon

# 优化内存使用
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# 增加文件描述符限制 (适度的值)
echo "deribit soft nofile 4096" | sudo tee -a /etc/security/limits.conf
echo "deribit hard nofile 4096" | sudo tee -a /etc/security/limits.conf
```

### 2. 应用优化配置
在 `.env` 文件中添加：
```env
# Python优化
PYTHONOPTIMIZE=1

# UVicorn优化 (单进程模式)
UVICORN_WORKERS=1
UVICORN_LOOP=uvloop
UVICORN_HTTP=httptools

# 减少轮询频率以节省资源
POSITION_POLLING_INTERVAL_MINUTES=10
ORDER_POLLING_INTERVAL_MINUTES=15
```

### 3. 数据库优化 (SQLite)
```bash
# 定期清理SQLite数据库
sqlite3 ./data/delta_records.db "VACUUM;"
```

### 4. 日志管理
```bash
# 更激进的日志轮转
sudo nano /etc/logrotate.d/deribit-webhook
```

**优化后的Logrotate配置**:
```
/home/deribit/tiger-webhook/logs/*.log {
    daily
    missingok
    rotate 7  # 只保留7天
    compress
    delaycompress
    notifempty
    create 644 deribit deribit
    maxsize 5M  # 文件超过5MB就轮转
}
```

## 安全建议

1. **定期更新系统**：`sudo apt update && sudo apt upgrade`
2. **使用强密码**：确保所有密码足够复杂
3. **配置防火墙**：`sudo ufw enable && sudo ufw allow ssh && sudo ufw allow 3001`
4. **禁用root登录**：编辑SSH配置 `sudo nano /etc/ssh/sshd_config`
5. **使用SSH密钥认证**：禁用密码认证
6. **定期备份**：设置自动备份
7. **监控日志**：定期检查异常访问
8. **限制API访问**：考虑使用IP白名单

### 低配服务器安全优化
```bash
# 启用基本防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 3001
sudo ufw enable

# 禁用不必要的服务
sudo systemctl disable avahi-daemon
sudo systemctl disable cups-browsed
```

## API端点

部署完成后，可以通过以下端点访问服务：

- **健康检查**: `https://your-domain.com/health`
- **Webhook**: `https://your-domain.com/webhook/signal`
- **Delta管理**: `https://your-domain.com/delta`
- **位置轮询**: `https://your-domain.com/api/positions/poll`
- **轮询状态**: `https://your-domain.com/api/positions/polling-status`
- **日志查询**: `https://your-domain.com/api/logs/query`

## 联系信息

如有问题，请联系系统管理员或查看项目文档。