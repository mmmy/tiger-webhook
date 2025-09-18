# Deployment Guide | 部署指南

This guide covers various deployment options for the Deribit Webhook Python service.

本指南涵盖了 Deribit Webhook Python 服务的各种部署选项。

## Prerequisites | 先决条件

- Python 3.9+
- Docker (for containerized deployment) | Docker（用于容器化部署）
- Docker Compose (for multi-container deployment) | Docker Compose（用于多容器部署）
- Git (for source code management) | Git（用于源代码管理）

## Environment Setup | 环境设置

### 1. Configuration Files | 配置文件

Before deployment, ensure you have the necessary configuration files:

在部署之前，确保您拥有必要的配置文件：

```bash
# Environment configuration | 环境配置
cp .env.example .env          # Development | 开发环境
cp .env.production .env       # Production | 生产环境
cp .env.test .env            # Testing | 测试环境

# API keys configuration | API 密钥配置
mkdir -p config
cp ../deribit_webhook/config/apikeys.example.yml config/apikeys.yml
```

### 2. Directory Structure | 目录结构

Create necessary directories:

创建必要的目录：

```bash
mkdir -p data logs config public/static
```

### 3. Environment Variables | 环境变量

Key environment variables to configure:

需要配置的关键环境变量：

#### Development | 开发环境
```bash
NODE_ENV=development
USE_MOCK_MODE=true
USE_TEST_ENVIRONMENT=true
PORT=3000
```

#### Production | 生产环境
```bash
NODE_ENV=production
USE_MOCK_MODE=false
USE_TEST_ENVIRONMENT=false
PORT=3000
SECRET_KEY=your-secure-secret-key
```

## Deployment Methods | 部署方法

### Method 1: Local Development | 方法 1：本地开发

For local development and testing:

用于本地开发和测试：

```bash
# Install dependencies | 安装依赖
pip install -r requirements.txt
pip install -e .

# Run in development mode | 以开发模式运行
make dev

# Or manually | 或手动运行
uvicorn deribit_webhook.app:app --reload --host 0.0.0.0 --port 3000 --app-dir src
```

### Method 2: Production Server | 方法 2：生产服务器

For production deployment on a server:

用于在服务器上进行生产部署：

```bash
# Setup production environment | 设置生产环境
cp .env.production .env
# Edit .env with your production settings | 编辑 .env 文件设置您的生产配置

# Install dependencies | 安装依赖
pip install -r requirements.txt
pip install -e .

# Run with Gunicorn | 使用 Gunicorn 运行
gunicorn deribit_webhook.app:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:3000 \
  --access-logfile ./logs/access.log \
  --error-logfile ./logs/error.log \
  --log-level info
```

### Method 3: Docker Deployment | 方法 3：Docker 部署

#### Using the Deployment Script | 使用部署脚本

The easiest way to deploy with Docker:

使用 Docker 部署的最简单方法：

```bash
# Setup environment | 设置环境
./deploy.sh setup production

# Deploy standalone container | 部署独立容器
./deploy.sh deploy

# Or deploy with Docker Compose | 或使用 Docker Compose 部署
./deploy.sh compose

# Or deploy with Nginx proxy | 或使用 Nginx 代理部署
./deploy.sh compose-proxy
```

#### Manual Docker Deployment

Build and run manually:

```bash
# Build image
docker build -t deribit-webhook-python .

# Run container
docker run -d \
  --name deribit-webhook \
  -p 3001:3001 \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  deribit-webhook-python
```

#### Docker Compose Deployment

```bash
# Basic deployment
docker-compose up -d --build

# With Nginx proxy
docker-compose --profile with-proxy up -d --build
```

### Method 4: Cloud Deployment

#### AWS ECS

1. **Build and push image to ECR:**
```bash
# Create ECR repository
aws ecr create-repository --repository-name deribit-webhook-python

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t deribit-webhook-python .
docker tag deribit-webhook-python:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/deribit-webhook-python:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/deribit-webhook-python:latest
```

2. **Create ECS task definition and service**

#### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/deribit-webhook-python

# Deploy to Cloud Run
gcloud run deploy deribit-webhook-python \
  --image gcr.io/PROJECT-ID/deribit-webhook-python \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 3000
```

#### Azure Container Instances

```bash
# Create resource group
az group create --name deribit-webhook-rg --location eastus

# Create container instance
az container create \
  --resource-group deribit-webhook-rg \
  --name deribit-webhook \
  --image deribit-webhook-python:latest \
  --dns-name-label deribit-webhook \
  --ports 3000
