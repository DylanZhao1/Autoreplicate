// 全局变量
let currentMarkdownContent = '';
let currentExtractedInfo = {};
let currentFactorCode = '';
let backtestChart = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadDatasets();
});

// 更新状态指示器
function updateStatus(step, status) {
    const statusElement = document.getElementById(`${step}Status`);
    const statusClasses = {
        'pending': 'bg-secondary',
        'processing': 'bg-warning',
        'success': 'bg-success',
        'error': 'bg-danger'
    };
    
    const statusTexts = {
        'pending': '待处理',
        'processing': '处理中',
        'success': '已完成',
        'error': '失败'
    };
    
    // 移除所有状态类
    Object.values(statusClasses).forEach(cls => {
        statusElement.classList.remove(cls);
    });
    
    // 添加新状态类
    statusElement.classList.add(statusClasses[status]);
    statusElement.textContent = statusTexts[status];
}

// 启用/禁用按钮
function toggleButton(buttonId, enabled) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = !enabled;
    }
}

// 启用/禁用输入框
function toggleInputs(inputIds, enabled) {
    inputIds.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.disabled = !enabled;
        }
    });
}

// 上传PDF文件
async function uploadPDF() {
    const fileInput = document.getElementById('pdfFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('请选择PDF文件');
        return;
    }
    
    updateStatus('pdf', 'processing');
    showLoading('PDF上传');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload_pdf', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentMarkdownContent = result.markdown_content;
            document.getElementById('markdownContent').textContent = result.markdown_content;
            Prism.highlightElement(document.getElementById('markdownContent'));
            showResult('markdownResult');
            updateStatus('pdf', 'success');
            
            // 启用下一步
            toggleButton('extractBtn', true);
        } else {
            alert('转换失败: ' + result.error);
            updateStatus('pdf', 'error');
        }
    } catch (error) {
        alert('上传失败: ' + error.message);
        updateStatus('pdf', 'error');
    } finally {
        hideLoading('PDF上传');
    }
}

// 提取内容
async function extractContent() {
    if (!currentMarkdownContent) {
        alert('请先上传并转换PDF文件');
        return;
    }
    
    updateStatus('extract', 'processing');
    showLoading('内容提取');
    
    try {
        const response = await fetch('/api/extract_content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                markdown_content: currentMarkdownContent
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentExtractedInfo = result.extracted_info;
            displayExtractionResults(result.extracted_info);
            showResult('extractionResult');
            updateStatus('extract', 'success');
            
            // 启用下一步
            toggleButton('generateBtn', true);
        } else {
            alert('提取失败: ' + result.error);
            updateStatus('extract', 'error');
        }
    } catch (error) {
        alert('提取失败: ' + error.message);
        updateStatus('extract', 'error');
    } finally {
        hideLoading('内容提取');
    }
}

// 显示提取结果
// 显示提取结果
function displayExtractionResults(info) {
    // 数据集信息
    const datasetHtml = `
        <p><strong>主要数据源:</strong> ${info.datasets?.primary || '未知'}</p>
        <p><strong>时间范围:</strong> ${info.datasets?.time_range || '未知'}</p>
        <p><strong>数据频率:</strong> ${info.datasets?.frequency || '未知'}</p>
    `;
    document.getElementById('datasetInfo').innerHTML = datasetHtml;
    
    // 核心问题
    document.getElementById('coreProblem').innerHTML = `<p>${info.core_problem || '未提取到核心问题'}</p>`;
    
    // 解决方案
    const solutionHtml = `
        <p><strong>方法:</strong> ${info.solution?.method || '未知'}</p>
        <p><strong>算法:</strong> ${info.solution?.algorithm || '未知'}</p>
        <p><strong>策略:</strong> ${info.solution?.strategy || '未知'}</p>
    `;
    document.getElementById('solution').innerHTML = solutionHtml;
    
    // 关键因子 - 添加类型检查和错误处理
    let factorsHtml = '';
    
    // 检查key_factors是否存在且为数组
    if (info.key_factors && Array.isArray(info.key_factors)) {
        factorsHtml = info.key_factors.map(factor => 
            `<div class="mb-2">
                <strong>${factor.name || '未知因子'}:</strong> ${factor.description || '无描述'}
                <span class="badge bg-secondary">${factor.type || '未分类'}</span>
            </div>`
        ).join('');
    } else if (info.key_factors && typeof info.key_factors === 'string') {
        // 如果是字符串，尝试解析为JSON
        try {
            const parsedFactors = JSON.parse(info.key_factors);
            if (Array.isArray(parsedFactors)) {
                factorsHtml = parsedFactors.map(factor => 
                    `<div class="mb-2">
                        <strong>${factor.name || '未知因子'}:</strong> ${factor.description || '无描述'}
                        <span class="badge bg-secondary">${factor.type || '未分类'}</span>
                    </div>`
                ).join('');
            } else {
                factorsHtml = '<div class="alert alert-warning">关键因子数据格式错误</div>';
            }
        } catch (e) {
            factorsHtml = `<div class="alert alert-warning">关键因子解析失败: ${info.key_factors}</div>`;
        }
    } else if (info.key_factors && typeof info.key_factors === 'object') {
        // 如果是对象，尝试转换为数组
        const factorArray = Object.entries(info.key_factors).map(([key, value]) => ({
            name: key,
            description: typeof value === 'string' ? value : JSON.stringify(value),
            type: '提取的因子'
        }));
        factorsHtml = factorArray.map(factor => 
            `<div class="mb-2">
                <strong>${factor.name}:</strong> ${factor.description}
                <span class="badge bg-secondary">${factor.type}</span>
            </div>`
        ).join('');
    } else {
        factorsHtml = '<div class="alert alert-info">未提取到关键因子信息</div>';
    }
    
    document.getElementById('keyFactors').innerHTML = factorsHtml;
    
    // 添加调试信息到控制台
    console.log('提取的信息:', info);
    console.log('key_factors类型:', typeof info.key_factors);
    console.log('key_factors内容:', info.key_factors);
}

