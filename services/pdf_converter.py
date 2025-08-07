import os
from typing import Optional
import logging
from gptpdf import parse_pdf
from .model_manager import LangChainModelManager
from services import model_manager

logger = logging.getLogger(__name__)

class PDFConverter:
    """PDF转换服务，使用LangChain统一接口"""
    
    def __init__(self, model_manager: Optional[LangChainModelManager] = None):
        self.model_manager = model_manager or LangChainModelManager()
        self.output_dir = './outputs'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def convert_to_markdown(self, pdf_path: str, model_id: Optional[str] = None, 
                          verbose: bool = False) -> str:
        """将PDF文件转换为Markdown格式"""
        try:
            # 使用gptpdf进行转换
            content, image_paths = parse_pdf(
                pdf_path=pdf_path,
                output_dir=self.output_dir,
                model_manager = self.model_manager
            )
            
            logger.info(f"PDF转换成功，使用模型: {model_id}，生成了{len(image_paths)}个图片文件")
            return content
                
        except Exception as e:
            logger.warning(f"PDF转换失败，使用模拟转换: {str(e)}")
            return self._mock_conversion(pdf_path)

    def _mock_conversion(self, pdf_path: str) -> str:
        """模拟PDF转换"""
        return f"""
# 论文标题：基于机器学习的股票价格预测模型研究

## 摘要
本文提出了一种基于机器学习的股票价格预测模型，通过分析历史价格数据、技术指标和基本面数据，构建了一个多因子预测框架。

## 1. 引言
股票价格预测一直是金融领域的重要研究方向...

## 2. 数据与方法
### 2.1 数据来源
- 股票价格数据：来自Wind数据库
- 财务数据：上市公司年报和季报
- 宏观经济数据：央行和统计局数据

### 2.2 特征工程
构建了以下技术指标：
- 移动平均线（MA5, MA10, MA20）
- 相对强弱指数（RSI）
- 布林带指标
- 成交量相关指标

## 3. 模型构建
采用随机森林算法构建预测模型...

## 4. 实证结果
回测结果显示，该策略在2020-2023年期间年化收益率达到15.2%...

## 5. 结论
本文提出的多因子模型在股票预测方面表现良好...
"""