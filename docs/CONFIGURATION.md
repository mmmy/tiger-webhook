# Configuration Guide | 配置指南

This guide explains how to configure the Deribit Webhook Python service for different environments and use cases.

本指南说明如何为不同环境和用例配置 Deribit Webhook Python 服务。

## Configuration Files | 配置文件

The service uses two main configuration files:

该服务使用两个主要配置文件：

1. **Environment Configuration | 环境配置** (`.env`)
2. **API Keys Configuration | API 密钥配置** (`config/apikeys.yml`)

## Environment Configuration | 环境配置

### File Locations | 文件位置

- `.env.example` - Template with all available options | 包含所有可用选项的模板
- `.env.development` - Development settings (not included) | 开发设置（不包含）
- `.env.production` - Production settings template | 生产设置模板
- `.env.test` - Test environment settings | 测试环境设置
- `.env` - Active configuration (create from templates) | 活动配置（从模板创建）

### Core Settings | 核心设置

#### Server Configuration | 服务器配置
```bash
# Server binding | 服务器绑定
HOST=0.0.0.0
PORT=3000

# Environment mode | 环境模式
NODE_ENV=development|production|test
```

#### Application Settings | 应用程序设置
```bash
# Mock mode (for development/testing) | 模拟模式（用于开发/测试）
USE_MOCK_MODE=true|false

# Deribit environment | Deribit 环境
USE_TEST_ENVIRONMENT=true|false

# Auto-start features | 自动启动功能
AUTO_START_POLLING=true|false
```

#### Database Configuration | 数据库配置
```bash
# SQLite database URL | SQLite 数据库 URL
DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db

# For in-memory database (testing) | 内存数据库（测试用）
DATABASE_URL=sqlite+aiosqlite:///:memory:
```

#### Security Settings | 安全设置
```bash
# Application secret key (CHANGE IN PRODUCTION!) | 应用程序密钥（生产环境中请更改！）
SECRET_KEY=your-secure-secret-key-here

# Webhook signature verification | Webhook 签名验证
WEBHOOK_SECRET=your-webhook-secret
WEBHOOK_SECURITY_ENABLED=true|false
WEBHOOK_TIMESTAMP_TOLERANCE=300

# API key authentication | API 密钥身份验证
API_KEY_HEADER=X-API-Key
API_KEY_VALUE=your-api-key-here

# Rate limiting | 速率限制
RATE_LIMIT_ENABLED=true|false
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

#### Deribit API Configuration | Deribit API 配置
```bash
# API URLs (usually don't change these) | API URL（通常不要更改这些）
DERIBIT_API_URL=https://www.deribit.com/api/v2
DERIBIT_TEST_API_URL=https://test.deribit.com/api/v2
DERIBIT_WS_URL=wss://www.deribit.com/ws/api/v2
DERIBIT_TEST_WS_URL=wss://test.deribit.com/ws/api/v2

# API key file location | API 密钥文件位置
API_KEY_FILE=./config/apikeys.yml
```

#### Position Polling Configuration | 持仓轮询配置
```bash
# Enable position polling | 启用持仓轮询
ENABLE_POSITION_POLLING=true|false

# Polling interval in seconds | 轮询间隔（秒）
POLLING_INTERVAL_SECONDS=30

# Maximum consecutive errors before stopping | 停止前的最大连续错误数
MAX_POLLING_ERRORS=5

# Auto-start polling on service startup | 服务启动时自动开始轮询
AUTO_START_POLLING=true|false
```

#### Background Tasks Configuration | 后台任务配置
```bash
# Database cleanup | 数据库清理
ENABLE_DATABASE_CLEANUP=true|false
DATABASE_CLEANUP_DAYS=30

# Health checks | 健康检查
ENABLE_HEALTH_CHECKS=true|false
HEALTH_CHECK_INTERVAL=300
```

#### WeChat Bot Configuration | 微信机器人配置
```bash
# Global defaults (can be overridden per account) | 全局默认值（可按账户覆盖）
WECHAT_TIMEOUT=10000
WECHAT_RETRY_COUNT=3
WECHAT_RETRY_DELAY=1000
```

#### Logging Configuration | 日志配置
```bash
# Log level | 日志级别
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# Log format | 日志格式
LOG_FORMAT=text|json

