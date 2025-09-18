"""
WeChat bot notification service

Handles sending notifications to WeChat groups via webhook.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from config import ConfigLoader, settings
from models.config_types import WeChatBotConfig
from models.trading_types import OptionTradingResult


class WeChatNotificationService:
    """WeChat notification service"""
    
    def __init__(self):
        self._config_loader: Optional[ConfigLoader] = None
    
    def _get_config_loader(self) -> ConfigLoader:
        """Get config loader instance"""
        if self._config_loader is None:
            self._config_loader = ConfigLoader.get_instance()
        return self._config_loader
    
    async def send_trading_notification(
        self,
        account_name: str,
        trading_result: OptionTradingResult,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send trading notification to WeChat
        
        Args:
            account_name: Account name
            trading_result: Trading result
            additional_info: Additional information to include
            
        Returns:
            True if notification sent successfully
        """
        try:
            config_loader = self._get_config_loader()
            wechat_config = config_loader.get_account_wechat_bot_config(account_name)
            
            if not wechat_config:
                print(f"⚠️ No WeChat bot configuration found for account: {account_name}")
                return False
            
            # Create notification message
            message = self._create_trading_message(account_name, trading_result, additional_info)
            
            # Send notification
            success = await self._send_message(wechat_config, message)
            
            if success:
                print(f"✅ WeChat notification sent for account: {account_name}")
            else:
                print(f"❌ Failed to send WeChat notification for account: {account_name}")
            
            return success
            
        except Exception as error:
            print(f"❌ Error sending WeChat notification: {error}")
            return False
    
    async def send_system_notification(
        self,
        message: str,
        account_names: Optional[List[str]] = None,
        notification_type: str = "system"
    ) -> Dict[str, bool]:
        """
        Send system notification to multiple accounts
        
        Args:
            message: Notification message
            account_names: List of account names (if None, send to all enabled accounts)
            notification_type: Type of notification
            
        Returns:
            Dictionary mapping account names to success status
        """
        results = {}
        
        try:
            config_loader = self._get_config_loader()
            
            if account_names is None:
                # Get all enabled accounts with WeChat bot configuration
                wechat_configs = config_loader.get_all_wechat_bot_configs()
                account_names = [config["account_name"] for config in wechat_configs]
            
            # Send to each account
            for account_name in account_names:
                try:
                    wechat_config = config_loader.get_account_wechat_bot_config(account_name)
                    
                    if not wechat_config:
                        results[account_name] = False
                        continue
                    
                    # Create system message
                    formatted_message = self._create_system_message(message, notification_type)
                    
                    # Send notification
                    success = await self._send_message(wechat_config, formatted_message)
                    results[account_name] = success
                    
                except Exception as error:
                    print(f"❌ Error sending system notification to {account_name}: {error}")
                    results[account_name] = False
            
            return results
            
        except Exception as error:
            print(f"❌ Error sending system notifications: {error}")
            return {}
    
    def _create_trading_message(
        self,
        account_name: str,
        trading_result: OptionTradingResult,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create trading notification message"""
        # Determine message color based on success
        color = "info" if trading_result.success else "warning"
        
        # Create message content
        content_lines = [
            f"**交易通知 - {account_name}**",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"状态: {'✅ 成功' if trading_result.success else '❌ 失败'}",
            f"消息: {trading_result.message}"
        ]
        
        if trading_result.success:
            if trading_result.order_id:
                content_lines.append(f"订单ID: {trading_result.order_id}")
            if trading_result.instrument_name:
                content_lines.append(f"合约: {trading_result.instrument_name}")
            if trading_result.executed_quantity:
                content_lines.append(f"数量: {trading_result.executed_quantity}")
            if trading_result.executed_price:
                content_lines.append(f"价格: {trading_result.executed_price}")
        else:
            if trading_result.error:
                content_lines.append(f"错误: {trading_result.error}")
        
        # Add additional info if provided
        if additional_info:
            content_lines.append("---")
            for key, value in additional_info.items():
                content_lines.append(f"{key}: {value}")
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": "\n".join(content_lines)
            }
        }
    
    def _create_system_message(self, message: str, notification_type: str = "system") -> Dict[str, Any]:
        """Create system notification message"""
        # Determine emoji based on type
        emoji_map = {
            "system": "🔔",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }
        
        emoji = emoji_map.get(notification_type, "🔔")
        
        content = f"{emoji} **系统通知**\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{message}"
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
    
    async def _send_message(self, config: WeChatBotConfig, message: Dict[str, Any]) -> bool:
        """
        Send message to WeChat webhook
        
        Args:
            config: WeChat bot configuration
            message: Message payload
            
        Returns:
            True if sent successfully
        """
        for attempt in range(config.retry_count):
            try:
                async with httpx.AsyncClient(timeout=config.timeout / 1000) as client:
                    response = await client.post(
                        config.webhook_url,
                        json=message,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get("errcode") == 0:
                            return True
                        else:
                            print(f"❌ WeChat API error: {response_data}")
                    else:
                        print(f"❌ WeChat webhook HTTP error: {response.status_code}")
                
            except Exception as error:
                print(f"❌ WeChat notification attempt {attempt + 1} failed: {error}")
                
                # Wait before retry (except for last attempt)
                if attempt < config.retry_count - 1:
                    await asyncio.sleep(config.retry_delay / 1000)
        
        return False
    
    async def test_notification(self, account_name: str) -> bool:
        """
        Send test notification
        
        Args:
            account_name: Account name to test
            
        Returns:
            True if test successful
        """
        try:
            config_loader = self._get_config_loader()
            wechat_config = config_loader.get_account_wechat_bot_config(account_name)
            
            if not wechat_config:
                print(f"❌ No WeChat bot configuration found for account: {account_name}")
                return False
            
            # Create test message
            test_message = self._create_system_message(
                f"WeChat机器人测试消息\n账户: {account_name}\n配置正常，连接成功！",
                "info"
            )
            
            # Send test message
            success = await self._send_message(wechat_config, test_message)
            
            if success:
                print(f"✅ WeChat test notification sent successfully for account: {account_name}")
            else:
                print(f"❌ WeChat test notification failed for account: {account_name}")
            
            return success
            
        except Exception as error:
            print(f"❌ Error sending WeChat test notification: {error}")
            return False


# Global instance
wechat_notification_service = WeChatNotificationService()
