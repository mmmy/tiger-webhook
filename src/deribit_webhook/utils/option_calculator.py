"""
期权计算工具模块

基于QuantLib库实现期权希腊字母计算、期权价格计算、隐含波动率计算等功能。
参考: https://quant.itigerup.com/openapi/zh/python/quickStart/other.html#期权计算工具
"""

from datetime import datetime, date
from typing import Dict, Optional, Union
import math
# 注释掉Tiger的helper，因为存在兼容性问题
# 注释掉Tiger的helper，因为存在兼容性问题
# from tigeropen.examples.option_helpers.helpers import FDAmericanDividendOptionHelper
try:
    import QuantLib as ql
    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False
    # 创建一个虚拟的ql模块以避免NameError
    class MockQL:
        class Date:
            pass
    ql = MockQL()


class OptionCalculator:
    """期权计算器 - 计算希腊字母、期权价格和隐含波动率"""
    
    def __init__(self):
        if not QUANTLIB_AVAILABLE:
            raise ImportError(
                "QuantLib is required for option calculations. "
                "Please install it with: pip install quantlib"
            )
    
    def calculate_greeks(
        self,
        option_type: str,
        underlying_price: float,
        strike_price: float,
        risk_free_rate: float,
        dividend_rate: float,
        volatility: float,
        settlement_date: Union[datetime, date, str],
        expiration_date: Union[datetime, date, str],
        evaluation_date: Optional[Union[datetime, date, str]] = None,
        option_style: str = "american"
    ) -> Dict[str, float]:
        """
        计算期权希腊字母
        
        Args:
            option_type: 期权类型 ('call' 或 'put')
            underlying_price: 标的价格
            strike_price: 行权价
            risk_free_rate: 无风险利率 (例如: 0.017 表示 1.7%)
            dividend_rate: 股息率 (例如: 0.02 表示 2%)
            volatility: 隐含波动率 (例如: 0.25 表示 25%)
            settlement_date: 结算日期
            expiration_date: 到期日期
            evaluation_date: 估值日期 (默认为今天)
            option_style: 期权风格 ('american' 或 'european')
            
        Returns:
            包含希腊字母的字典: {
                'value': 期权价格,
                'delta': Delta值,
                'gamma': Gamma值,
                'theta': Theta值,
                'vega': Vega值,
                'rho': Rho值
            }
        """
        try:
            # 设置估值日期
            if evaluation_date is None:
                evaluation_date = datetime.now().date()
            
            eval_date = self._convert_to_ql_date(evaluation_date)
            ql.Settings.instance().evaluationDate = eval_date
            
            # 转换期权类型
            ql_option_type = ql.Option.Call if option_type.lower() == 'call' else ql.Option.Put
            
            # 转换日期
            settlement_ql = self._convert_to_ql_date(settlement_date)
            expiration_ql = self._convert_to_ql_date(expiration_date)
            
            # 选择期权计算器
            if option_style.lower() == "american":
                helper = self._create_american_option_helper(
                    ql_option_type, underlying_price, strike_price,
                    risk_free_rate, dividend_rate, volatility,
                    settlement_ql, expiration_ql
                )
            else:
                helper = self._create_european_option_helper(
                    ql_option_type, underlying_price, strike_price,
                    risk_free_rate, dividend_rate, volatility,
                    settlement_ql, expiration_ql
                )
            
            # 计算希腊字母
            return {
                'value': helper.NPV(),
                'delta': helper.delta(),
                'gamma': helper.gamma(),
                'theta': helper.theta(),
                'vega': helper.vega(),
                'rho': helper.rho()
            }
            
        except Exception as e:
            raise ValueError(f"Failed to calculate option Greeks: {str(e)}")
    
    def calculate_implied_volatility(
        self,
        option_type: str,
        underlying_price: float,
        strike_price: float,
        risk_free_rate: float,
        dividend_rate: float,
        option_price: float,
        settlement_date: Union[datetime, date, str],
        expiration_date: Union[datetime, date, str],
        evaluation_date: Optional[Union[datetime, date, str]] = None,
        option_style: str = "american"
    ) -> float:
        """
        根据期权价格计算隐含波动率
        
        Args:
            option_type: 期权类型 ('call' 或 'put')
            underlying_price: 标的价格
            strike_price: 行权价
            risk_free_rate: 无风险利率
            dividend_rate: 股息率
            option_price: 期权市场价格
            settlement_date: 结算日期
            expiration_date: 到期日期
            evaluation_date: 估值日期 (默认为今天)
            option_style: 期权风格 ('american' 或 'european')
            
        Returns:
            隐含波动率 (例如: 0.25 表示 25%)
        """
        try:
            # 设置估值日期
            if evaluation_date is None:
                evaluation_date = datetime.now().date()
            
            eval_date = self._convert_to_ql_date(evaluation_date)
            ql.Settings.instance().evaluationDate = eval_date
            
            # 转换期权类型
            ql_option_type = ql.Option.Call if option_type.lower() == 'call' else ql.Option.Put
            
            # 转换日期
            settlement_ql = self._convert_to_ql_date(settlement_date)
            expiration_ql = self._convert_to_ql_date(expiration_date)
            
            # 创建期权计算器 (初始波动率设为0)
            if option_style.lower() == "american":
                helper = self._create_american_option_helper(
                    ql_option_type, underlying_price, strike_price,
                    risk_free_rate, dividend_rate, 0.0,  # 初始波动率为0
                    settlement_ql, expiration_ql
                )
            else:
                helper = self._create_european_option_helper(
                    ql_option_type, underlying_price, strike_price,
                    risk_free_rate, dividend_rate, 0.0,  # 初始波动率为0
                    settlement_ql, expiration_ql
                )
            
            # 计算隐含波动率
            implied_vol = helper.implied_volatility(option_price)
            return implied_vol
            
        except Exception as e:
            raise ValueError(f"Failed to calculate implied volatility: {str(e)}")
    
    def _convert_to_ql_date(self, date_input: Union[datetime, date, str]) -> ql.Date:
        """将日期转换为QuantLib Date对象"""
        if isinstance(date_input, str):
            # 假设格式为 'YYYY-MM-DD'
            dt = datetime.strptime(date_input, '%Y-%m-%d').date()
        elif isinstance(date_input, datetime):
            dt = date_input.date()
        else:
            dt = date_input
        
        return ql.Date(dt.day, dt.month, dt.year)
    
    def _create_american_option_helper(
        self, option_type, underlying, strike, risk_free_rate,
        dividend_rate, volatility, settlement_date, expiration_date
    ):
        """创建美式期权计算器 (适用于美股期权、港股期权、ETF期权)"""
        return self._create_option_engine(
            option_type, underlying, strike, risk_free_rate,
            dividend_rate, volatility, settlement_date, expiration_date,
            exercise_type="american"
        )

    def _create_european_option_helper(
        self, option_type, underlying, strike, risk_free_rate,
        dividend_rate, volatility, settlement_date, expiration_date
    ):
        """创建欧式期权计算器 (适用于指数期权)"""
        return self._create_option_engine(
            option_type, underlying, strike, risk_free_rate,
            dividend_rate, volatility, settlement_date, expiration_date,
            exercise_type="european"
        )

    def _create_option_engine(
        self, option_type, underlying, strike, risk_free_rate,
        dividend_rate, volatility, settlement_date, expiration_date,
        exercise_type="american"
    ):
        """使用QuantLib直接创建期权定价引擎"""
        # 实现有限差分美式期权计算，替代Tiger的FDAmericanDividendOptionHelper
        # 创建标的资产价格
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying))

        # 创建利率曲线
        risk_free_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(settlement_date, risk_free_rate, ql.Actual365Fixed())
        )

        # 创建股息率曲线
        dividend_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(settlement_date, dividend_rate, ql.Actual365Fixed())
        )

        # 创建波动率曲线
        volatility_ts = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(settlement_date, ql.NullCalendar(), volatility, ql.Actual365Fixed())
        )

        # 创建Black-Scholes过程
        bsm_process = ql.BlackScholesMertonProcess(
            spot_handle, dividend_ts, risk_free_ts, volatility_ts
        )

        # 创建期权payoff
        payoff = ql.PlainVanillaPayoff(option_type, strike)

        # 创建行权条件
        if exercise_type.lower() == "american":
            exercise = ql.AmericanExercise(settlement_date, expiration_date)
        else:
            exercise = ql.EuropeanExercise(expiration_date)

        # 创建期权
        option = ql.VanillaOption(payoff, exercise)

        # 设置定价引擎
        if exercise_type.lower() == "american":
            # 美式期权使用二叉树方法 (更稳定，支持所有希腊字母)
            # 注意：有限差分方法虽然精度更高，但不支持Vega和Rho计算
            engine = ql.BinomialCRRVanillaEngine(bsm_process, 200)  # 增加步数提高精度
        else:
            # 欧式期权使用解析解
            engine = ql.AnalyticEuropeanEngine(bsm_process)

        option.setPricingEngine(engine)

        return OptionWrapper(option, bsm_process)

    def _create_fd_american_option(
        self, option_type, underlying, strike, risk_free_rate,
        dividend_rate, volatility, settlement_date, expiration_date
    ):
        """
        使用有限差分方法创建美式期权

        这个方法实现了类似Tiger FDAmericanDividendOptionHelper的功能，
        使用QuantLib的有限差分引擎。

        注意：有限差分引擎不支持Vega和Rho的计算，
        如果需要这些希腊字母，请使用二叉树方法。
        """
        # 创建标的资产价格
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying))

        # 创建利率曲线
        risk_free_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(settlement_date, risk_free_rate, ql.Actual365Fixed())
        )

        # 创建股息率曲线
        dividend_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(settlement_date, dividend_rate, ql.Actual365Fixed())
        )

        # 创建波动率曲线
        volatility_ts = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(settlement_date, ql.NullCalendar(), volatility, ql.Actual365Fixed())
        )

        # 创建Black-Scholes过程
        bsm_process = ql.BlackScholesMertonProcess(
            spot_handle, dividend_ts, risk_free_ts, volatility_ts
        )

        # 创建期权payoff
        payoff = ql.PlainVanillaPayoff(option_type, strike)

        # 创建美式行权条件
        exercise = ql.AmericanExercise(settlement_date, expiration_date)

        # 创建期权
        option = ql.VanillaOption(payoff, exercise)

        # 使用有限差分引擎
        # 参数：时间步数=100, 空间步数=100
        engine = ql.FdBlackScholesVanillaEngine(bsm_process, 100, 100)
        option.setPricingEngine(engine)

        return OptionWrapper(option, bsm_process)