# Log file location | 日志文件位置
LOG_FILE=./logs/combined.log

# Log rotation | 日志轮转
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

#### Performance Settings | 性能设置
```bash
# Worker processes (for production) | 工作进程（用于生产环境）
WORKER_PROCESSES=4

# Connection limits | 连接限制
MAX_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=5

# Monitoring | 监控
ENABLE_METRICS=true|false
METRICS_PORT=9090
```

## API Keys Configuration | API 密钥配置

### File Structure | 文件结构

The `config/apikeys.yml` file contains Deribit API credentials and account-specific settings:

`config/apikeys.yml` 文件包含 Deribit API 凭据和账户特定设置：

```yaml
accounts:
  - name: main_account
    description: "Main trading account"
    clientId: "your_client_id_here"
    clientSecret: "your_client_secret_here"
    enabled: true
    grantType: "client_credentials"
    scope: ""
    
    # WeChat Bot configuration (optional)
    wechat_bot:
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key"
      timeout: 10000
      retry_count: 3
      retry_delay: 1000
      enabled: true

  - name: test_account
    description: "Test account for development"
    clientId: "test_client_id"
    clientSecret: "test_client_secret"
    enabled: false
    grantType: "client_credentials"
    scope: ""
    
    wechat_bot:
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key"
      enabled: false

# Global settings (optional)
settings:
  connectionTimeout: 30
  maxReconnectAttempts: 5
  rateLimitPerMinute: 60
```

### Account Configuration | 账户配置

#### Required Fields | 必填字段
- `name`: Unique account identifier | 唯一账户标识符
- `clientId`: Deribit API client ID | Deribit API 客户端 ID
- `clientSecret`: Deribit API client secret | Deribit API 客户端密钥
- `enabled`: Whether the account is active | 账户是否激活

#### Optional Fields | 可选字段
- `description`: Human-readable description | 人类可读的描述
- `grantType`: OAuth grant type (default: "client_credentials") | OAuth 授权类型（默认："client_credentials"）
- `scope`: OAuth scope (usually empty for Deribit) | OAuth 范围（对于 Deribit 通常为空）

#### WeChat Bot Configuration | 微信机器人配置
- `webhook_url`: WeChat bot webhook URL | 微信机器人 webhook URL
- `timeout`: Request timeout in milliseconds | 请求超时时间（毫秒）
- `retry_count`: Number of retry attempts | 重试次数
- `retry_delay`: Delay between retries in milliseconds | 重试间隔时间（毫秒）
- `enabled`: Whether WeChat notifications are enabled | 是否启用微信通知

### Security Best Practices | 安全最佳实践

1. **Never commit real API keys to version control** | **永远不要将真实的 API 密钥提交到版本控制**
2. **Use environment-specific configuration files** | **使用特定环境的配置文件**
3. **Restrict file permissions** | **限制文件权限**: `chmod 600 config/apikeys.yml`
4. **Use different keys for different environments** | **为不同环境使用不同的密钥**
5. **Rotate API keys regularly** | **定期轮换 API 密钥**

## Environment-Specific Configurations

### Development Environment

```bash
# .env (development)
NODE_ENV=development
USE_MOCK_MODE=true
USE_TEST_ENVIRONMENT=true
AUTO_START_POLLING=false
LOG_LEVEL=DEBUG
LOG_FORMAT=text
RATE_LIMIT_ENABLED=false
WEBHOOK_SECURITY_ENABLED=false
```

### Production Environment

```bash
# .env (production)
NODE_ENV=production
USE_MOCK_MODE=false
USE_TEST_ENVIRONMENT=false
AUTO_START_POLLING=true
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_ENABLED=true
WEBHOOK_SECURITY_ENABLED=true
SECRET_KEY=your-production-secret-key
WEBHOOK_SECRET=your-production-webhook-secret
```

