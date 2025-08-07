from typing import Dict, Any, Optional, List
import logging
from .model_manager import LangChainModelManager

logger = logging.getLogger(__name__)

class FactorGenerator:
    """因子代码生成服务，支持多个大模型API"""
    
    def __init__(self, model_manager: Optional[LangChainModelManager] = None):
        self.model_manager = model_manager or LangChainModelManager()
    
    def generate_factor_code(self, paper_content: str, extracted_info: Dict[str, Any]) -> str:
        """根据提取的信息生成因子代码"""
        try:
            prompt = self._build_prompt(paper_content, extracted_info)
            
            messages = [
                {"role": "system", "content": "你是一个专业的量化分析师，擅长根据学术论文生成Python因子代码。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.model_manager.invoke_task_model("factor_generation", messages)
            
            logger.info(f"因子代码生成成功")
            return response
            
        except Exception as e:
            logger.warning(f"生成因子代码失败，使用模拟生成: {str(e)}")
            return self._mock_factor_generation(extracted_info)
    
    
    def _build_prompt(self, paper_content, extracted_info: Dict[str, Any]) -> str:
        """构建提示词"""
        return f"""
请是一篇金融学领域的论文，具体内容如下：
{paper_content}
请根据论文具体内容和以下的论文信息生成一个Python因子类，要求：
1. 继承自基础Factor类
2. 实现calculate方法计算因子值
3. 包含必要的参数配置
4. 添加详细的文档说明
5. 代码要能够处理pandas DataFrame格式的股票数据

论文信息：
- 核心问题：{extracted_info.get('core_problem', '')}
- 解决方案：{extracted_info.get('solution', {})}
- 关键因子：{extracted_info.get('key_factors', [])}
- 数据集：{extracted_info.get('datasets', {})}

请生成完整的Python代码，包含类定义和使用示例。
"""
    
    def _mock_factor_generation(self, extracted_info: Dict[str, Any]) -> str:
        """模拟因子代码生成（用于测试）"""
        return '''
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class MLPredictionFactor:
    """
    基于机器学习的股票预测因子
    
    根据论文《基于机器学习的股票价格预测模型研究》实现的多因子模型
    """
    
    def __init__(self, 
                 ma_periods: list = [5, 10, 20],
                 rsi_period: int = 14,
                 volume_period: int = 20):
        """
        初始化因子参数
        
        Args:
            ma_periods: 移动平均线周期列表
            rsi_period: RSI计算周期
            volume_period: 成交量比率计算周期
        """
        self.ma_periods = ma_periods
        self.rsi_period = rsi_period
        self.volume_period = volume_period
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子值
        
        Args:
            data: 包含OHLCV数据的DataFrame
                 必须包含列：open, high, low, close, volume
        
        Returns:
            包含因子值的DataFrame
        """
        result = data.copy()
        
        # 计算移动平均线
        for period in self.ma_periods:
            result[f'ma_{period}'] = data['close'].rolling(window=period).mean()
            result[f'ma_{period}_ratio'] = data['close'] / result[f'ma_{period}'] - 1
        
        # 计算RSI
        result['rsi'] = self._calculate_rsi(data['close'], self.rsi_period)
        
        # 计算成交量比率
        result['volume_ma'] = data['volume'].rolling(window=self.volume_period).mean()
        result['volume_ratio'] = data['volume'] / result['volume_ma']
        
        # 计算价格动量
        result['price_momentum_5'] = data['close'].pct_change(5)
        result['price_momentum_20'] = data['close'].pct_change(20)
        
        # 计算波动率
        result['volatility_20'] = data['close'].pct_change().rolling(window=20).std()
        
        # 计算综合因子得分
        result['ml_factor_score'] = self._calculate_composite_score(result)
        
        return result
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """
        计算相对强弱指数(RSI)
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_composite_score(self, data: pd.DataFrame) -> pd.Series:
        """
        计算综合因子得分
        """
        # 标准化各个因子
        features = ['ma_5_ratio', 'ma_10_ratio', 'ma_20_ratio', 'rsi', 
                   'volume_ratio', 'price_momentum_5', 'price_momentum_20', 'volatility_20']
        
        score = pd.Series(0, index=data.index)
        
        for feature in features:
            if feature in data.columns:
                # 简单的线性组合，实际应用中可以使用机器学习模型
                normalized = (data[feature] - data[feature].rolling(252).mean()) / data[feature].rolling(252).std()
                score += normalized.fillna(0) * 0.125  # 等权重
        
        return score
    
    def get_factor_info(self) -> Dict[str, Any]:
        """
        获取因子信息
        """
        return {
            'name': 'ML Prediction Factor',
            'description': '基于机器学习的股票预测因子',
            'parameters': {
                'ma_periods': self.ma_periods,
                'rsi_period': self.rsi_period,
                'volume_period': self.volume_period
            },
            'output_columns': [
                'ma_5', 'ma_10', 'ma_20',
                'ma_5_ratio', 'ma_10_ratio', 'ma_20_ratio',
                'rsi', 'volume_ratio', 'price_momentum_5', 
                'price_momentum_20', 'volatility_20', 'ml_factor_score'
            ]
        }

# 使用示例
if __name__ == "__main__":
    # 创建因子实例
    factor = MLPredictionFactor()
    
    # 假设有股票数据
    # data = pd.read_csv('stock_data.csv')
    # result = factor.calculate(data)
    # print(result[['close', 'ml_factor_score']].tail())
    
    print("因子信息：")
    print(factor.get_factor_info())
'''
