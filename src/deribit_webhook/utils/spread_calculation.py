"""
盘口价差计算工具函数
统一不同模块中的价差比率计算逻辑

参考 ../deribit_webhook/src/utils/spread-calculation.ts 实现
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


def calculate_spread_ratio(bid_price: float, ask_price: float) -> float:
    """
    计算盘口价差比率
    
    价差比率 = (卖1价 - 买1价) / (卖1价 + 买1价) * 2
    
    这个比率表示价差相对于中间价的比例：
    - 0 表示没有价差（买卖价相等）
    - 接近1表示价差很大（流动性差）
    - 负值表示买价高于卖价（异常情况）
    
    Args:
        bid_price: 买1价（最高买价）
        ask_price: 卖1价（最低卖价）
        
    Returns:
        价差比率，如果价格无效则返回1（表示最大价差）
    """
    # 验证价格有效性
    if not bid_price or not ask_price or bid_price <= 0 or ask_price <= 0:
        return 1.0  # 返回最大价差比率，表示流动性极差
    
    # 检查价格合理性（买价不应高于卖价）
    if bid_price > ask_price:
        print(f"⚠️ Abnormal prices: bid={bid_price} > ask={ask_price}")
        return 1.0  # 异常情况，返回最大价差
    
    # 计算标准化价差比率
    spread_ratio = (ask_price - bid_price) / (ask_price + bid_price) * 2
    
    return spread_ratio


def calculate_absolute_spread(bid_price: float, ask_price: float) -> float:
    """
    计算绝对价差
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        
    Returns:
        绝对价差（卖1价 - 买1价）
    """
    if not bid_price or not ask_price or bid_price <= 0 or ask_price <= 0:
        return 0.0
    
    return max(0.0, ask_price - bid_price)


def calculate_mid_price(bid_price: float, ask_price: float) -> float:
    """
    计算中间价
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        
    Returns:
        中间价 ((买1价 + 卖1价) / 2)
    """
    if not bid_price or not ask_price or bid_price <= 0 or ask_price <= 0:
        return 0.0
    
    return (bid_price + ask_price) / 2


def format_spread_ratio_as_percentage(spread_ratio: float, decimals: int = 2) -> str:
    """
    格式化价差比率为百分比字符串
    
    Args:
        spread_ratio: 价差比率
        decimals: 小数位数，默认2位
        
    Returns:
        格式化的百分比字符串，如 "1.25%"
    """
    return f"{(spread_ratio * 100):.{decimals}f}%"


def calculate_spread_tick_multiple(bid_price: float, ask_price: float, tick_size: float) -> float:
    """
    计算价差步进倍数
    
    步进倍数 = (卖1价 - 买1价) / 价格最小步进
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        tick_size: 价格最小步进
        
    Returns:
        价差步进倍数，如果参数无效则返回float('inf')
    """
    # 验证参数有效性
    if not bid_price or not ask_price or not tick_size or bid_price <= 0 or ask_price <= 0 or tick_size <= 0:
        return float('inf')  # 返回无穷大，表示价差极大
    
    # 检查价格合理性
    if bid_price > ask_price:
        return float('inf')  # 异常情况
    
    absolute_spread = ask_price - bid_price
    return absolute_spread / tick_size


def is_spread_too_wide(bid_price: float, ask_price: float, threshold: float = 0.15) -> bool:
    """
    判断价差是否过大（基于比率阈值）
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        threshold: 价差比率阈值，默认0.15 (15%)
        
    Returns:
        True表示价差过大，False表示价差合理
    """
    spread_ratio = calculate_spread_ratio(bid_price, ask_price)
    return spread_ratio > threshold


def is_spread_too_wide_by_ticks(bid_price: float, ask_price: float, tick_size: float, threshold: int = 2) -> bool:
    """
    判断价差是否过大（基于步进倍数阈值）
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        tick_size: 价格最小步进
        threshold: 步进倍数阈值，默认2
        
    Returns:
        True表示价差过大，False表示价差合理
    """
    tick_multiple = calculate_spread_tick_multiple(bid_price, ask_price, tick_size)
    return tick_multiple > threshold


def is_spread_reasonable(
    bid_price: float,
    ask_price: float,
    tick_size: float,
    ratio_threshold: float = 0.15,
    tick_threshold: int = 2
) -> bool:
    """
    综合判断价差是否合理（满足任一条件即可）
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        tick_size: 价格最小步进
        ratio_threshold: 价差比率阈值，默认0.15 (15%)
        tick_threshold: 步进倍数阈值，默认2
        
    Returns:
        True表示价差合理，False表示价差过大
    """
    # 满足任一条件即认为价差合理
    ratio_ok = not is_spread_too_wide(bid_price, ask_price, ratio_threshold)
    # tick_ok = not is_spread_too_wide_by_ticks(bid_price, ask_price, tick_size, tick_threshold)
    
    return ratio_ok # or tick_ok


def get_spread_quality_description(bid_price: float, ask_price: float) -> str:
    """
    获取价差质量描述
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        
    Returns:
        价差质量描述字符串
    """
    spread_ratio = calculate_spread_ratio(bid_price, ask_price)
    
    if spread_ratio <= 0.01:
        return '极佳 (≤1%)'
    elif spread_ratio <= 0.05:
        return '良好 (≤5%)'
    elif spread_ratio <= 0.15:
        return '一般 (≤15%)'
    elif spread_ratio <= 0.30:
        return '较差 (≤30%)'
    else:
        return '极差 (>30%)'


@dataclass
class SpreadInfo:
    """价差信息数据类"""
    bid_price: float
    ask_price: float
    absolute_spread: float
    spread_ratio: float
    mid_price: float
    quality_description: str
    formatted_ratio: str
    tick_size: Optional[float] = None
    tick_multiple: Optional[float] = None
    is_reasonable_by_ratio: Optional[bool] = None
    is_reasonable_by_ticks: Optional[bool] = None
    is_reasonable_overall: Optional[bool] = None


def get_spread_info(
    bid_price: float,
    ask_price: float,
    tick_size: Optional[float] = None,
    ratio_threshold: Optional[float] = None,
    tick_threshold: Optional[int] = None
) -> SpreadInfo:
    """
    获取完整的价差信息
    
    Args:
        bid_price: 买1价
        ask_price: 卖1价
        tick_size: 价格最小步进（可选）
        ratio_threshold: 价差比率阈值（可选）
        tick_threshold: 步进倍数阈值（可选）
        
    Returns:
        完整的价差信息对象
    """
    spread_ratio = calculate_spread_ratio(bid_price, ask_price)
    info = SpreadInfo(
        bid_price=bid_price,
        ask_price=ask_price,
        absolute_spread=calculate_absolute_spread(bid_price, ask_price),
        spread_ratio=spread_ratio,
        mid_price=calculate_mid_price(bid_price, ask_price),
        quality_description=get_spread_quality_description(bid_price, ask_price),
        formatted_ratio=format_spread_ratio_as_percentage(spread_ratio)
    )
    
    # 如果提供了tick_size，计算相关信息
    if tick_size is not None and tick_size > 0:
        tick_multiple = calculate_spread_tick_multiple(bid_price, ask_price, tick_size)
        ratio_thresh = ratio_threshold or 0.15
        tick_thresh = tick_threshold or 2
        
        info.tick_size = tick_size
        info.tick_multiple = tick_multiple
        info.is_reasonable_by_ratio = not is_spread_too_wide(bid_price, ask_price, ratio_thresh)
        info.is_reasonable_by_ticks = not is_spread_too_wide_by_ticks(bid_price, ask_price, tick_size, tick_thresh)
        info.is_reasonable_overall = is_spread_reasonable(bid_price, ask_price, tick_size, ratio_thresh, tick_thresh)
    
    return info
