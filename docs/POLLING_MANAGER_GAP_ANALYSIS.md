# 轮询管理器差异分析

## 参考来源
- 参考实现：`../deribit_webhook/src/polling/polling-manager.ts`
- 当前实现：`src/services/polling_manager.py`

## `start_polling` 缺失的业务逻辑

1. **订单轮询从未启动**
   - 参考实现会在启动阶段同时设置仓位与订单两个轮询间隔（`../deribit_webhook/src/polling/polling-manager.ts:27-54`）。
   - 当前代码只启动仓位轮询循环，订单相关字段始终闲置（`src/services/polling_manager.py:68-85`）。

2. **缺少启动时的订单初始化拉取**
   - 参考实现会立即执行 `executeInitialPolling()`，先后获取仓位与未成交订单后再进入计划任务（`../deribit_webhook/src/polling/polling-manager.ts:37-54, 90-104`）。
   - 当前代码没有任何 pending order 的首次拉取逻辑，导致启动阶段缺少订单数据（`src/services/polling_manager.py:68-85`）。

3. **订单轮询错误处理缺位**
   - 参考实现会在每次订单轮询时注册 `catch` 处理器，单独记录失败情况（`../deribit_webhook/src/polling/polling-manager.ts:49-53`）。
   - 当前代码虽然保留了订单错误计数器，但从未与真实任务绑定，重试与退避逻辑实际未实现（`src/services/polling_manager.py:29-35, 105-113`）。

4. **订单轮询状态报告失真**
   - 参考实现能够给出下一次订单轮询的预计时间等实时状态（`../deribit_webhook/src/polling/polling-manager.ts:141-160`）。
   - 当前管理器虽暴露类似字段，但因为订单轮询未启动，始终返回默认值（`src/services/polling_manager.py:275-299`）。

## 影响
- 无法产出 pending order 的洞察、通知与自动化处理。
- 面向仪表盘或状态查询的消费者会获得误导性的订单轮询健康度。
- 订单轮询的错误次数防护从未生效，隐藏了潜在的集成问题。