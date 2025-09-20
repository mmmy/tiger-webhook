# API Documentation | API 文档

This document provides detailed information about the Deribit Webhook Python API endpoints.

本文档提供了 Deribit Webhook Python API 端点的详细信息。

## Base URL | 基础 URL

- Development | 开发环境: `http://localhost:3000`
- Production | 生产环境: `https://your-domain.com`

## Authentication | 身份验证

Most endpoints require authentication via API key or account validation. Include the API key in the request headers:

大多数端点需要通过 API 密钥或账户验证进行身份验证。请在请求头中包含 API 密钥：

```
X-API-Key: your-api-key-here
```

## Response Format | 响应格式

All API responses follow a consistent format:

所有 API 响应都遵循一致的格式：

### Success Response | 成功响应
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response | 错误响应
```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error information",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_1234567890_abcdef123"
}
```

## Health & Status Endpoints | 健康检查和状态端点

### GET /health

Basic health check endpoint.

基础健康检查端点。

**Response | 响应:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

### GET /api/status

Detailed service status information.

详细的服务状态信息。

**Response:**
```json
{
  "service": "Deribit Options Trading Microservice",
  "version": "1.0.0",
  "environment": "development",
  "mock_mode": true,
  "enabled_accounts": 2,
  "accounts": [
    {"name": "main_account", "enabled": true},
    {"name": "test_account", "enabled": true}
  ],
  "test_environment": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Trading Endpoints | 交易端点

### POST /webhook/signal

Process TradingView webhook signal for automated trading.

处理 TradingView webhook 信号进行自动交易。

**Request Body | 请求体:**
```json
{
  "account_name": "main_account",
  "side": "buy",
  "size": "1.0",
  "market_position": "long",
  "prev_market_position": "flat",
  "comment": "Entry signal",
  "tv_id": "12345",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Response | 响应:**
```json
{
  "success": true,
  "message": "Trade executed successfully",
  "order_id": "order_1234567890",
  "instrument_name": "BTC-25DEC21-50000-C",
  "executed_quantity": 1.0,
  "executed_price": 0.05,
  "final_order_state": "filled",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET /api/trading/options/{account_name}

Get available options for an account.

获取账户的可用期权。

**Parameters | 参数:**
- `account_name` (path): Account name | 账户名称
- `underlying` (query): Underlying asset (default: BTC) | 标的资产（默认：BTC）
- `direction` (query): Option direction (long/short) | 期权方向（多头/空头）
- `expired` (query): Include expired options (default: false) | 包含已过期期权（默认：false）

**Response:**
```json
{
  "success": true,
  "message": "Found 150 options",
  "data": {
    "instruments": [
      {
        "instrument_name": "BTC-25DEC21-50000-C",
        "kind": "option",
        "option_type": "call",
        "strike": 50000,
        "expiration_timestamp": 1640419200000,
        "underlying": "BTC"
      }
    ],
    "total": 150,
    "filtered": 150,
    "underlying": "BTC",
    "direction": "long"
  }
}
```

## Position Management Endpoints | 持仓管理端点

### GET /api/positions/{account_name}/{currency}

Retrieve Tiger Brokers account positions for a specific currency.

获取 Tiger Brokers 账户的指定币种持仓信息。

**Parameters | 参数:**
- `account_name` (path): Account name | 账户名称
- `currency` (path): Currency code (e.g. USD) | 币种（例如 USD）

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 2 positions for tiger_main",
  "account_name": "tiger_main",
  "currency": "USD",
  "mock_mode": false,
  "positions": [
    {
      "instrument_name": "AAPL_20241220_200_C",
      "size": 1.0,
      "mark_price": 2.5,
      "delta": 0.52,
      "gamma": 0.08,
      "theta": -0.03,
      "vega": 0.12,
      "direction": "buy",
      "kind": "option"
    }
  ],
  "summary": {
    "account": "XXXXXXXX",
    "currency": "USD",
    "option_position_count": 2,
    "option_total_delta": 1.04,
    "option_total_gamma": 0.16,
    "option_total_theta": -0.06,
    "option_total_vega": 0.24,
    "total_unrealized_pnl": 25.0,
    "total_realized_pnl": 10.0,
    "total_mark_value": 25000.0,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### GET /api/positions/{account_name}/delta

Calculate position delta for an account.

计算账户的持仓 delta。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Calculated delta for main_account",
  "account_name": "main_account",
  "currency": "BTC",
  "mock_mode": true,
  "greeks": {
    "delta": 2.5,
    "gamma": 0.05,
    "theta": -0.1,
    "vega": 1.2
  },
  "position_count": 5
}
```

### GET /api/positions/polling/status

Get position polling status.

获取持仓轮询状态。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Polling status retrieved successfully",
  "polling_enabled": true,
  "accounts": ["main_account", "test_account"],
  "interval_seconds": 30
}
```

### POST /api/positions/polling/start

Start position polling.

开始持仓轮询。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Position polling started successfully",
  "is_running": true,
  "interval_seconds": 30,
  "mock_mode": true
}
```

