# 美股品种缓存功能

## 概述

在 `TigerClient` 类中实现了美股品种缓存功能，使用 `QuoteClient.get_symbols(market=Market.ALL, include_otc=False)` 接口获取美股品种数据，并实现每24小时自动更新的缓存机制。

## 功能特性

### 核心功能
- ✅ **自动缓存**: 首次调用时从API获取数据并缓存
- ✅ **24小时TTL**: 缓存有效期为24小时，适合每日更新场景
- ✅ **智能刷新**: 支持强制刷新和自动过期检测
- ✅ **多账户支持**: 支持多个账户独立缓存
- ✅ **错误处理**: 完善的异常处理和日志记录

### 数据格式
返回的美股品种数据包含以下字段：
```json
{
  "symbol": "AAPL",           // 股票代码
  "name": "Apple Inc.",       // 公司名称
  "market": "US",             // 市场
  "currency": "USD",          // 货币
  "sector": "Technology",     // 行业板块
  "industry": "Consumer Electronics", // 细分行业
  "market_cap": 3000000000000, // 市值
  "price": 150.25,            // 当前价格
  "volume": 1000000,          // 成交量
  "is_otc": false             // 是否为OTC股票
}
```

## API 接口

### 主要方法

#### `get_us_symbols_cache(account_name=None, force_refresh=False)`
获取美股品种缓存数据。

**参数:**
- `account_name` (str, 可选): 账户名称
- `force_refresh` (bool): 是否强制刷新缓存

**返回:**
- `List[Dict[str, Any]]`: 美股品种列表

**示例:**
```python
client = TigerClient()
symbols = await client.get_us_symbols_cache()
print(f"获取到 {len(symbols)} 个美股品种")
```

#### `get_us_symbols_cache_info(account_name=None)`
获取缓存信息。

**参数:**
- `account_name` (str, 可选): 账户名称

**返回:**
- `Dict[str, Any]`: 缓存信息字典

**示例:**
```python
cache_info = client.get_us_symbols_cache_info()
print(f"缓存年龄: {cache_info['cache_age_hours']:.2f} 小时")
print(f"缓存有效: {cache_info['is_valid']}")
```

#### `invalidate_us_symbols_cache(account_name=None)`
清理缓存。

**参数:**
- `account_name` (str, 可选): 账户名称，如果为None则清理所有账户缓存

**示例:**
```python
# 清理所有账户缓存
client.invalidate_us_symbols_cache()

# 清理指定账户缓存
client.invalidate_us_symbols_cache("my_account")
```

## 使用场景

### 1. 应用启动时预热缓存
```python
async def init_app():
    client = TigerClient()
    # 预热缓存
    await client.get_us_symbols_cache()
    print("美股品种缓存已预热")
```

### 2. 定期检查和更新
```python
async def daily_update():
    client = TigerClient()
    # 强制刷新缓存
    symbols = await client.get_us_symbols_cache(force_refresh=True)
    print(f"更新了 {len(symbols)} 个美股品种")
```

### 3. 监控缓存状态
```python
async def monitor_cache():
    client = TigerClient()
    cache_info = client.get_us_symbols_cache_info()
    
    if not cache_info['is_valid']:
        print("缓存已过期，需要更新")
        await client.get_us_symbols_cache(force_refresh=True)
```

## 配置参数

### 缓存TTL设置
```python
# 在 TigerClient 类中
self._us_symbols_cache_ttl_sec: int = 24 * 3600  # 24小时
```

### 日志级别
缓存操作会记录详细的日志，包括：
- 缓存命中/未命中
- 数据获取状态
- 错误信息
- 性能指标

## 实现细节

### 缓存键格式
```
{account_name}:US_SYMBOLS
```

### 缓存数据结构
```python
{
    'timestamp': 1699999999.999,  # 缓存时间戳
    'symbols': [...],            # 品种数据列表
    'account': 'account_name'    # 账户名称
}
```

### 数据提取逻辑
支持多种数据格式：
- **DataFrame**: 使用 `iterrows()` 遍历
- **List**: 直接遍历列表项
- **Object**: 通过属性访问

### 错误处理策略
- API调用失败时返回空列表，不抛出异常
- 数据格式错误时跳过该项，继续处理其他数据
- 完善的日志记录便于问题排查

## 测试

### 运行测试
```bash
# 运行完整测试
python test_us_symbols_cache.py

# 运行使用示例
python examples/us_symbols_cache_example.py
```

### 测试覆盖
- ✅ 缓存获取和更新
- ✅ 缓存命中验证
- ✅ 强制刷新功能
- ✅ 缓存清理功能
- ✅ 多账户支持
- ✅ 错误处理
- ✅ TTL行为验证

## 性能考虑

### 优势
- **减少API调用**: 24小时内重复请求直接返回缓存
- **快速响应**: 缓存命中时响应时间极短
- **内存高效**: 只在内存中保存必要数据
- **自动清理**: 支持手动和自动缓存清理

### 注意事项
- 首次调用需要等待API响应
- 大量品种数据可能占用较多内存
- 建议在应用启动时预热缓存

## 故障排除

### 常见问题

**Q: 获取到的品种数量为0？**
A: 可能原因：
- 测试账户权限限制
- API返回数据格式变化
- 网络连接问题

**Q: 缓存不生效？**
A: 检查：
- 账户名称是否正确
- 缓存时间戳是否有效
- 是否被其他代码清理

**Q: 如何调试缓存问题？**
A: 启用详细日志：
```python
import logging
logging.getLogger('deribit_webhook').setLevel(logging.DEBUG)
```

## 更新日志

### v1.0.0 (2025-10-14)
- ✅ 初始版本发布
- ✅ 实现基础缓存功能
- ✅ 支持24小时TTL
- ✅ 完善的错误处理
- ✅ 多账户支持
- ✅ 完整的测试覆盖