class OptionWrapper:
    """期权包装器，提供统一的接口"""

    def __init__(self, option, process):
        self.option = option
        self.process = process

    def NPV(self):
        """期权价格"""
        return self.option.NPV()

    def delta(self):
        """Delta值"""
        try:
            return self.option.delta()
        except Exception:
            return 0.0

    def gamma(self):
        """Gamma值"""
        try:
            return self.option.gamma()
        except Exception:
            return 0.0

    def theta(self):
        """Theta值 (每日时间衰减)"""
        try:
            return self.option.theta() / 365.0  # 转换为每日
        except Exception:
            return 0.0

    def vega(self):
        """Vega值 (对1%波动率变化的敏感性)"""
        try:
            return self.option.vega() / 100.0  # 转换为对1%变化的敏感性
        except Exception:
            # 如果vega计算失败，返回0
            return 0.0

    def rho(self):
        """Rho值 (对1%利率变化的敏感性)"""
        try:
            return self.option.rho() / 100.0  # 转换为对1%变化的敏感性
        except Exception:
            return 0.0

    def implied_volatility(self, target_price, accuracy=1e-6):
        """计算隐含波动率"""
        try:
            return self.option.impliedVolatility(target_price, self.process, accuracy)
        except Exception as e:
            raise ValueError(f"Failed to calculate implied volatility: {str(e)}")

    def update_implied_volatility(self, volatility):
        """更新隐含波动率"""
        # 这个方法在我们的实现中不需要，因为我们每次都重新创建期权对象
        pass


