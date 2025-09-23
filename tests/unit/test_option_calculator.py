"""
期权计算器测试模块
"""

import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock

# 模拟QuantLib不可用的情况
def test_option_calculator_without_quantlib():
    """测试没有QuantLib时的错误处理"""
    with patch.dict('sys.modules', {'quantlib': None}):
        with patch('src.deribit_webhook.utils.option_calculator.QUANTLIB_AVAILABLE', False):
            from src.deribit_webhook.utils.option_calculator import OptionCalculator
            
            with pytest.raises(ImportError, match="QuantLib is required"):
                OptionCalculator()


# 如果QuantLib可用，运行完整测试
try:
    import QuantLib as ql
    from src.deribit_webhook.utils.option_calculator import (
        OptionCalculator,
        calculate_option_greeks,
        calculate_implied_volatility
    )
    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not available")
class TestOptionCalculator:
    """期权计算器测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.calculator = OptionCalculator()
        
        # 测试数据 (基于Tiger API文档示例)
        self.test_data = {
            'option_type': 'call',
            'underlying_price': 985.0,
            'strike_price': 990.0,
            'risk_free_rate': 0.017,
            'dividend_rate': 0.0,
            'volatility': 0.6153,
            'settlement_date': '2022-04-14',
            'expiration_date': '2022-04-22',
            'evaluation_date': '2022-04-19'
        }
    
    def test_calculate_greeks_call_option(self):
        """测试看涨期权希腊字母计算"""
        greeks = self.calculator.calculate_greeks(**self.test_data)
        
        # 验证返回的字典包含所有希腊字母
        expected_keys = ['value', 'delta', 'gamma', 'theta', 'vega', 'rho']
        assert all(key in greeks for key in expected_keys)
        
        # 验证数值合理性
        assert greeks['value'] > 0  # 看涨期权价值应为正
        assert 0 < greeks['delta'] < 1  # Call期权Delta应在0-1之间
        assert greeks['gamma'] > 0  # Gamma应为正
        assert greeks['theta'] < 0  # Theta通常为负(时间衰减)
        assert greeks['vega'] >= 0  # Vega应为非负(某些方法可能返回0)
        
        print(f"Call Option Greeks: {greeks}")
    
    def test_calculate_greeks_put_option(self):
        """测试看跌期权希腊字母计算"""
        put_data = self.test_data.copy()
        put_data['option_type'] = 'put'
        
        greeks = self.calculator.calculate_greeks(**put_data)
        
        # 验证返回的字典包含所有希腊字母
        expected_keys = ['value', 'delta', 'gamma', 'theta', 'vega', 'rho']
        assert all(key in greeks for key in expected_keys)
        
        # 验证数值合理性
        assert greeks['value'] > 0  # 看跌期权价值应为正
        assert -1 < greeks['delta'] < 0  # Put期权Delta应在-1到0之间
        assert greeks['gamma'] > 0  # Gamma应为正
        assert greeks['vega'] >= 0  # Vega应为非负(某些方法可能返回0)
        
        print(f"Put Option Greeks: {greeks}")
    
    def test_calculate_greeks_european_style(self):
        """测试欧式期权计算"""
        european_data = self.test_data.copy()
        european_data['option_style'] = 'european'
        
        greeks = self.calculator.calculate_greeks(**european_data)
        
        # 验证返回的字典包含所有希腊字母
        expected_keys = ['value', 'delta', 'gamma', 'theta', 'vega', 'rho']
        assert all(key in greeks for key in expected_keys)
        
        print(f"European Option Greeks: {greeks}")
    
    def test_calculate_implied_volatility(self):
        """测试隐含波动率计算"""
        # 使用Tiger API文档中的示例数据
        iv_data = {
            'option_type': 'call',
            'underlying_price': 985.0,
            'strike_price': 990.0,
            'risk_free_rate': 0.017,
            'dividend_rate': 0.0,
            'option_price': 33.6148,  # 期权市场价格
            'settlement_date': '2022-04-14',
            'expiration_date': '2022-04-22',
            'evaluation_date': '2022-04-19'
        }
        
        implied_vol = self.calculator.calculate_implied_volatility(**iv_data)
        
        # 验证隐含波动率合理性
        assert 0.1 < implied_vol < 2.0  # 隐含波动率应在合理范围内
        assert abs(implied_vol - 0.6153) < 0.1  # 应接近预期值
        
        print(f"Implied Volatility: {implied_vol:.4f} ({implied_vol*100:.2f}%)")
    
    def test_date_conversion(self):
        """测试日期转换功能"""
        # 测试不同日期格式
        test_dates = [
            '2022-04-19',
            datetime(2022, 4, 19),
            date(2022, 4, 19)
        ]
        
        for test_date in test_dates:
            ql_date = self.calculator._convert_to_ql_date(test_date)
            assert isinstance(ql_date, ql.Date)
            assert ql_date.dayOfMonth() == 19
            assert ql_date.month() == 4
            assert ql_date.year() == 2022
    
    def test_invalid_inputs(self):
        """测试无效输入的错误处理"""
        invalid_data = self.test_data.copy()
        
        # 测试无效期权类型
        invalid_data['option_type'] = 'invalid'
        with pytest.raises(ValueError):
            self.calculator.calculate_greeks(**invalid_data)
        
        # 测试负的标的价格
        invalid_data = self.test_data.copy()
        invalid_data['underlying_price'] = -100
        with pytest.raises(ValueError):
            self.calculator.calculate_greeks(**invalid_data)
        
        # 测试无效日期格式
        invalid_data = self.test_data.copy()
        invalid_data['settlement_date'] = 'invalid-date'
        with pytest.raises(ValueError):
            self.calculator.calculate_greeks(**invalid_data)
    
    def test_convenience_functions(self):
        """测试便捷函数"""
        # 测试calculate_option_greeks便捷函数
        greeks = calculate_option_greeks(
            option_type='call',
            underlying_price=985,
            strike_price=990,
            risk_free_rate=0.017,
            volatility=0.6153,
            settlement_date='2022-04-14',
            expiration_date='2022-04-22'
        )
        
        assert 'delta' in greeks
        assert 'gamma' in greeks
        
        # 测试calculate_implied_volatility便捷函数
        iv = calculate_implied_volatility(
            option_type='call',
            underlying_price=985,
            strike_price=990,
            risk_free_rate=0.017,
            option_price=33.6148,
            settlement_date='2022-04-14',
            expiration_date='2022-04-22'
        )
        
        assert 0.1 < iv < 2.0
    
    def test_option_wrapper(self):
        """测试OptionWrapper类"""
        from src.deribit_webhook.utils.option_calculator import OptionWrapper
        
        # 创建模拟的QuantLib期权对象
        mock_option = MagicMock()
        mock_option.NPV.return_value = 33.6148
        mock_option.delta.return_value = 0.6234
        mock_option.gamma.return_value = 0.0045
        mock_option.theta.return_value = -4.5  # 年化
        mock_option.vega.return_value = 567.0  # 对100%波动率变化
        mock_option.rho.return_value = 234.0  # 对100%利率变化
        
        mock_process = MagicMock()
        
        wrapper = OptionWrapper(mock_option, mock_process)
        
        # 测试各个方法
        assert wrapper.NPV() == 33.6148
        assert wrapper.delta() == 0.6234
        assert wrapper.gamma() == 0.0045
        assert abs(wrapper.theta() - (-4.5/365)) < 1e-6  # 转换为每日
        assert abs(wrapper.vega() - 5.67) < 1e-6  # 转换为对1%变化
        assert abs(wrapper.rho() - 2.34) < 1e-6  # 转换为对1%变化


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not available")
def test_real_world_example():
    """测试真实世界的例子"""
    # QQQ期权示例
    greeks = calculate_option_greeks(
        option_type='call',
        underlying_price=400.0,  # QQQ当前价格
        strike_price=405.0,      # 行权价
        risk_free_rate=0.05,     # 5%无风险利率
        volatility=0.25,         # 25%隐含波动率
        settlement_date=datetime.now().strftime('%Y-%m-%d'),
        expiration_date='2024-12-20',  # 到期日
        dividend_rate=0.02       # 2%股息率
    )
    
    print(f"\nQQQ Call Option Greeks:")
    print(f"Value: ${greeks['value']:.2f}")
    print(f"Delta: {greeks['delta']:.4f}")
    print(f"Gamma: {greeks['gamma']:.4f}")
    print(f"Theta: {greeks['theta']:.4f}")
    print(f"Vega: {greeks['vega']:.4f}")
    print(f"Rho: {greeks['rho']:.4f}")
    
    # 验证结果合理性
    assert greeks['value'] > 0
    assert 0 < greeks['delta'] < 1
    assert greeks['gamma'] > 0
