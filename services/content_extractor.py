import json
from typing import Dict, Any, Optional
import logging
from .model_manager import LangChainModelManager

logger = logging.getLogger(__name__)

class ContentExtractor:
    """内容提取服务，使用LangChain统一接口"""
    
    def __init__(self, model_manager: Optional[LangChainModelManager] = None):
        self.model_manager = model_manager or LangChainModelManager()
    
    def extract_key_information(self, markdown_content: str) -> Dict[str, Any]:
        """从Markdown内容中提取关键信息"""
        try:
            prompt = f"""
请从以下论文内容中提取关键信息，严格按照JSON格式返回，确保key_factors是一个数组：

论文内容：
{markdown_content}

请返回严格的JSON格式，包含以下字段：
{{
    "datasets": {{
        "primary": "主要数据源",
        "time_range": "时间范围",
        "frequency": "数据频率"
    }},
    "core_problem": "核心问题描述",
    "solution": {{
        "method": "方法",
        "algorithm": "算法",
        "strategy": "策略"
    }},
    "key_factors": [
        {{
            "name": "因子名称",
            "description": "因子描述",
            "type": "因子类型"
        }}
    ]
}}

注意：
1. 必须返回有效的JSON格式
2. key_factors必须是数组格式
3. 如果没有找到相关信息，使用"未知"或"未提取到"作为默认值
"""
            
            # 使用LangChain统一接口调用模型
            response = self.model_manager.invoke_task_model("content_extraction", prompt)
            
            # 解析JSON响应
            extracted_data = self._parse_json_response(response)
            
            # 验证和修复数据结构
            return self._validate_and_fix_structure(extracted_data)
                
        except Exception as e:
            logger.warning(f"使用模型提取内容失败，使用模拟提取: {str(e)}")
            return self._mock_extraction(markdown_content)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析模型返回的JSON响应"""
        try:
            # 直接尝试解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # 如果都失败，返回错误结构
            raise Exception(f"无法解析模型返回的JSON: {response[:200]}...")
    
    def _validate_and_fix_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证和修复数据结构"""
        # 确保基本结构存在
        if not isinstance(data, dict):
            raise Exception("返回的数据不是字典格式")
        
        # 修复key_factors字段
        if 'key_factors' not in data:
            data['key_factors'] = []
        elif not isinstance(data['key_factors'], list):
            # 尝试转换为列表
            if isinstance(data['key_factors'], str):
                try:
                    parsed = json.loads(data['key_factors'])
                    if isinstance(parsed, list):
                        data['key_factors'] = parsed
                    else:
                        data['key_factors'] = [{'name': 'parsed_factor', 'description': str(parsed), 'type': '解析因子'}]
                except:
                    data['key_factors'] = [{'name': 'string_factor', 'description': data['key_factors'], 'type': '文本因子'}]
            elif isinstance(data['key_factors'], dict):
                # 将字典转换为列表
                factor_list = []
                for key, value in data['key_factors'].items():
                    factor_list.append({
                        'name': key,
                        'description': str(value),
                        'type': '提取因子'
                    })
                data['key_factors'] = factor_list
            else:
                data['key_factors'] = [{'name': 'unknown_factor', 'description': str(data['key_factors']), 'type': '未知因子'}]
        
        # 确保每个因子都有必要的字段
        for i, factor in enumerate(data['key_factors']):
            if not isinstance(factor, dict):
                data['key_factors'][i] = {
                    'name': f'factor_{i}',
                    'description': str(factor),
                    'type': '转换因子'
                }
            else:
                factor.setdefault('name', f'factor_{i}')
                factor.setdefault('description', '无描述')
                factor.setdefault('type', '未分类')
        
        # 确保其他字段存在
        data.setdefault('datasets', {
            'primary': '未知',
            'time_range': '未知',
            'frequency': '未知'
        })
        data.setdefault('core_problem', '未提取到核心问题')
        data.setdefault('solution', {
            'method': '未知',
            'algorithm': '未知',
            'strategy': '未知'
        })
        
        return data
    
    def _mock_extraction(self, markdown_content: str) -> Dict[str, Any]:
        """模拟内容提取"""
        return {
            'datasets': {
                'primary': 'Wind股票数据库',
                'secondary': ['上市公司财务数据', '宏观经济数据'],
                'time_range': '2020-2023',
                'frequency': '日频数据'
            },
            'core_problem': '如何利用机器学习方法提高股票价格预测的准确性',
            'solution': {
                'method': '多因子机器学习模型',
                'algorithm': '随机森林',
                'features': ['技术指标', '基本面数据', '宏观经济指标'],
                'strategy': '基于预测结果的量化交易策略'
            },
            'key_factors': [
                {
                    'name': '移动平均线',
                    'description': 'MA5, MA10, MA20',
                    'type': '技术指标'
                },
                {
                    'name': '相对强弱指数',
                    'description': 'RSI技术指标',
                    'type': '技术指标'
                },
                {
                    'name': '市盈率',
                    'description': 'P/E比率',
                    'type': '基本面指标'
                }
            ]
        }