# 便捷函数
def calculate_option_greeks(
    option_type: str,
    underlying_price: float,
    strike_price: float,
    risk_free_rate: float,
    volatility: float,
    settlement_date: Union[datetime, date, str],
    expiration_date: Union[datetime, date, str],
    dividend_rate: float = 0.0,
    evaluation_date: Optional[Union[datetime, date, str]] = None,
    option_style: str = "american"
) -> Dict[str, float]:
    """
    便捷函数：计算期权希腊字母
    
    Example:
        greeks = calculate_option_greeks(
            option_type='call',
            underlying_price=985,
            strike_price=990,
            risk_free_rate=0.017,
            volatility=0.6153,
            settlement_date='2022-04-14',
            expiration_date='2022-04-22'
        )
        print(f"Delta: {greeks['delta']:.4f}")
        print(f"Gamma: {greeks['gamma']:.4f}")
    """
    calculator = OptionCalculator()
    return calculator.calculate_greeks(
        option_type=option_type,
        underlying_price=underlying_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        dividend_rate=dividend_rate,
        volatility=volatility,
        settlement_date=settlement_date,
        expiration_date=expiration_date,
        evaluation_date=evaluation_date,
        option_style=option_style
    )


def calculate_implied_volatility(
    option_type: str,
    underlying_price: float,
    strike_price: float,
    risk_free_rate: float,
    option_price: float,
    settlement_date: Union[datetime, date, str],
    expiration_date: Union[datetime, date, str],
    dividend_rate: float = 0.0,
    evaluation_date: Optional[Union[datetime, date, str]] = None,
    option_style: str = "american"
) -> float:
    """
    便捷函数：计算隐含波动率
    
    Example:
        iv = calculate_implied_volatility(
            option_type='call',
            underlying_price=985,
            strike_price=990,
            risk_free_rate=0.017,
            option_price=33.6148,
            settlement_date='2022-04-14',
            expiration_date='2022-04-22'
        )
        print(f"Implied Volatility: {iv:.4f} ({iv*100:.2f}%)")
    """
    calculator = OptionCalculator()
    return calculator.calculate_implied_volatility(
        option_type=option_type,
        underlying_price=underlying_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        dividend_rate=dividend_rate,
        option_price=option_price,
        settlement_date=settlement_date,
        expiration_date=expiration_date,
        evaluation_date=evaluation_date,
        option_style=option_style
    )
