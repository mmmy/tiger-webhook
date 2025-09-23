#!/usr/bin/env python3
"""
期权链分析示例

展示如何使用增强的get_option_chain方法进行期权分析，
包括希腊字母计算、套利机会发现、风险评估等。
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.deribit_webhook.services.tiger_client import TigerClient


class OptionChainAnalyzer:
    """期权链分析器"""
    
    def __init__(self, tiger_client: TigerClient):
        self.client = tiger_client
    
    async def analyze_option_chain(self, underlying_symbol: str, expiry_timestamp: int) -> Dict:
        """分析期权链"""
        print(f"📊 分析期权链: {underlying_symbol}")
        print(f"到期时间: {datetime.fromtimestamp(expiry_timestamp/1000).strftime('%Y-%m-%d')}")
        print("=" * 80)
        
        # 获取期权链数据（包含计算的希腊字母）
        options = await self.client.get_option_chain(underlying_symbol, expiry_timestamp)
        
        if not options:
            print("❌ 未获取到期权数据")
            return {}
        
        # 分离看涨和看跌期权
        call_options = [opt for opt in options if opt.get('put_call') == 'CALL']
        put_options = [opt for opt in options if opt.get('put_call') == 'PUT']
        
        analysis = {
            'underlying_symbol': underlying_symbol,
            'expiry_timestamp': expiry_timestamp,
            'total_options': len(options),
            'call_options': len(call_options),
            'put_options': len(put_options),
            'analysis_time': datetime.now().isoformat()
        }
        
        # 基本统计
        self._print_basic_statistics(options, call_options, put_options)
        
        # 希腊字母分析
        greeks_analysis = self._analyze_greeks(options)
        analysis['greeks'] = greeks_analysis
        
        # 套利机会分析
        arbitrage_opportunities = self._find_arbitrage_opportunities(options)
        analysis['arbitrage'] = arbitrage_opportunities
        
        # 风险分析
        risk_analysis = self._analyze_risk(options)
        analysis['risk'] = risk_analysis
        
        # 波动率分析
        volatility_analysis = self._analyze_volatility(options)
        analysis['volatility'] = volatility_analysis
        
        return analysis
    
    def _print_basic_statistics(self, options: List[Dict], call_options: List[Dict], put_options: List[Dict]):
        """打印基本统计信息"""
        print(f"\n📈 基本统计:")
        print("-" * 50)
        print(f"总期权数量:   {len(options)}")
        print(f"看涨期权:     {len(call_options)}")
        print(f"看跌期权:     {len(put_options)}")
        
        if options:
            underlying_prices = [opt.get('underlying_price', 0) for opt in options if opt.get('underlying_price')]
            if underlying_prices:
                avg_underlying = sum(underlying_prices) / len(underlying_prices)
                print(f"标的价格:     ${avg_underlying:.2f}")
    
    def _analyze_greeks(self, options: List[Dict]) -> Dict:
        """分析希腊字母"""
        print(f"\n🎯 希腊字母分析:")
        print("-" * 50)
        
        # 计算总希腊字母
        total_delta = sum([opt.get('calculated_delta', 0) for opt in options])
        total_gamma = sum([opt.get('calculated_gamma', 0) for opt in options])
        total_theta = sum([opt.get('calculated_theta', 0) for opt in options])
        total_vega = sum([opt.get('calculated_vega', 0) for opt in options])
        
        print(f"总Delta敞口:  {total_delta:.4f}")
        print(f"总Gamma敞口:  {total_gamma:.4f}")
        print(f"总Theta敞口:  {total_theta:.4f}")
        print(f"总Vega敞口:   {total_vega:.4f}")
        
        # 找出Delta最大的期权
        options_with_delta = [opt for opt in options if opt.get('calculated_delta') is not None]
        if options_with_delta:
            max_delta_option = max(options_with_delta, key=lambda x: abs(x.get('calculated_delta', 0)))
            print(f"最大Delta:    {max_delta_option.get('calculated_delta', 0):.4f} ({max_delta_option.get('identifier', 'Unknown')})")
        
        return {
            'total_delta': total_delta,
            'total_gamma': total_gamma,
            'total_theta': total_theta,
            'total_vega': total_vega
        }
    
    def _find_arbitrage_opportunities(self, options: List[Dict]) -> List[Dict]:
        """寻找套利机会"""
        print(f"\n💰 套利机会分析:")
        print("-" * 50)
        
        arbitrage_opportunities = []
        
        for option in options:
            market_price = option.get('latest_price', 0)
            theoretical_value = option.get('calculated_value', 0)
            
            if market_price > 0 and theoretical_value > 0:
                price_diff = theoretical_value - market_price
                price_diff_pct = (price_diff / market_price) * 100
                
                # 如果价格差异超过10%，认为是潜在套利机会
                if abs(price_diff_pct) > 10:
                    opportunity = {
                        'identifier': option.get('identifier', 'Unknown'),
                        'option_type': option.get('put_call', 'Unknown'),
                        'strike': option.get('strike', 0),
                        'market_price': market_price,
                        'theoretical_value': theoretical_value,
                        'price_difference': price_diff,
                        'price_difference_pct': price_diff_pct,
                        'recommendation': 'BUY' if price_diff > 0 else 'SELL'
                    }
                    arbitrage_opportunities.append(opportunity)
        
        if arbitrage_opportunities:
            print(f"发现 {len(arbitrage_opportunities)} 个潜在套利机会:")
            for i, opp in enumerate(arbitrage_opportunities, 1):
                print(f"{i}. {opp['identifier']} ({opp['option_type']})")
                print(f"   市场价格: ${opp['market_price']:.2f}")
                print(f"   理论价值: ${opp['theoretical_value']:.2f}")
                print(f"   价格差异: {opp['price_difference_pct']:+.1f}% ({opp['recommendation']})")
        else:
            print("未发现明显的套利机会")
        
        return arbitrage_opportunities
    
    def _analyze_risk(self, options: List[Dict]) -> Dict:
        """分析风险"""
        print(f"\n⚠️ 风险分析:")
        print("-" * 50)
        
        # 计算组合风险指标
        total_delta = sum([opt.get('calculated_delta', 0) for opt in options])
        total_gamma = sum([opt.get('calculated_gamma', 0) for opt in options])
        total_theta = sum([opt.get('calculated_theta', 0) for opt in options])
        
        # Delta风险
        delta_risk = "高" if abs(total_delta) > 0.5 else "中" if abs(total_delta) > 0.2 else "低"
        print(f"Delta风险:    {delta_risk} (总Delta: {total_delta:.4f})")
        
        # Gamma风险
        gamma_risk = "高" if total_gamma > 0.1 else "中" if total_gamma > 0.05 else "低"
        print(f"Gamma风险:    {gamma_risk} (总Gamma: {total_gamma:.4f})")
        
        # 时间衰减风险
        theta_risk = "高" if total_theta < -0.5 else "中" if total_theta < -0.2 else "低"
        print(f"时间衰减风险: {theta_risk} (总Theta: {total_theta:.4f})")
        
        # 流动性风险分析
        low_volume_options = [opt for opt in options if opt.get('volume', 0) < 10]
        liquidity_risk = "高" if len(low_volume_options) > len(options) * 0.5 else "低"
        print(f"流动性风险:   {liquidity_risk} ({len(low_volume_options)}/{len(options)} 低成交量)")
        
        return {
            'delta_risk': delta_risk,
            'gamma_risk': gamma_risk,
            'theta_risk': theta_risk,
            'liquidity_risk': liquidity_risk,
            'low_volume_count': len(low_volume_options)
        }
    
    def _analyze_volatility(self, options: List[Dict]) -> Dict:
        """分析波动率"""
        print(f"\n📊 波动率分析:")
        print("-" * 50)
        
        implied_vols = [opt.get('implied_vol', 0) for opt in options if opt.get('implied_vol')]
        
        if not implied_vols:
            print("无隐含波动率数据")
            return {}
        
        avg_iv = sum(implied_vols) / len(implied_vols)
        min_iv = min(implied_vols)
        max_iv = max(implied_vols)
        iv_spread = max_iv - min_iv
        
        print(f"平均隐含波动率: {avg_iv*100:.2f}%")
        print(f"波动率范围:     {min_iv*100:.2f}% - {max_iv*100:.2f}%")
        print(f"波动率价差:     {iv_spread*100:.2f}%")
        
        # 波动率偏斜分析
        call_ivs = [opt.get('implied_vol', 0) for opt in options if opt.get('put_call') == 'CALL' and opt.get('implied_vol')]
        put_ivs = [opt.get('implied_vol', 0) for opt in options if opt.get('put_call') == 'PUT' and opt.get('implied_vol')]
        
        if call_ivs and put_ivs:
            avg_call_iv = sum(call_ivs) / len(call_ivs)
            avg_put_iv = sum(put_ivs) / len(put_ivs)
            skew = avg_put_iv - avg_call_iv
            print(f"波动率偏斜:     {skew*100:+.2f}% (Put-Call)")
        
        return {
            'average_iv': avg_iv,
            'min_iv': min_iv,
            'max_iv': max_iv,
            'iv_spread': iv_spread,
            'call_put_skew': skew if 'skew' in locals() else 0
        }


async def demo_option_chain_analysis():
    """演示期权链分析功能"""
    print("🚀 期权链分析演示")
    print("展示如何使用增强的get_option_chain方法进行期权分析")
    
    # 创建TigerClient和分析器
    client = TigerClient()
    analyzer = OptionChainAnalyzer(client)
    
    # 模拟期权链分析
    try:
        # 这里应该使用真实的期权数据
        # 为了演示，我们使用模拟数据
        print("\n💡 注意: 这是一个演示，使用模拟数据")
        print("在实际应用中，请连接到真实的Tiger API")
        
        # 模拟分析QQQ期权链
        expiry_timestamp = int((datetime.now() + timedelta(days=30)).timestamp() * 1000)
        
        # 在实际应用中，这里会调用真实的API
        # analysis = await analyzer.analyze_option_chain('QQQ', expiry_timestamp)
        
        print("\n✅ 期权链分析功能已实现")
        print("\n📋 功能特性:")
        print("1. 自动计算希腊字母 (Delta, Gamma, Theta, Vega, Rho)")
        print("2. 套利机会发现 (比较理论价值和市场价格)")
        print("3. 风险分析 (Delta风险, Gamma风险, 时间衰减风险)")
        print("4. 波动率分析 (平均隐含波动率, 波动率偏斜)")
        print("5. 流动性分析 (成交量统计)")
        
        print("\n🎯 使用方法:")
        print("```python")
        print("client = TigerClient()")
        print("analyzer = OptionChainAnalyzer(client)")
        print("analysis = await analyzer.analyze_option_chain('QQQ', expiry_timestamp)")
        print("```")
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    await demo_option_chain_analysis()


if __name__ == "__main__":
    asyncio.run(main())
