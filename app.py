from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import json
from datetime import datetime
import logging
from services.pdf_converter import PDFConverter
from services.content_extractor import ContentExtractor
from services.factor_generator import FactorGenerator
from services.backtest_service import BacktestService
from services.model_manager import LangChainModelManager

app = Flask(__name__)
CORS(app)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """获取所有可用的模型列表"""
    try:
        models = model_manager.get_available_models()
        return jsonify({
            'success': True,
            'models': models,
            'total_models': sum(len(provider_models) for provider_models in models.values())
        })
    except Exception as e:
        logger.error(f"获取模型列表错误: {str(e)}")
        return jsonify({'error': f'获取失败: {str(e)}'}), 500

@app.route('/api/test_model', methods=['POST'])
def test_model():
    """测试指定模型是否可用"""
    try:
        data = request.get_json()
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({'error': '请指定模型ID'}), 400
        
        # 测试模型调用
        test_message = "你好，请回复'测试成功'。"
        response = model_manager.invoke_model(model_id, test_message)
        
        return jsonify({
            'success': True,
            'model_id': model_id,
            'response': response,
            'status': 'available'
        })
        
    except Exception as e:
        logger.error(f"测试模型错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'unavailable'
        }), 500

@app.route('/api/upload_pdf', methods=['POST'])
def upload_pdf():
    """上传PDF文件并转换为Markdown"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': '只支持PDF文件'}), 400
        
        # 获取选择的模型
        model_id = request.form.get('model_id')
        
        # 保存上传的文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # 转换PDF为Markdown
        markdown_content = pdf_converter.convert_to_markdown(filepath, model_id)
        
        # 保存Markdown文件
        markdown_filename = f"{timestamp}_converted.md"
        markdown_path = os.path.join('outputs', markdown_filename)
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return jsonify({
            'success': True,
            'markdown_content': markdown_content,
            'markdown_file': markdown_filename,
            'original_file': filename,
            'model_used': model_id or model_manager.get_default_model("pdf_conversion")
        })
    
    except Exception as e:
        logger.error(f"PDF转换错误: {str(e)}")
        return jsonify({'error': f'转换失败: {str(e)}'}), 500

@app.route('/api/extract_content', methods=['POST'])
def extract_content():
    """从Markdown内容中提取关键信息"""
    try:
        data = request.get_json()
        markdown_content = data.get('markdown_content')
        model_id = data.get('model_id')
        
        if not markdown_content:
            return jsonify({'error': 'Markdown内容为空'}), 400
        
        # 提取内容
        extracted_info = content_extractor.extract_key_information(markdown_content, model_id)
        
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
        
        return jsonify({
            'success': True,
            'extracted_info': extracted_info,
            'model_used': model_id or model_manager.get_default_model("content_extraction")
        })
    
    except Exception as e:
        logger.error(f"内容提取错误: {str(e)}")
        return jsonify({'error': f'提取失败: {str(e)}'}), 500

@app.route('/api/generate_factor', methods=['POST'])
def generate_factor():
    """根据提取的信息生成因子代码"""
    try:
        data = request.get_json()
        extracted_info = data.get('extracted_info')
        model_id = data.get('model_id')
        
        if not extracted_info:
            return jsonify({'error': '提取信息为空'}), 400
        
        # 生成因子代码
        factor_code = factor_generator.generate_factor_code(extracted_info, model_id)
        
        # 保存生成的代码
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        code_filename = f"factor_{timestamp}.py"
        code_path = os.path.join('outputs', code_filename)
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(factor_code)
        
        return jsonify({
            'success': True,
            'factor_code': factor_code,
            'code_file': code_filename,
            'model_used': model_id or model_manager.get_default_model("factor_generation")
        })
    
    except Exception as e:
        logger.error(f"因子生成错误: {str(e)}")
        return jsonify({'error': f'生成失败: {str(e)}'}), 500

@app.route('/api/run_backtest', methods=['POST'])
def run_backtest():
    """运行回测"""
    try:
        data = request.get_json()
        factor_code = data.get('factor_code')
        dataset = data.get('dataset')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not all([factor_code, dataset]):
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 运行回测
        backtest_results = backtest_service.run_backtest(
            factor_code, dataset, start_date, end_date
        )
        
        return jsonify({
            'success': True,
            'results': backtest_results
        })
    
    except Exception as e:
        logger.error(f"回测错误: {str(e)}")
        return jsonify({'error': f'回测失败: {str(e)}'}), 500

@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    """获取可用数据集列表"""
    datasets = [
        {'id': 'stock_daily', 'name': '股票日频数据', 'description': '包含价格、成交量等基础数据'},
        {'id': 'stock_minute', 'name': '股票分钟数据', 'description': '高频交易数据'},
        {'id': 'financial_statements', 'name': '财务报表数据', 'description': '上市公司财务数据'},
        {'id': 'market_data', 'name': '市场数据', 'description': '指数、宏观经济数据'}
    ]
    return jsonify({'datasets': datasets})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)