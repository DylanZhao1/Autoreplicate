import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BacktestService:
    """回测服务"""
    
    def __init__(self):
        self.data_cache = {}
    
    def run_backtest(self, 
                    factor_code: str, 
                    dataset: str, 
                    start_date: Optional[str] = None, 
                    end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            factor_code: 因子代码
            dataset: 数据集名称
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            回测结果字典
        """
        try:
            # 获取数据
            data = self._get_dataset(dataset, start_date, end_date)
            
            # 执行因子代码
            factor_values = self._execute_factor_code(factor_code, data)
            
            # 计算回测结果
            results = self._calculate_backtest_results(data, factor_values)
            
            return results
            
        except Exception as e:
            logger.error(f"回测执行错误: {str(e)}")
            return {'error': str(e)}
    
    def _get_dataset(self, dataset: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取数据集"""
        # 这里应该连接到实际的数据源
        # 现在返回模拟数据
        
        if not start_date:
            start_date = '2020-01-01'
        if not end_date:
            end_date = '2023-12-31'
        
        # 生成模拟股票数据
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 模拟多只股票数据
        stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
        
        data_list = []
        for stock in stocks:
            stock_data = self._generate_mock_stock_data(stock, date_range)
            data_list.append(stock_data)
        
        return pd.concat(data_list, ignore_index=True)
    
    def _generate_mock_stock_data(self, stock_code: str, date_range: pd.DatetimeIndex) -> pd.DataFrame:
        """生成模拟股票数据"""
        np.random.seed(hash(stock_code) % 2**32)  # 为每只股票设置不同的随机种子
        
        n_days = len(date_range)
        
        # 生成价格数据（随机游走）
        returns = np.random.normal(0.0005, 0.02, n_days)  # 日收益率
        prices = [10.0]  # 初始价格
        
        for i in range(1, n_days):
            prices.append(prices[-1] * (1 + returns[i]))
        
        prices = np.array(prices)
        
        # 生成OHLC数据
        high = prices * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
        low = prices * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
        open_prices = prices * (1 + np.random.normal(0, 0.005, n_days))
        
        # 生成成交量数据
        volume = np.random.lognormal(15, 0.5, n_days).astype(int)
        
        return pd.DataFrame({
            'date': date_range,
            'stock_code': stock_code,
            'open': open_prices,
            'high': high,
            'low': low,
            'close': prices,
            'volume': volume
        })
    
    def _execute_factor_code(self, factor_code: str, data: pd.DataFrame) -> pd.DataFrame:
        """执行因子代码"""
        try:
            # 创建安全的执行环境
            exec_globals = {
                'pd': pd,
                'np': np,
                '__builtins__': {
                    'len': len,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'list': list,
                    'dict': dict,
                    'str': str,
                    'int': int,
                    'float': float,
                    'print': print
                }
            }
            
            # 执行因子代码
            exec(factor_code, exec_globals)
            
            # 获取因子类
            factor_class = None
            for name, obj in exec_globals.items():
                if (isinstance(obj, type) and 
                    hasattr(obj, 'calculate') and 
                    name != 'pd' and name != 'np'):
                    factor_class = obj
                    break
            
            if factor_class is None:
                raise ValueError("未找到有效的因子类")
            
            # 按股票分组计算因子
            results = []
            for stock_code in data['stock_code'].unique():
                stock_data = data[data['stock_code'] == stock_code].copy()
                stock_data = stock_data.sort_values('date').reset_index(drop=True)
                
                # 创建因子实例并计算
                factor = factor_class()
                factor_result = factor.calculate(stock_data)
                factor_result['stock_code'] = stock_code
                results.append(factor_result)
            
            return pd.concat(results, ignore_index=True)
            
        except Exception as e:
            logger.error(f"因子代码执行错误: {str(e)}")
            raise
    
    def _calculate_backtest_results(self, data: pd.DataFrame, factor_data: pd.DataFrame) -> Dict[str, Any]:
        """计算回测结果"""
        try:
            # 合并数据
            merged_data = pd.merge(data, factor_data[['date', 'stock_code', 'ml_factor_score']], 
                                 on=['date', 'stock_code'], how='left')
            
            # 计算收益率
            merged_data = merged_data.sort_values(['stock_code', 'date'])
            merged_data['return'] = merged_data.groupby('stock_code')['close'].pct_change()
            
            # 因子分层回测
            daily_returns = []
            
            for date in merged_data['date'].unique():
                day_data = merged_data[merged_data['date'] == date].copy()
                
                if len(day_data) < 3 or day_data['ml_factor_score'].isna().all():
                    continue
                
                # 按因子值分层（五分位）
                day_data['factor_rank'] = pd.qcut(day_data['ml_factor_score'].rank(method='first'), 
                                                q=5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
                
                # 计算下一期收益率
                next_day_data = merged_data[merged_data['date'] > date].groupby('stock_code').first()
                day_data = day_data.merge(next_day_data[['return']], left_on='stock_code', right_index=True, suffixes=('', '_next'))
                
                if 'return_next' in day_data.columns:
                    # 计算各分层的平均收益率
                    layer_returns = day_data.groupby('factor_rank')['return_next'].mean()
                    
                    daily_returns.append({
                        'date': date,
                        'Q1_return': layer_returns.get('Q1', 0),
                        'Q2_return': layer_returns.get('Q2', 0),
                        'Q3_return': layer_returns.get('Q3', 0),
                        'Q4_return': layer_returns.get('Q4', 0),
                        'Q5_return': layer_returns.get('Q5', 0),
                        'long_short': layer_returns.get('Q5', 0) - layer_returns.get('Q1', 0)
                    })
            
            if not daily_returns:
                return {'error': '无法计算有效的回测结果'}
            
            returns_df = pd.DataFrame(daily_returns)
            
            # 计算累计收益率
            for col in ['Q1_return', 'Q2_return', 'Q3_return', 'Q4_return', 'Q5_return', 'long_short']:
                returns_df[f'{col}_cum'] = (1 + returns_df[col]).cumprod() - 1
            
            # 计算统计指标
            stats = self._calculate_performance_stats(returns_df)
            
            # 准备返回结果
            result = {
                'success': True,
                'performance_stats': stats,
                'daily_returns': returns_df.to_dict('records'),
                'cumulative_returns': {
                    'dates': returns_df['date'].dt.strftime('%Y-%m-%d').tolist(),
                    'Q1': returns_df['Q1_return_cum'].tolist(),
                    'Q2': returns_df['Q2_return_cum'].tolist(),
                    'Q3': returns_df['Q3_return_cum'].tolist(),
                    'Q4': returns_df['Q4_return_cum'].tolist(),
                    'Q5': returns_df['Q5_return_cum'].tolist(),
                    'long_short': returns_df['long_short_cum'].tolist()
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"回测结果计算错误: {str(e)}")
            return {'error': f'回测计算失败: {str(e)}'}
    
    def _calculate_performance_stats(self, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """计算绩效统计指标"""
        stats = {}
        
        for strategy in ['Q1_return', 'Q2_return', 'Q3_return', 'Q4_return', 'Q5_return', 'long_short']:
            returns = returns_df[strategy]
            
            # 年化收益率
            annual_return = (1 + returns.mean()) ** 252 - 1
            
            # 年化波动率
            annual_vol = returns.std() * np.sqrt(252)
            
            # 夏普比率
            sharpe = annual_return / annual_vol if annual_vol > 0 else 0
            
            # 最大回撤
            cum_returns = (1 + returns).cumprod()
            rolling_max = cum_returns.expanding().max()
            drawdown = (cum_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # 胜率
            win_rate = (returns > 0).mean()
            
            stats[strategy] = {
                'annual_return': round(annual_return * 100, 2),
                'annual_volatility': round(annual_vol * 100, 2),
                'sharpe_ratio': round(sharpe, 3),
                'max_drawdown': round(max_drawdown * 100, 2),
                'win_rate': round(win_rate * 100, 2),
                'total_return': round((cum_returns.iloc[-1] - 1) * 100, 2)
            }
        
        return stats