### POST /api/positions/polling/stop

Stop position polling.

停止持仓轮询。

**Response:**
```json
{
  "success": true,
  "message": "Position polling stopped successfully",
  "is_running": false,
  "mock_mode": true
}
```

### POST /api/positions/poll

Perform manual position poll.

执行手动持仓轮询。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Manual poll completed successfully",
  "start_time": "2024-01-01T12:00:00Z",
  "end_time": "2024-01-01T12:00:05Z",
  "duration_seconds": 5.2,
  "mock_mode": true
}
```

## WeChat Bot Endpoints | 微信机器人端点

### POST /api/wechat/test/{account_name}

Test WeChat notification for an account.

测试账户的微信通知。

**Response | 响应:**
```json
{
  "success": true,
  "message": "WeChat test notification sent successfully",
  "account_name": "main_account"
}
```

### GET /api/wechat/config/{account_name}

Get WeChat configuration for an account.

获取账户的微信配置。

**Response:**
```json
{
  "success": true,
  "message": "WeChat configuration found",
  "account_name": "main_account",
  "has_config": true,
  "config_details": {
    "webhook_url_configured": true,
    "timeout": 10000,
    "retry_count": 3,
    "retry_delay": 1000
  }
}
```

### GET /api/wechat/configs

Get all WeChat configurations.

获取所有微信配置。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Found 2 WeChat configurations",
  "total_configs": 2,
  "configs": [
    {
      "account_name": "main_account",
      "webhook_url_configured": true,
      "timeout": 10000,
      "retry_count": 3,
      "retry_delay": 1000
    }
  ]
}
```

### POST /api/wechat/broadcast

Broadcast message to WeChat groups.

向微信群组广播消息。

**Request Body | 请求体:**
```json
{
  "message": "System maintenance scheduled",
  "notification_type": "system",
  "account_names": ["main_account", "test_account"]
}
```

**Response | 响应:**
```json
{
  "success": true,
  "message": "Broadcast sent to 2/2 accounts",
  "results": {
    "main_account": true,
    "test_account": true
  },
  "total_accounts": 2,
  "successful_sends": 2
}
```

### POST /api/wechat/test-all

Test WeChat notifications for all configured accounts.

测试所有已配置账户的微信通知。

**Response:**
```json
{
  "success": true,
  "message": "WeChat test completed: 2/2 successful",
  "results": {
    "main_account": true,
    "test_account": true
  },
  "total_accounts": 2,
  "successful_tests": 2
}
```

## Authentication Endpoints | 身份验证端点

### POST /api/auth/token/{account_name}

Get authentication token for an account.

获取账户的身份验证令牌。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Authentication successful",
  "account_name": "main_account",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write",
  "is_mock": true
}
```

### POST /api/auth/refresh/{account_name}

Refresh authentication token for an account.

刷新账户的身份验证令牌。

**Response | 响应:**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "account_name": "main_account",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write",
  "is_mock": true
}
```

## Error Codes | 错误代码

| Code | Description | 描述 |
|------|-------------|------|
| 400 | Bad Request - Invalid request parameters | 错误请求 - 无效的请求参数 |
| 401 | Unauthorized - Missing or invalid authentication | 未授权 - 缺少或无效的身份验证 |
| 403 | Forbidden - Insufficient permissions | 禁止访问 - 权限不足 |
| 404 | Not Found - Resource not found | 未找到 - 资源不存在 |
| 422 | Unprocessable Entity - Validation error | 无法处理的实体 - 验证错误 |
| 429 | Too Many Requests - Rate limit exceeded | 请求过多 - 超出速率限制 |
| 500 | Internal Server Error - Server error | 内部服务器错误 - 服务器错误 |

## Rate Limiting | 速率限制

API endpoints are rate limited to prevent abuse:

API 端点有速率限制以防止滥用：

- General API | 通用 API: 60 requests per minute | 每分钟 60 次请求
- Webhook endpoint | Webhook 端点: 30 requests per minute | 每分钟 30 次请求
- Authentication | 身份验证: 10 requests per minute | 每分钟 10 次请求

Rate limit headers are included in responses:

响应中包含速率限制头：
- `X-RateLimit-Limit`: Request limit per window | 每个时间窗口的请求限制
- `X-RateLimit-Remaining`: Remaining requests in current window | 当前时间窗口剩余请求数
- `X-RateLimit-Reset`: Time when the rate limit resets | 速率限制重置时间

## Interactive Documentation | 交互式文档

When the service is running, you can access interactive API documentation:

当服务运行时，您可以访问交互式 API 文档：

- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc

These interfaces allow you to test API endpoints directly from your browser.

这些界面允许您直接从浏览器测试 API 端点。
