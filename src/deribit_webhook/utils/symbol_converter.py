"""
期权标识符转换器

实现Deribit格式与Tiger Brokers格式之间的双向转换
"""

import re
from datetime import datetime
from typing import Dict, Optional


class OptionSymbolConverter:
    """期权标识符转换器"""
    
    # 标的资产映射表
    UNDERLYING_MAPPING = {
        # Deribit -> Tiger
        "BTC": "AAPL",
        "ETH": "TSLA", 
        "SOL": "NVDA",
        "USDC": "SPY",
        # Tiger -> Deribit  
        "AAPL": "BTC",
        "TSLA": "ETH",
        "NVDA": "SOL",
        "SPY": "USDC",
        "MSFT": "BTC",
        "GOOGL": "BTC",
        "META": "ETH",
        "QQQ": "USDC",
        "IWM": "USDC"
    }
    
    # 月份映射
    MONTH_MAPPING = {
        1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
        7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"
    }
    
    MONTH_REVERSE_MAPPING = {v: k for k, v in MONTH_MAPPING.items()}
    
    @classmethod
    def deribit_to_tiger(cls, deribit_symbol: str) -> str:
        """
        转换Deribit期权标识符到Tiger格式
        BTC-25DEC21-50000-C -> AAPL  211225C00050000
        """
        try:
            parts = deribit_symbol.split('-')
            if len(parts) != 4:
                raise ValueError(f"Invalid Deribit symbol format: {deribit_symbol}")
            
            underlying, expiry_str, strike_str, option_type = parts
            
            # 转换标的资产
            tiger_underlying = cls.UNDERLYING_MAPPING.get(underlying)
            if not tiger_underlying:
                raise ValueError(f"Unsupported underlying: {underlying}")
            
            # 转换到期日: 25DEC21 -> 211225
            expiry_date = cls._parse_deribit_expiry(expiry_str)
            tiger_expiry = expiry_date.strftime("%y%m%d")
            
            # 转换行权价: 50000 -> 00050000
            strike_price = float(strike_str)
            # Tiger使用千分之一为单位，所以乘以1000
            tiger_strike = f"{int(strike_price * 1000):08d}"
            
            # 转换期权类型: C/P -> C/P
            tiger_type = option_type.upper()
            
            return f"{tiger_underlying}  {tiger_expiry}{tiger_type}{tiger_strike}"
            
        except Exception as error:
            raise ValueError(f"Failed to convert Deribit symbol {deribit_symbol}: {error}")
    
    @classmethod
    def tiger_to_deribit(cls, tiger_symbol: str) -> str:
        """
        转换Tiger期权标识符到Deribit格式
        AAPL  211225C00050000 -> BTC-25DEC21-50000-C
        """
        try:
            # 解析Tiger格式
            parts = tiger_symbol.strip().split()
            if len(parts) != 2:
                raise ValueError(f"Invalid Tiger symbol format: {tiger_symbol}")
            
            underlying = parts[0]
            option_part = parts[1]
            
            # 解析期权部分: 211225C00050000
            if len(option_part) < 9:
                raise ValueError(f"Invalid Tiger option part: {option_part}")
            
            expiry_str = option_part[:6]  # 211225
            option_type = option_part[6]  # C or P
            strike_str = option_part[7:]  # 00050000
            
            # 转换标的资产
            deribit_underlying = cls.UNDERLYING_MAPPING.get(underlying)
            if not deribit_underlying:
                raise ValueError(f"Unsupported underlying: {underlying}")
            
            # 转换到期日: 211225 -> 25DEC21
            expiry_date = datetime.strptime(f"20{expiry_str}", "%Y%m%d")
            day = expiry_date.day
            month = cls.MONTH_MAPPING[expiry_date.month]
            year = expiry_date.strftime("%y")
            deribit_expiry = f"{day:02d}{month}{year}"
            
            # 转换行权价: 00050000 -> 50000
            strike_price = int(strike_str) / 1000
            
            return f"{deribit_underlying}-{deribit_expiry}-{int(strike_price)}-{option_type}"
            
        except Exception as error:
            raise ValueError(f"Failed to convert Tiger symbol {tiger_symbol}: {error}")
    
    @classmethod
    def _parse_deribit_expiry(cls, expiry_str: str) -> datetime:
        """
        解析Deribit到期日格式
        25DEC21 -> datetime(2021, 12, 25)
        """
        try:
            # 使用正则表达式解析
            match = re.match(r'(\d{1,2})([A-Z]{3})(\d{2})', expiry_str.upper())
            if not match:
                raise ValueError(f"Invalid expiry format: {expiry_str}")
            
            day_str, month_str, year_str = match.groups()
            
            day = int(day_str)
            month = cls.MONTH_REVERSE_MAPPING.get(month_str)
            if month is None:
                raise ValueError(f"Invalid month: {month_str}")
            
            # 假设年份在2000-2099之间
            year = 2000 + int(year_str)
            
            return datetime(year, month, day)
            
        except Exception as error:
            raise ValueError(f"Failed to parse expiry {expiry_str}: {error}")
    
    @classmethod
    def get_underlying_mapping(cls, deribit_underlying: str) -> Optional[str]:
        """获取Deribit标的对应的Tiger标的"""
        return cls.UNDERLYING_MAPPING.get(deribit_underlying)
    
    @classmethod
    def get_deribit_underlying(cls, tiger_underlying: str) -> Optional[str]:
        """获取Tiger标的对应的Deribit标的"""
        return cls.UNDERLYING_MAPPING.get(tiger_underlying)
    
    @classmethod
    def is_valid_deribit_symbol(cls, symbol: str) -> bool:
        """验证是否为有效的Deribit期权标识符"""
        try:
            parts = symbol.split('-')
            if len(parts) != 4:
                return False
            
            underlying, expiry_str, strike_str, option_type = parts
            
            # 检查标的资产
            if underlying not in cls.UNDERLYING_MAPPING:
                return False
            
            # 检查到期日格式
            cls._parse_deribit_expiry(expiry_str)
            
            # 检查行权价
            float(strike_str)
            
            # 检查期权类型
            if option_type not in ['C', 'P']:
                return False
            
            return True
            
        except:
            return False
    
    @classmethod
    def is_valid_tiger_symbol(cls, symbol: str) -> bool:
        """验证是否为有效的Tiger期权标识符"""
        try:
            parts = symbol.strip().split()
            if len(parts) != 2:
                return False
            
            underlying = parts[0]
            option_part = parts[1]
            
            # 检查标的资产
            if underlying not in cls.UNDERLYING_MAPPING:
                return False
            
            # 检查期权部分格式
            if len(option_part) < 9:
                return False
            
            expiry_str = option_part[:6]
            option_type = option_part[6]
            strike_str = option_part[7:]
            
            # 验证到期日
            datetime.strptime(f"20{expiry_str}", "%Y%m%d")
            
            # 验证期权类型
            if option_type not in ['C', 'P']:
                return False
            
            # 验证行权价
            int(strike_str)
            
            return True
            
        except:
            return False


# 测试函数
def test_symbol_converter():
    """测试标识符转换器"""
    converter = OptionSymbolConverter()
    
    test_cases = [
        "BTC-25DEC21-50000-C",
        "ETH-31DEC21-4000-P",
        "BTC-15JAN22-60000-C"
    ]
    
    print("🔄 Testing symbol conversion...")
    
    for deribit_symbol in test_cases:
        try:
            tiger_symbol = converter.deribit_to_tiger(deribit_symbol)
            back_to_deribit = converter.tiger_to_deribit(tiger_symbol)
            
            print(f"✅ {deribit_symbol} -> {tiger_symbol} -> {back_to_deribit}")
            
            if deribit_symbol == back_to_deribit:
                print("✅ Round-trip conversion successful")
            else:
                print("❌ Round-trip conversion failed")
                
        except Exception as e:
            print(f"❌ Conversion failed for {deribit_symbol}: {e}")


if __name__ == "__main__":
    test_symbol_converter()
