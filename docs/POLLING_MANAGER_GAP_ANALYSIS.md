# 轮询管理器差异分析

## 参考来源
- 参考实现：`../deribit_webhook/src/polling/polling-manager.ts`
- 当前实现：`src/deribit_webhook/services/polling_manager.py`

## `start_polling` 差异项处理状态

1. **订单轮询从未启动** ✅ 已完成
   - 现在 `start_polling()` 会初始化订单轮询状态并创建 `_order_polling_loop` 任务（`src/deribit_webhook/services/polling_manager.py:62-132`）。

2. **缺少启动时的订单初始化拉取** ✅ 已完成
   - `_execute_initial_polling()` 在启动时先执行一次仓位与订单的完整轮询（`src/deribit_webhook/services/polling_manager.py:220-240`）。

3. **订单轮询错误处理缺位** ✅ 已完成
   - `_order_polling_loop()` 对失败计数、退避并在超限时停用轮询（`src/deribit_webhook/services/polling_manager.py:188-218`）。

4. **订单轮询状态报告失真** ✅ 已完成
   - `get_status()` 返回真实的订单轮询启用状态、下一次时间估计等信息（`src/deribit_webhook/services/polling_manager.py:443-479`）。

## 说明
- 补齐逻辑后新增了针对订单轮询的单元测试 `tests/unit/test_polling_manager_orders.py`。
- 集成用例 `pytest tests/integration/test_api_endpoints.py -k polling` 已验证接口能返回最新状态。