### Test Environment

```bash
# .env (test)
NODE_ENV=test
USE_MOCK_MODE=true
USE_TEST_ENVIRONMENT=true
AUTO_START_POLLING=false
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite+aiosqlite:///:memory:
RATE_LIMIT_ENABLED=false
WEBHOOK_SECURITY_ENABLED=false
```

## Configuration Validation

The service validates configuration on startup and will report errors for:

- Missing required environment variables
- Invalid API key file format
- Inaccessible database paths
- Invalid URL formats
- Missing account configurations

## Dynamic Configuration

Some settings can be changed at runtime through the API:

### Polling Configuration
```bash
# Start/stop polling
POST /api/positions/polling/start
POST /api/positions/polling/stop
```

### WeChat Testing
```bash
# Test WeChat configuration
POST /api/wechat/test/{account_name}
```

## Configuration Templates

### Minimal Development Setup

```bash
# .env
NODE_ENV=development
USE_MOCK_MODE=true
USE_TEST_ENVIRONMENT=true
PORT=3000
DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db
SECRET_KEY=dev-secret-key
```

```yaml
# config/apikeys.yml
accounts:
  - name: dev_account
    description: "Development account"
    clientId: "dev_client_id"
    clientSecret: "dev_client_secret"
    enabled: true
```

### Production Setup

```bash
# .env
NODE_ENV=production
USE_MOCK_MODE=false
USE_TEST_ENVIRONMENT=false
PORT=3000
HOST=0.0.0.0
DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db
SECRET_KEY=your-secure-production-key
WEBHOOK_SECRET=your-webhook-secret
API_KEY_VALUE=your-api-key
RATE_LIMIT_ENABLED=true
WEBHOOK_SECURITY_ENABLED=true
ENABLE_POSITION_POLLING=true
POLLING_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=./logs/combined.log
```

```yaml
# config/apikeys.yml
accounts:
  - name: production_account
    description: "Production trading account"
    clientId: "prod_client_id"
    clientSecret: "prod_client_secret"
    enabled: true
    
    wechat_bot:
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=prod_key"
      enabled: true
```

## Troubleshooting Configuration

### Common Issues

1. **Configuration file not found**
   ```bash
   # Check file exists
   ls -la config/apikeys.yml
   # Copy from template
   cp config/apikeys.example.yml config/apikeys.yml
   ```

2. **Invalid YAML syntax**
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('config/apikeys.yml'))"
   ```

3. **Permission denied**
   ```bash
   # Fix file permissions
   chmod 644 config/apikeys.yml
   chown $USER:$USER config/apikeys.yml
   ```

4. **Environment variable not loaded**
   ```bash
   # Check .env file exists
   ls -la .env
   # Verify variable is set
   echo $USE_MOCK_MODE
   ```

### Configuration Validation

The service provides configuration validation:

```bash
# Check configuration
python -m deribit_webhook.config.validate

# Or through API
GET /api/status
```

### Debug Configuration | 调试配置

Enable debug logging to see configuration loading:

启用调试日志以查看配置加载：

```bash
LOG_LEVEL=DEBUG
```

This will show:

这将显示：
- Configuration file loading | 配置文件加载
- Environment variable resolution | 环境变量解析
- Account validation | 账户验证
- API key verification | API 密钥验证

## Best Practices | 最佳实践

1. **Use environment-specific files** | **使用特定环境的文件**
2. **Never commit secrets to version control** | **永远不要将密钥提交到版本控制**
3. **Validate configuration before deployment** | **部署前验证配置**
4. **Use secure file permissions** | **使用安全的文件权限**
5. **Monitor configuration changes** | **监控配置更改**
6. **Document custom settings** | **记录自定义设置**
7. **Test configuration in staging environment** | **在预发布环境中测试配置**
8. **Use configuration management tools for production** | **在生产环境中使用配置管理工具**

This configuration guide should help you properly set up the service for your specific needs and environment.

本配置指南应该能帮助您根据特定需求和环境正确设置服务。