```

## Reverse Proxy Setup | 反向代理设置

### Nginx Configuration | Nginx 配置

For production deployments, use Nginx as a reverse proxy:

对于生产部署，使用 Nginx 作为反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=webhook:10m rate=5r/s;

    # Static files
    location /static/ {
        proxy_pass http://localhost:3000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Webhook endpoint
    location /webhook/ {
        limit_req zone=webhook burst=10 nodelay;
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # All other requests
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/TLS Configuration

For HTTPS support, add SSL configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Same location blocks as above
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring and Logging | 监控和日志

### Health Checks | 健康检查

The service provides health check endpoints:

该服务提供健康检查端点：

- Basic | 基础: `GET /health`
- Detailed | 详细: `GET /api/status`

### Logging Configuration | 日志配置

Configure logging in your environment:

在您的环境中配置日志：

```bash
# Log format (text or json) | 日志格式（文本或 json）
LOG_FORMAT=json

# Log file location | 日志文件位置
LOG_FILE=./logs/combined.log

# Log level | 日志级别
LOG_LEVEL=INFO
```

### Monitoring Setup | 监控设置

#### Prometheus Metrics | Prometheus 指标

If metrics are enabled:

如果启用了指标：

```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

Access metrics at | 访问指标: `http://localhost:9090/metrics`

#### Log Aggregation | 日志聚合

For centralized logging, configure log shipping:

对于集中式日志记录，配置日志传输：

```bash
# Using Filebeat | 使用 Filebeat
filebeat.inputs:
- type: log
  paths:
    - /app/logs/*.log
  fields:
    service: deribit-webhook-python
```

## Security Considerations | 安全考虑

### Production Security Checklist | 生产安全检查清单

- [ ] Change default secret keys | 更改默认密钥
- [ ] Enable HTTPS/TLS | 启用 HTTPS/TLS
- [ ] Configure rate limiting | 配置速率限制
- [ ] Set up webhook signature verification | 设置 webhook 签名验证
- [ ] Use environment variables for secrets | 使用环境变量存储密钥
- [ ] Enable API key authentication | 启用 API 密钥身份验证
- [ ] Configure CORS appropriately | 适当配置 CORS
- [ ] Set up log monitoring | 设置日志监控
- [ ] Enable health checks | 启用健康检查
- [ ] Use non-root user in containers | 在容器中使用非 root 用户

### Environment Variables Security | 环境变量安全

Never commit sensitive environment variables to version control:

永远不要将敏感的环境变量提交到版本控制：

```bash
# Use environment-specific files | 使用特定环境的文件
.env.local
.env.production
.env.staging

# Or use external secret management | 或使用外部密钥管理
AWS_SECRETS_MANAGER_SECRET_ID=deribit-webhook-secrets
```

## Troubleshooting | 故障排除

### Common Issues | 常见问题

1. **Port already in use | 端口已被使用**
   ```bash
   # Find process using port 3000 | 查找使用端口 3000 的进程
   lsof -i :3000
   # Kill process | 终止进程
   kill -9 <PID>
   ```

2. **Permission denied errors | 权限拒绝错误**
   ```bash
   # Fix file permissions | 修复文件权限
   chmod +x deploy.sh
   chown -R $USER:$USER data logs
   ```

3. **Database connection errors | 数据库连接错误**
   ```bash
   # Check database file permissions | 检查数据库文件权限
   ls -la data/
   # Recreate database directory | 重新创建数据库目录
   rm -rf data && mkdir data
   ```

4. **Configuration file not found | 配置文件未找到**
   ```bash
   # Verify configuration files exist | 验证配置文件是否存在
   ls -la config/
   # Copy from examples | 从示例复制
   cp config/apikeys.example.yml config/apikeys.yml
   ```

### Deployment Script Commands

```bash
# Show help
./deploy.sh help

# Setup environment
./deploy.sh setup production

# Build Docker image
./deploy.sh build

# Deploy standalone
./deploy.sh deploy

# Deploy with compose
./deploy.sh compose

# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Stop service
./deploy.sh stop

# Clean up
./deploy.sh clean
```

## Performance Tuning | 性能调优

### Production Optimization | 生产优化

1. **Worker Processes | 工作进程**
   ```bash
   # Gunicorn workers (CPU cores * 2 + 1) | Gunicorn 工作进程（CPU 核心数 * 2 + 1）
   gunicorn -w 4 deribit_webhook.app:app
   ```

2. **Database Optimization | 数据库优化**
   ```bash
   # Enable WAL mode for SQLite | 为 SQLite 启用 WAL 模式
   DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db?mode=rwc&cache=shared
   ```

3. **Caching | 缓存**
   ```bash
   # Enable response caching | 启用响应缓存
   ENABLE_CACHING=true
   CACHE_TTL=300
   ```

4. **Connection Pooling | 连接池**
   ```bash
   # HTTP client settings | HTTP 客户端设置
   MAX_CONNECTIONS=100
   KEEPALIVE_TIMEOUT=5
   ```

This deployment guide should help you successfully deploy the Deribit Webhook Python service in various environments.

本部署指南应该能帮助您在各种环境中成功部署 Deribit Webhook Python 服务。
