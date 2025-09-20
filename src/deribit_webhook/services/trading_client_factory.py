"""
Tiger Brokers交易客户端工厂

简化的客户端工厂，只支持Tiger Brokers
"""

from ..config.config_loader import ConfigLoader
from .tiger_client import TigerClient


class TradingClientFactory:
    """Tiger Brokers交易客户端工厂"""

    @staticmethod
    def create_client() -> TigerClient:
        """创建Tiger Brokers交易客户端"""
        print("🐅 Using Tiger Brokers client")
        return TigerClient()

    @staticmethod
    def get_broker_type() -> str:
        """获取broker类型"""
        return 'tiger'


# 为了保持向后兼容，创建一个统一的客户端接口
def get_trading_client() -> TigerClient:
    """获取交易客户端实例"""
    return TradingClientFactory.create_client()


# 全局客户端实例（单例模式）
_client_instance = None

def get_global_trading_client() -> TigerClient:
    """获取全局交易客户端实例（单例）"""
    global _client_instance
    if _client_instance is None:
        _client_instance = TradingClientFactory.create_client()
    return _client_instance


def reset_global_client():
    """重置全局客户端实例（用于测试或配置更改）"""
    global _client_instance
    _client_instance = None
