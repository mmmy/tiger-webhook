# 日志系统配置 - 毫秒精度

本项目现在支持毫秒级精度的结构化日志记录。

## 功能特性

### ✅ 毫秒级时间戳
- 所有日志条目都包含毫秒级精度的时间戳
- 格式：`2024-01-15 14:30:25.123`
- 支持快速连续日志记录的精确时间区分

### ✅ 结构化日志
- 支持 JSON 和文本两种格式
- 自动包含上下文信息（模块、函数、行号）
- 支持自定义字段和嵌套数据

### ✅ 多种输出方式
- 控制台输出（彩色格式）
- 文件输出（支持日志轮转）
- 可配置的日志级别

## 配置选项

### 环境变量

```bash
# 日志级别
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

# 日志格式
LOG_FORMAT=json|text

# 日志文件路径
LOG_FILE=./logs/combined.log

# 日志文件大小限制
LOG_MAX_SIZE=10MB

# 保留的备份文件数量
LOG_BACKUP_COUNT=5
```

### 配置示例

```bash
# 开发环境 - 文本格式，调试级别
LOG_LEVEL=DEBUG
LOG_FORMAT=text
LOG_FILE=./logs/dev.log

# 生产环境 - JSON格式，信息级别
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=./logs/combined.log
LOG_MAX_SIZE=50MB
LOG_BACKUP_COUNT=10
```

## 使用方法

### 1. 基本使用

```python
from utils.logging_config import get_global_logger

logger = get_global_logger()

# 基本日志记录
logger.info("应用程序启动")
logger.warning("检测到高价差", spread_ratio=0.25)
logger.error("交易失败", symbol="BTC-25DEC24-100000-C", error="连接超时")
```

### 2. 便捷函数

```python
from utils.logging_config import info, warning, error, debug, critical

# 直接使用便捷函数
info("📈 持仓更新", account="test_account", delta=0.25)
warning("⏰ 轮询超时", timeout_seconds=30)
error("🔌 API连接失败", endpoint="/api/v2/private/get_positions")
```

### 3. 带上下文的日志

```python
logger.info("📊 交易数据接收",
           symbol="BTC-25DEC24-100000-C",
           price=45678.123,
           volume=1.5,
           bid=45677.5,
           ask=45678.7,
           spread=1.2,
           timestamp=time.time())
```

### 4. 嵌套数据记录

```python
logger.info("📋 账户摘要",
           account_data={
               "name": "test_account",
               "balance": 10000.50,
               "positions": [
                   {"symbol": "BTC-25DEC24-100000-C", "size": 1.0, "delta": 0.5},
                   {"symbol": "ETH-25DEC24-3500-P", "size": -2.0, "delta": -0.3}
               ],
               "total_delta": 0.2
           })
```

## 日志格式示例

### 文本格式
```
2024-01-15 14:30:25.123 [    INFO] deribit_webhook: 🚀 应用程序启动 (main.py:85)
2024-01-15 14:30:25.124 [ WARNING] deribit_webhook: ⚠️ 检测到高价差 (trading.py:156)
2024-01-15 14:30:25.125 [   ERROR] deribit_webhook: ❌ 交易操作失败 (order_service.py:89)
```

### JSON格式
```json
{
  "timestamp": "2024-01-15 14:30:25.123",
  "level": "INFO",
  "logger": "deribit_webhook",
  "message": "🚀 应用程序启动",
  "module": "main",
  "function": "main",
  "line": 85,
  "port": 3001,
  "environment": "development"
}
```

## 初始化

### 应用程序启动时
```python
from utils.logging_config import init_logging

# 在应用程序启动时初始化日志系统
logger = init_logging()
```

### 在模块中使用
```python
from utils.logging_config import get_logger

# 为特定模块获取日志器
logger = get_logger("trading_service")
```

## 性能考虑

### 毫秒精度的影响
- 毫秒级时间戳对性能影响极小
- 适合高频交易应用的精确时间记录
- 便于调试和性能分析

### 日志轮转
- 自动管理日志文件大小
- 防止磁盘空间耗尽
- 保留历史日志用于分析

## 最佳实践

### 1. 使用结构化字段
```python
# 好的做法
logger.info("订单执行", symbol="BTC", price=50000, quantity=1.0)

# 避免的做法
logger.info(f"订单执行: {symbol} 价格 {price} 数量 {quantity}")
```

### 2. 包含相关上下文
```python
logger.error("API调用失败",
            endpoint="/api/v2/private/buy",
            status_code=500,
            response_time_ms=1500,
            retry_count=3)
```

### 3. 使用适当的日志级别
- `DEBUG`: 详细的调试信息
- `INFO`: 一般信息和状态更新
- `WARNING`: 警告但不影响正常运行
- `ERROR`: 错误但应用程序可以继续
- `CRITICAL`: 严重错误，可能导致应用程序停止

## 测试

运行测试脚本查看毫秒精度日志：

```bash
python test_logging_milliseconds.py
```

这将展示：
- 毫秒级时间戳的精确性
- 不同日志级别的输出
- 结构化数据的记录
- JSON和文本格式的对比
