#!/bin/bash
# 虚拟币分析指标产品 - 安装脚本

set -e

echo "================================================================"
echo "虚拟币分析指标产品 - 安装脚本"
echo "================================================================"

# 检查Python版本
echo "检查Python版本..."
python3 --version || { echo "❌ 需要Python 3.8或更高版本"; exit 1; }

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv || { echo "❌ 创建虚拟环境失败"; exit 1; }

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 安装TA-Lib（可能需要系统依赖）
echo "安装TA-Lib..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y build-essential python3-dev
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    cd ..
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
    pip install TA-Lib
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum groupinstall -y "Development Tools"
    sudo yum install -y python3-devel
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    cd ..
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
    pip install TA-Lib
else
    echo "⚠️  无法自动安装TA-Lib，请手动安装或使用备用方案"
    echo "    pip install ta  # 使用纯Python实现的TA库"
fi

# 创建目录结构
echo "创建目录结构..."
mkdir -p logs results reports data

# 复制配置文件
echo "配置API密钥..."
if [ ! -f config/api_keys.yaml ]; then
    cp config/api_keys.example.yaml config/api_keys.yaml
    echo "✅ 已创建配置文件: config/api_keys.yaml"
    echo "⚠️  请编辑此文件配置您的API密钥"
else
    echo "✅ 配置文件已存在"
fi

# 测试安装
echo "测试安装..."
python scripts/test_connection.py

echo "================================================================"
echo "安装完成！"
echo ""
echo "下一步操作:"
echo "1. 编辑 config/api_keys.yaml 配置API密钥"
echo "2. 运行测试: python scripts/test_connection.py"
echo "3. 运行分析: python scripts/hourly_analysis.py"
echo "4. 启动调度: python scripts/scheduler_service.py"
echo ""
echo "API密钥配置说明:"
echo "- Binance API: 可选，免费层有限制"
echo "- DeepSeek API: 需要，从 https://platform.deepseek.com/ 获取"
echo "- MiniMax API: 需要，从 https://api.minimax.chat/ 获取"
echo "================================================================"