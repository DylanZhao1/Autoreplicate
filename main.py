import os
import json
from datetime import datetime
import logging
from services.pdf_converter import PDFConverter
from services.content_extractor import ContentExtractor
from services.factor_generator import FactorGenerator
from services.backtest_service import BacktestService
from services.model_manager import LangChainModelManager


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建必要的目录
os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)
os.makedirs('static/results', exist_ok=True)
os.makedirs('config', exist_ok=True)

# 初始化LangChain模型管理器和服务
model_manager = LangChainModelManager()
pdf_converter = PDFConverter(model_manager)
content_extractor = ContentExtractor(model_manager)
factor_generator = FactorGenerator(model_manager)
backtest_service = BacktestService()

def generate(filepath):

    try:
        if not filepath.lower().endswith('.pdf'):
            return jsonify({'error': '只支持PDF文件'}), 400
        
        # 转换PDF为Markdown
        markdown_content = pdf_converter.convert_to_markdown(filepath)
        
        print(markdown_content)
        # 保存Markdown文件
        markdown_filename = f"{filepath.split('/')[-1].split('.')[0]}_converted.md"
        markdown_path = os.path.join('outputs', markdown_filename)
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
    except Exception as e:
        logger.error(f"PDF转换错误: {str(e)}")
        raise Exception(f'PDF转换失败: {str(e)}')

    extracted_info = content_extractor.extract_key_information(markdown_content)
        
    # 验证返回的数据结构
    if not isinstance(extracted_info.get('key_factors'), list):
        logger.warning(f"key_factors不是列表格式: {type(extracted_info.get('key_factors'))}")
        # 尝试修复
        if 'key_factors' in extracted_info:
            if isinstance(extracted_info['key_factors'], str):
                try:
                    extracted_info['key_factors'] = json.loads(extracted_info['key_factors'])
                except:
                    extracted_info['key_factors'] = []
            elif not isinstance(extracted_info['key_factors'], list):
                extracted_info['key_factors'] = []
    
    try:
        factor_code = factor_generator.generate_factor_code(markdown_content, extracted_info)
        
        # 保存生成的代码
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        code_filename = f"factor_{timestamp}.py"
        code_path = os.path.join('outputs', code_filename)
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(factor_code)
        
        return {
            'success': True,
            #'factor_code': factor_code,
            'markdown_file': markdown_filename,
            'extracted_info': extracted_info,
            'code_file': code_filename,
            'model_used':  model_manager.get_default_model("factor_generation")
        }
    
    except Exception as e:
        logger.error(f"因子生成错误: {str(e)}")
        raise Exception(f'生成失败: {str(e)}')

if __name__ == '__main__':
    result = generate('ssrn-44335102.pdf')
    print(result)