// 生成因子代码
async function generateFactor() {
    if (!currentExtractedInfo || Object.keys(currentExtractedInfo).length === 0) {
        alert('请先提取论文内容');
        return;
    }
    
    updateStatus('factor', 'processing');
    showLoading('因子生成');
    
    try {
        const response = await fetch('/api/generate_factor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extracted_info: currentExtractedInfo
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentFactorCode = result.factor_code;
            document.getElementById('factorCode').textContent = result.factor_code;
            Prism.highlightElement(document.getElementById('factorCode'));
            showResult('factorResult');
            updateStatus('factor', 'success');
            
            // 启用编辑和回测功能
            toggleButton('editBtn', true);
            toggleButton('backtestBtn', true);
            toggleInputs(['datasetSelect', 'startDate', 'endDate'], true);
        } else {
            alert('生成失败: ' + result.error);
            updateStatus('factor', 'error');
        }
    } catch (error) {
        alert('生成失败: ' + error.message);
        updateStatus('factor', 'error');
    } finally {
        hideLoading('因子生成');
    }
}

// 编辑代码
function editCode() {
    document.getElementById('codeEditor').value = currentFactorCode;
    const modal = new bootstrap.Modal(document.getElementById('codeEditModal'));
    modal.show();
}

// 保存代码
function saveCode() {
    currentFactorCode = document.getElementById('codeEditor').value;
    document.getElementById('factorCode').textContent = currentFactorCode;
    Prism.highlightElement(document.getElementById('factorCode'));
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('codeEditModal'));
    modal.hide();
}

// 加载数据集列表
async function loadDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const result = await response.json();
        
        const select = document.getElementById('datasetSelect');
        select.innerHTML = '<option value="">请选择数据集</option>';
        
        result.datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.id;
            option.textContent = `${dataset.name} - ${dataset.description}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载数据集失败:', error);
    }
}

// 运行回测
async function runBacktest() {
    if (!currentFactorCode) {
        alert('请先生成因子代码');
        return;
    }
    
    const dataset = document.getElementById('datasetSelect').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!dataset) {
        alert('请选择数据集');
        return;
    }
    
    updateStatus('backtest', 'processing');
    showLoading('回测分析');
    
    try {
        const response = await fetch('/api/run_backtest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                factor_code: currentFactorCode,
                dataset: dataset,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayBacktestResults(result.results);
            showResult('backtestResult');
            updateStatus('backtest', 'success');
        } else {
            alert('回测失败: ' + result.error);
            updateStatus('backtest', 'error');
        }
    } catch (error) {
        alert('回测失败: ' + error.message);
        updateStatus('backtest', 'error');
    } finally {
        hideLoading('回测分析');
    }
}

// 显示回测结果
function displayBacktestResults(results) {
    // 显示绩效统计
    const statsHtml = Object.entries(results.performance_stats).map(([strategy, stats]) => {
        const strategyName = {
            'Q1_return': 'Q1 (最低)',
            'Q2_return': 'Q2',
            'Q3_return': 'Q3',
            'Q4_return': 'Q4',
            'Q5_return': 'Q5 (最高)',
            'long_short': '多空策略'
        }[strategy] || strategy;
        
        return `
            <div class="card mb-2">
                <div class="card-body p-2">
                    <h6 class="card-title mb-1">${strategyName}</h6>
                    <small class="text-muted">
                        年化收益: <span class="text-primary">${stats.annual_return}%</span> | 
                        波动率: ${stats.annual_volatility}% | 
                        夏普: ${stats.sharpe_ratio} | 
                        最大回撤: <span class="text-danger">${stats.max_drawdown}%</span>
                    </small>
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('performanceStats').innerHTML = statsHtml;
    
    // 绘制累计收益率图表
    drawReturnsChart(results.cumulative_returns);
}

// 绘制收益率图表
function drawReturnsChart(data) {
    const ctx = document.getElementById('returnsChart').getContext('2d');
    
    // 销毁现有图表
    if (backtestChart) {
        backtestChart.destroy();
    }
    
    backtestChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Q1 (最低)',
                    data: data.Q1,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Q2',
                    data: data.Q2,
                    borderColor: 'rgb(255, 159, 64)',
                    backgroundColor: 'rgba(255, 159, 64, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Q3',
                    data: data.Q3,
                    borderColor: 'rgb(255, 205, 86)',
                    backgroundColor: 'rgba(255, 205, 86, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Q4',
                    data: data.Q4,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Q5 (最高)',
                    data: data.Q5,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: '多空策略',
                    data: data.long_short,
                    borderColor: 'rgb(153, 102, 255)',
                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '因子分层累计收益率对比'
                },
                legend: {
                    position: 'top'
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '日期'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: '累计收益率'
                    },
                    ticks: {
                        callback: function(value) {
                            return (value * 100).toFixed(1) + '%';
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// 显示加载状态
function showLoading(context) {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(el => {
        if (el.closest('.card').querySelector('.card-header').textContent.includes(context.split(' ')[0])) {
            el.style.display = 'block';
        }
    });
}

// 隐藏加载状态
function hideLoading(context) {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(el => {
        if (el.closest('.card').querySelector('.card-header').textContent.includes(context.split(' ')[0])) {
            el.style.display = 'none';
        }
    });
}

// 显示结果区域
function showResult(resultId) {
    const result = document.getElementById(resultId);
    if (result) {
        result.style.display = 'block';
    }
}