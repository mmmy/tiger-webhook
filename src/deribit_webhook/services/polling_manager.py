"""
Enhanced polling manager

Manages background polling of account positions and orders.
Supports both position polling (every 15 minutes) and order polling (every 5 minutes).
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from pydantic import ValidationError

from ..config import ConfigLoader, settings
from .tiger_client import TigerClient
from .trading_client_factory import get_trading_client
from .position_adjustment import execute_position_adjustment, execute_position_close
from .wechat_notification import WeChatNotificationService
from ..database import get_delta_manager
from ..database.types import (
    DeltaRecordQuery,
    DeltaRecordType,
    CreateDeltaRecordInput,
    DeltaRecord
)
from ..models.deribit_types import DeribitPosition


class PollingManager:
    """Enhanced polling manager for positions and orders"""

    OPTION_BASE_CURRENCIES = ("BTC", "ETH", "SOL", "USDC")

    def __init__(self):
        # Position polling state
        self.is_running = False
        self.position_polling_task: Optional[asyncio.Task] = None
        self.position_error_count = 0
        self.last_position_poll_time: Optional[datetime] = None
        self.position_poll_count = 0

        # Order polling state (future enhancement)
        self.order_polling_enabled = False
        self.order_polling_task: Optional[asyncio.Task] = None
        self.order_error_count = 0
        self.last_order_poll_time: Optional[datetime] = None
        self.order_poll_count = 0

        # Initial burst polling task handle
        self.initial_polling_task: Optional[asyncio.Task] = None

        # Shared resources
        self._config_loader: Optional[ConfigLoader] = None
        self._delta_manager = None
        self._wechat_service: Optional[WeChatNotificationService] = None

        # Backward compatibility aliases
        self.polling_task = None  # Will point to position_polling_task
        self.error_count = 0      # Will point to position_error_count
        self.last_poll_time = None # Will point to last_position_poll_time
        self.poll_count = 0       # Will point to position_poll_count

    def _get_config_loader(self) -> ConfigLoader:
        """Get config loader instance"""
        if self._config_loader is None:
            self._config_loader = ConfigLoader.get_instance()
        return self._config_loader

    def _get_delta_manager(self):
        """Get delta manager instance"""
        if self._delta_manager is None:
            self._delta_manager = get_delta_manager()
        return self._delta_manager

    def _get_wechat_service(self) -> WeChatNotificationService:
        """Get WeChat notification service"""
        if self._wechat_service is None:
            self._wechat_service = WeChatNotificationService()
        return self._wechat_service

    async def start_polling(self):
        """Start position polling (and optionally order polling)"""
        if self.is_running:
            print("?? Position polling is already running")
            return

        if not settings.enable_position_polling:
            print("?? Position polling is disabled in settings")
            return

        print("🟢 Starting position polling...")
        self.is_running = True
        self.position_error_count = 0
        self.last_position_poll_time = None
        self.position_poll_count = 0

        # Prepare order polling state
        self.order_error_count = 0
        self.last_order_poll_time = None
        self.order_poll_count = 0
        self.order_polling_enabled = True

        # Start the position polling task
        self.position_polling_task = asyncio.create_task(self._position_polling_loop())

        # Update backward compatibility aliases
        self.polling_task = self.position_polling_task
        self.error_count = self.position_error_count

        # Start the order polling task
        self.order_polling_task = asyncio.create_task(self._order_polling_loop())

        # Kick off an initial polling pass without blocking the caller
        self.initial_polling_task = asyncio.create_task(self._execute_initial_polling())
        self.initial_polling_task.add_done_callback(self._on_initial_polling_complete)

        # Use minute-based intervals for display (following reference project pattern)
        position_interval = settings.position_polling_interval_minutes
        order_interval = settings.order_polling_interval_minutes
        print(f"? Position polling started with {position_interval} minute interval")
        print(f"? Order polling started with {order_interval} minute interval")

    async def stop_polling(self):
        """Stop all polling (position and order)"""
        if not self.is_running:
            print("?? Polling is not running")
            return

        print("?? Stopping position polling...")
        self.is_running = False

        # Stop position polling
        if self.position_polling_task:
            self.position_polling_task.cancel()
            try:
                await self.position_polling_task
            except asyncio.CancelledError:
                pass
            self.position_polling_task = None

        # Stop order polling
        self.order_polling_enabled = False
        if self.order_polling_task:
            self.order_polling_task.cancel()
            try:
                await self.order_polling_task
            except asyncio.CancelledError:
                pass
            self.order_polling_task = None

        # Stop initial polling burst if still running
        if self.initial_polling_task and not self.initial_polling_task.done():
            self.initial_polling_task.cancel()
            try:
                await self.initial_polling_task
            except asyncio.CancelledError:
                pass
        self.initial_polling_task = None

        # Update backward compatibility aliases
        self.polling_task = None

        print("? All polling stopped")

    async def _position_polling_loop(self):
        """Main position polling loop"""
        try:
            while self.is_running:
                try:
                    await self._poll_all_accounts()
                    self.position_error_count = 0  # Reset error count on success
                    self.last_position_poll_time = datetime.now()
                    self.position_poll_count += 1

                    # Update backward compatibility aliases
                    self.error_count = self.position_error_count
                    self.last_poll_time = self.last_position_poll_time
                    self.poll_count = self.position_poll_count

                    # Wait for next poll (convert minutes to seconds)
                    interval_seconds = settings.position_polling_interval_minutes * 60
                    await asyncio.sleep(interval_seconds)

                except Exception as error:
                    self.position_error_count += 1
                    self.error_count = self.position_error_count  # Update alias
                    print(f"❌ Position polling error #{self.position_error_count}: {error}")

                    # Stop polling if too many errors
                    if self.position_error_count >= settings.max_polling_errors:
                        print(f"🛑 Too many position polling errors ({self.position_error_count}), stopping polling")
                        self.is_running = False
                        break

                    # Wait before retry (use shorter interval for retries)
                    retry_interval = min(30, settings.position_polling_interval_minutes * 60)
                    await asyncio.sleep(retry_interval)

        except asyncio.CancelledError:
            print("📡 Position polling loop cancelled")
            raise
        except Exception as error:
            print(f"💥 Fatal position polling error: {error}")
            self.is_running = False


    async def _order_polling_loop(self):
        """Main order polling loop"""
        try:
            while self.is_running and self.order_polling_enabled:
                try:
                    processed_accounts = await self._poll_all_pending_orders()
                    self.order_error_count = 0  # Reset error count on success
                    self.last_order_poll_time = datetime.now()
                    self.order_poll_count += 1

                    order_interval_minutes = max(1, settings.order_polling_interval_minutes)
                    await asyncio.sleep(order_interval_minutes * 60)

                except Exception as error:
                    self.order_error_count += 1
                    print(f"? Order polling error #{self.order_error_count}: {error}")

                    if self.order_error_count >= settings.max_polling_errors:
                        print(f"?? Too many order polling errors ({self.order_error_count}), disabling order polling")
                        self.order_polling_enabled = False
                        break

                    retry_interval = min(30, max(1, settings.order_polling_interval_minutes) * 60)
                    await asyncio.sleep(retry_interval)

        except asyncio.CancelledError:
            print("?? Order polling loop cancelled")
            raise
        except Exception as error:
            print(f"?? Fatal order polling error: {error}")
            self.order_polling_enabled = False

    async def _execute_initial_polling(self):
        """Run initial polling for positions and pending orders"""
        try:
            print("?? Starting initial polling burst...")
            position_processed = await self._poll_all_accounts()
            self.position_error_count = 0
            if position_processed is not None:
                self.last_position_poll_time = datetime.now()
                self.position_poll_count += 1
            print(f"? Initial position polling completed: {position_processed} accounts processed")

            if self.order_polling_enabled:
                order_processed = await self._poll_all_pending_orders()
                self.order_error_count = 0
                self.last_order_poll_time = datetime.now()
                self.order_poll_count += 1
                print(f"? Initial order polling completed: {order_processed} accounts processed")
            else:
                print("? Order polling disabled; skipping initial pending order check")

            print("?? Initial polling burst completed successfully")

        except Exception as error:
            print(f"? Initial polling burst failed: {error}")
            raise

    def _on_initial_polling_complete(self, task: asyncio.Task):
        """Handle completion of the initial polling task"""
        try:
            task.result()
        except asyncio.CancelledError:
            print("?? Initial polling task cancelled")
        except Exception as error:
            print(f"? Initial polling task failed: {error}")
        else:
            print("?? Initial polling task finished")

    async def _poll_all_pending_orders(self) -> int:
        """Poll pending orders for all enabled accounts"""
        config_loader = self._get_config_loader()
        accounts = config_loader.get_enabled_accounts()

        if not accounts:
            print("?? No enabled accounts found for order polling")
            return 0

        print(f"?? Polling pending orders for {len(accounts)} accounts...")

        processed_accounts = 0
        for account in accounts:
            try:
                matched_orders = await self._process_pending_orders_for_account(account.name)
                processed_accounts += 1
                if matched_orders:
                    print(f"? {account.name}: {len(matched_orders)} pending orders matched with open orders")
            except Exception as error:
                print(f"? Failed to poll pending orders for account {account.name}: {error}")

        return processed_accounts

    async def _process_pending_orders_for_account(self, account_name: str) -> List[Dict[str, Any]]:
        """Process pending orders for a single account"""
        delta_manager = self._get_delta_manager()
        query = DeltaRecordQuery(
            account_id=account_name,
            record_type=DeltaRecordType.ORDER
        )
        pending_records = await delta_manager.query_records(query)

        if not pending_records:
            print(f"?? {account_name}: No pending order records found")
            return []

        print(f"?? {account_name}: Found {len(pending_records)} pending order records")

        client = get_trading_client()
        try:
            open_orders = await client.get_open_orders(
                account_name,
                currency="BTC",
                kind="option",
                order_type="limit"
            )
        finally:
            await client.close()

        matched_orders: List[Dict[str, Any]] = []
        unmatched_records: List[str] = []

        order_map = {order.get("order_id"): order for order in open_orders if order.get("order_id")}

        for record in pending_records:
            order_id = record.order_id
            if not order_id:
                continue

            matched = order_map.get(order_id)
            if matched:
                matched_orders.append(
                    {
                        "order_id": matched.get("order_id"),
                        "instrument_name": matched.get("instrument_name"),
                        "direction": matched.get("direction"),
                        "amount": matched.get("amount"),
                        "price": matched.get("price"),
                        "record_id": record.id,
                    }
                )
            else:
                unmatched_records.append(order_id)

        if unmatched_records:
            print(f"? {account_name}: {len(unmatched_records)} pending order records had no matching open order IDs")

        return matched_orders
    async def _poll_all_accounts(self) -> int:
        """Poll positions for all enabled accounts"""
        config_loader = self._get_config_loader()
        accounts = config_loader.get_enabled_accounts()

        if not accounts:
            print("?? No enabled accounts found for polling")
            return 0

        print(f"?? Polling {len(accounts)} accounts...")

        processed_accounts = 0
        # Poll each account
        for account in accounts:
            try:
                await self._poll_account(account.name)
                processed_accounts += 1
            except Exception as error:
                print(f"? Failed to poll account {account.name}: {error}")
                # Continue with other accounts
                continue

        return processed_accounts

    async def _poll_account(self, account_name: str):
        """Poll positions for a single account"""
        try:
            # Get client
            client = get_trading_client()

            try:
                # Get positions across supported base currencies (Tiger uses USD by default)
                positions: List[Dict[str, Any]] = await client.get_positions(account_name)
                # for base_currency in self.OPTION_BASE_CURRENCIES:
                #     try:
                #         currency_positions = await client.get_positions(account_name, base_currency)
                #     except Exception as currency_error:
                #         print(f"? {account_name}: Failed to load positions for {base_currency}: {currency_error}")
                #         continue
                #     if currency_positions:
                #         positions.extend(currency_positions)

                # summary = await client.get_account_summary(account_name, "USD")

                # Process positions
                await self._process_positions(account_name, positions)
            except Exception as error:
                print(f"_poll_account get_positions error: {error}")
            finally:
                await client.close()

        except Exception as error:
            print(f"❌ Error polling account {account_name}: {error}")
            raise

    async def _process_positions(
        self,
        account_name: str,
        positions: List[Dict[str, Any]]
    ):
        """Process polled positions"""
        delta_manager = self._get_delta_manager()
        config_loader = self._get_config_loader()
        wechat_service = self._get_wechat_service()
        roi_threshold = 0.85
        option_positions: List[Dict[str, Any]] = []
        # total_delta = 0.0
        action_client: Optional[Any] = None
        trading_client = get_trading_client()

        try:
            # Aggregate option positions and total delta
            for position in positions:
                if position.get("kind") != "option":
                    continue

                # delta_value = float(position.get("delta") or 0.0)
                # size_value = float(position.get("size") or 0.0)
                # total_delta += delta_value * size_value
                option_positions.append(position)

            if option_positions:
                print(f"?? {account_name}: {len(option_positions)} option positions")
            else:
                return

            adjustment_count = 0
            high_roi_count = 0

            async def ensure_action_client():
                nonlocal action_client
                if action_client is None:
                    action_client = get_trading_client()
                return action_client

            for position in option_positions:
                instrument_name = position.get("instrument_name")
                if not instrument_name:
                    continue

                try:
                    size = float(position.get("size") or 0.0)
                    # delta_value = float(position.get("delta") or 0.0)
                    # position_delta_per_unit = (delta_value / size) if size else 0.0

                    # latest_record = await self._ensure_position_record(
                    #     delta_manager=delta_manager,
                    #     account_name=account_name,
                    #     instrument_name=instrument_name,
                    #     observed_delta=position_delta_per_unit
                    # )

                    position_query = DeltaRecordQuery(
                        account_id=account_name,
                        instrument_name=instrument_name,
                        record_type=DeltaRecordType.POSITION
                    )
                    records = await delta_manager.query_records(position_query, limit=1)
                    latest_record = records[0] if records else None
                    if latest_record is None:
                        continue;
                    
                    greeks = await trading_client._calc_option_greeks_by_instrument(instrument_name)
                    if greeks is None or greeks.get('delta') is None:
                        print(f"?? {account_name}: 无法获取希腊值 - {instrument_name}")
                        await asyncio.sleep(5)
                        continue

                    position['delta'] = greeks.get('delta')

                    if latest_record is not None:
                        threshold_abs = abs(latest_record.target_delta or 0.0)
                        position_delta_abs = abs(greeks.get('delta'))

                        if (
                            latest_record.min_expire_days is not None
                            and position_delta_abs > threshold_abs
                        ):
                            print(
                                f"?? {account_name}: Delta threshold exceeded for {instrument_name} "
                                f"(|{greeks.get('delta'):.4f}| > {threshold_abs:.4f})"
                            )
                            client = await ensure_action_client()
                            adjustment_success = await self._trigger_position_adjustment(
                                account_name=account_name,
                                position_data=position,
                                delta_record=latest_record,
                                action_client=client,
                                config_loader=config_loader,
                                delta_manager=delta_manager,
                                wechat_service=wechat_service
                            )
                            if adjustment_success:
                                adjustment_count += 1

                    average_price = position.get("average_price")
                    mark_price = position.get("mark_price")
                    direction = position.get("direction")

                    if (
                        direction == "sell"
                        and average_price not in (None, 0)
                        and mark_price is not None
                    ):
                        roi_value = -((mark_price - average_price) / average_price)
                        if roi_value > roi_threshold:
                            print(
                                f"?? {account_name}: ROI threshold exceeded for {instrument_name} "
                                f"({roi_value * 100:.2f}% > {roi_threshold * 100:.0f}%)"
                            )
                            client = await ensure_action_client()
                            close_success = await self._close_high_roi_position(
                                account_name=account_name,
                                position_data=position,
                                roi=roi_value,
                                roi_threshold=roi_threshold,
                                action_client=client,
                                config_loader=config_loader,
                                delta_manager=delta_manager,
                                wechat_service=wechat_service,
                                delta_record=latest_record
                            )
                            if close_success:
                                high_roi_count += 1

                except Exception as position_error:
                    print(f"?? {account_name}: Failed to process position {instrument_name or 'unknown'}: {position_error}")

                # 添加延迟，避免并发调用API过多
                await asyncio.sleep(5)

            if adjustment_count or high_roi_count:
                print(
                    f"?? {account_name}: adjustments triggered={adjustment_count}, "
                    f"high ROI closes={high_roi_count}"
                )

        except Exception as error:
            print(f"? Error processing positions for {account_name}: {error}")

        finally:
            if action_client:
                await action_client.close()

    async def _ensure_position_record(
        self,
        delta_manager,
        account_name: str,
        instrument_name: str,
        observed_delta: float
    ) -> Optional[DeltaRecord]:
        """Ensure delta record exists for the given instrument."""
        position_query = DeltaRecordQuery(
            account_id=account_name,
            instrument_name=instrument_name,
            record_type=DeltaRecordType.POSITION
        )
        position_records = await delta_manager.query_records(position_query, limit=1)
        if position_records:
            return position_records[0]

        order_query = DeltaRecordQuery(
            account_id=account_name,
            instrument_name=instrument_name,
            record_type=DeltaRecordType.ORDER
        )
        order_records = await delta_manager.query_records(order_query, limit=1)
        source_record = order_records[0] if order_records else None

        if source_record:
            create_input = CreateDeltaRecordInput(
                account_id=source_record.account_id,
                instrument_name=source_record.instrument_name,
                order_id=None,
                target_delta=source_record.target_delta,
                move_position_delta=source_record.move_position_delta,
                min_expire_days=source_record.min_expire_days,
                tv_id=source_record.tv_id,
                action=source_record.action,
                record_type=DeltaRecordType.POSITION
            )
        else:
            create_input = CreateDeltaRecordInput(
                account_id=account_name,
                instrument_name=instrument_name,
                order_id=None,
                target_delta=observed_delta,
                move_position_delta=observed_delta,
                min_expire_days=None,
                tv_id=None,
                action=None,
                record_type=DeltaRecordType.POSITION
            )

        try:
            new_record = await delta_manager.create_record(create_input)
            if source_record:
                print(f"? {account_name}: Created position delta record from order for {instrument_name} (ID: {new_record.id})")
            else:
                print(f"?? {account_name}: Created inferred delta record for {instrument_name} (ID: {new_record.id})")
            return new_record
        except Exception as error:
            print(f"? {account_name}: Failed to sync delta record for {instrument_name}: {error}")
            fallback_records = await delta_manager.query_records(position_query, limit=1)
            return fallback_records[0] if fallback_records else None

    async def _trigger_position_adjustment(
        self,
        account_name: str,
        position_data: Dict[str, Any],
        delta_record: DeltaRecord,
        action_client,
        config_loader: ConfigLoader,
        delta_manager,
        wechat_service: WeChatNotificationService
    ) -> bool:
        request_id = f"adjust_{account_name}_{int(datetime.now().timestamp() * 1000)}"
        try:
            position_obj = DeribitPosition.model_validate(position_data)
        except ValidationError as error:
            print(f"? {account_name}: Position validation failed for adjustment: {error}")
            return False

        position_delta = float(position_data.get("delta") or 0.0)
        # size = float(position_data.get("size") or 0.0)
        # per_unit_delta = (position_delta / size) if size else 0.0

        # Calculate delta per unit for better readability
        # size = float(position_data.get("size") or 0.0)
        # per_unit_delta = (position_delta / size) if size else 0.0

        notification = (
            f"⚠️ **Delta调整触发**\n\n"
            f"📊 **持仓信息**\n"
            f"• 账户: {account_name}\n"
            f"• 合约: {position_obj.instrument_name}\n"
            f"• 持仓数量: {position_obj.size}\n"
            f"• 当前Delta: {position_delta:.4f}\n"
            f"🎯 **调整目标**\n"
            f"• 目标Delta(2): {(delta_record.target_delta or 0.0):.4f}\n"
            f"• 移仓Delta(1): {(delta_record.move_position_delta or 0.0):.4f}\n"
            f"• 记录ID: {delta_record.id or 'N/A'}"
        )
        await wechat_service.send_custom_markdown(account_name, notification)

        try:
            result = await execute_position_adjustment(
                request_id=request_id,
                account_name=account_name,
                current_position=position_data,
                delta_record=delta_record,
                services={
                    "config_loader": config_loader,
                    "delta_manager": delta_manager,
                    "deribit_client": action_client
                }
            )
        except Exception as error:
            print(f"? {account_name}: Adjustment failed for {position_obj.instrument_name}: {error}")
            await wechat_service.send_custom_markdown(
                account_name,
                "?? **Delta adjustment failed**\n"
                f"- Instrument: {position_obj.instrument_name}\n"
                f"- Error: {error}"
            )
            return False

        status_icon = "??" if result.success else "??"
        result_lines = [
            f"{status_icon} **Delta adjustment result**",
            f"- Instrument: {position_obj.instrument_name}"
        ]
        if result.new_instrument:
            result_lines.append(f"- New instrument: {result.new_instrument}")
        if result.message:
            result_lines.append(f"- Message: {result.message}")
        if result.error:
            result_lines.append(f"- Error: {result.error}")
        await wechat_service.send_custom_markdown(account_name, "\n".join(result_lines))

        print(
            f"?? {account_name}: Delta adjustment {'success' if result.success else 'failed'} for {position_obj.instrument_name}"
        )
        return result.success

    async def _close_high_roi_position(
        self,
        account_name: str,
        position_data: Dict[str, Any],
        roi: float,
        roi_threshold: float,
        action_client,
        config_loader: ConfigLoader,
        delta_manager,
        wechat_service: WeChatNotificationService,
        delta_record: Optional[DeltaRecord]
    ) -> bool:
        request_id = f"roi_{account_name}_{int(datetime.now().timestamp() * 1000)}"
        try:
            position_obj = DeribitPosition.model_validate(position_data)
        except ValidationError as error:
            print(f"? {account_name}: Position validation failed for ROI close: {error}")
            return False

        pre_lines = [
            "?? **ROI close trigger**",
            f"- Account: {account_name}",
            f"- Instrument: {position_obj.instrument_name}",
            f"- Direction: {position_obj.direction}",
            f"- Position size: {position_obj.size}",
            f"- ROI: {roi * 100:.2f}% (threshold {roi_threshold * 100:.0f}%)"
        ]
        if delta_record and delta_record.id:
            pre_lines.append(f"- Record ID: {delta_record.id}")
        await wechat_service.send_custom_markdown(account_name, "\n".join(pre_lines))

        try:
            close_result = await execute_position_close(
                request_id=request_id,
                account_name=account_name,
                current_position=position_obj,
                delta_record=None,
                close_ratio=1.0,
                is_market_order=False,
                services={
                    "config_loader": config_loader,
                    "delta_manager": delta_manager,
                    "deribit_client": action_client
                }
            )
        except Exception as error:
            print(f"? {account_name}: ROI close failed for {position_obj.instrument_name}: {error}")
            await wechat_service.send_custom_markdown(
                account_name,
                "?? **ROI close failed**\n"
                f"- Instrument: {position_obj.instrument_name}\n"
                f"- Error: {error}"
            )
            return False

        success = bool(close_result.get("success"))
        result_lines = [
            ("??" if success else "??") + " **ROI close result**",
            f"- Instrument: {position_obj.instrument_name}",
            f"- ROI: {roi * 100:.2f}%"
        ]
        if not success and close_result.get("error"):
            result_lines.append(f"- Error: {close_result['error']}")
        await wechat_service.send_custom_markdown(account_name, "\n".join(result_lines))

        print(
            f"?? {account_name}: ROI close {'success' if success else 'failed'} for {position_obj.instrument_name}"
        )
        return success

    async def poll_once(self) -> Dict[str, Any]:
        """Perform a single poll of all accounts"""
        try:
            start_time = datetime.now()
            position_accounts = await self._poll_all_accounts()
            order_accounts = await self._poll_all_pending_orders()

            end_time = datetime.now()

            return {
                "success": True,
                "message": "Manual poll completed successfully",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds(),
                "position_accounts_polled": position_accounts,
                "order_accounts_polled": order_accounts
            }

        except Exception as error:
            return {
                "success": False,
                "message": f"Manual poll failed: {str(error)}",
                "error": str(error)
            }

    def get_status(self) -> dict:
        """Get polling status"""
        config_loader = self._get_config_loader()
        accounts = config_loader.get_enabled_accounts()

        return {
            # Main status
            "is_running": self.is_running,
            "auto_start": settings.auto_start_polling,
            "enabled_accounts": len(accounts),
            "account_names": [acc.name for acc in accounts],
            "mock_mode": settings.use_mock_mode,

            # Position polling status
            "position_polling": {
                "interval_minutes": settings.position_polling_interval_minutes,
                "error_count": self.position_error_count,
                "last_poll_time": self.last_position_poll_time.isoformat() if self.last_position_poll_time else None,
                "poll_count": self.position_poll_count,
            },

            # Order polling status (future enhancement)
            "order_polling": {
                "enabled": self.order_polling_enabled,
                "interval_minutes": settings.order_polling_interval_minutes,
                "error_count": self.order_error_count,
                "last_poll_time": self.last_order_poll_time.isoformat() if self.last_order_poll_time else None,
                "poll_count": self.order_poll_count,
            },

            # Backward compatibility fields
            "interval_seconds": settings.position_polling_interval_minutes * 60,
            "interval_minutes": settings.position_polling_interval_minutes,
            "position_polling_interval_minutes": settings.position_polling_interval_minutes,
            "order_polling_interval_minutes": settings.order_polling_interval_minutes,
            "error_count": self.position_error_count,  # Alias for position errors
            "max_errors": settings.max_polling_errors,
            "last_poll_time": self.last_position_poll_time.isoformat() if self.last_position_poll_time else None,
            "poll_count": self.position_poll_count,  # Alias for position poll count
        }

# Global instance
polling_manager = PollingManager()

