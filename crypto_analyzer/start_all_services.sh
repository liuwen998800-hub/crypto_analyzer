#!/bin/bash
# 一键启动所有服务脚本

echo "🚀 启动AI量化交易系统所有服务"
echo "============================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到python3，请先安装Python3${NC}"
    exit 1
fi

# 检查目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📁 工作目录: $(pwd)${NC}"

# 函数：检查端口是否被占用
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $port 已被占用 ($service)${NC}"
        return 1
    else
        echo -e "${GREEN}✅ 端口 $port 可用${NC}"
        return 0
    fi
}

# 函数：启动服务
start_service() {
    local name=$1
    local command=$2
    local log_file=$3
    
    echo -e "\n${BLUE}▶️  启动 $name...${NC}"
    echo "命令: $command"
    echo "日志: $log_file"
    
    # 在后台运行服务
    eval "$command > \"$log_file\" 2>&1 &"
    local pid=$!
    
    # 保存PID到文件
    echo $pid > "/tmp/${name}_pid.txt"
    
    # 等待服务启动
    sleep 3
    
    if ps -p $pid > /dev/null; then
        echo -e "${GREEN}✅ $name 启动成功 (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}❌ $name 启动失败${NC}"
        echo "查看日志: tail -f $log_file"
        return 1
    fi
}

# 检查端口
echo -e "\n${BLUE}🔍 检查端口占用情况...${NC}"
check_port 5000 "AI分析系统"
check_port 5001 "FMZ集成API"

# 创建日志目录
mkdir -p logs

# 1. 启动AI分析系统（端口5000）
start_service "AI分析系统" \
    "python3 web_dashboard/app.py" \
    "logs/ai_system.log"

# 2. 启动FMZ集成API（端口5001）
start_service "FMZ集成API" \
    "python3 src/fmz/fmz_api.py" \
    "logs/fmz_api.log"

# 3. 启动FMZ集成测试服务（可选）
echo -e "\n${BLUE}▶️  启动FMZ集成测试服务...${NC}"
python3 src/fmz/ai_fmz_integration.py > logs/fmz_integration.log 2>&1 &
FMZ_TEST_PID=$!
echo $FMZ_TEST_PID > /tmp/fmz_test_pid.txt
echo -e "${GREEN}✅ FMZ集成测试服务启动 (PID: $FMZ_TEST_PID)${NC}"

# 等待所有服务启动
echo -e "\n${BLUE}⏳ 等待服务启动...${NC}"
sleep 5

# 检查服务状态
echo -e "\n${BLUE}🔍 检查服务状态...${NC}"

check_service() {
    local name=$1
    local url=$2
    local pid_file=$3
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null; then
            echo -e "${GREEN}✅ $name 运行中 (PID: $pid)${NC}"
            
            # 尝试访问服务
            if curl -s --head --request GET "$url" > /dev/null 2>&1; then
                echo -e "   🌐 服务可访问: $url"
            else
                echo -e "${YELLOW}   ⚠️  服务可能未就绪: $url${NC}"
            fi
        else
            echo -e "${RED}❌ $name 已停止${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  $name PID文件不存在${NC}"
    fi
}

check_service "AI分析系统" "http://localhost:5000" "/tmp/AI分析系统_pid.txt"
check_service "FMZ集成API" "http://localhost:5001/api/fmz/status" "/tmp/FMZ集成API_pid.txt"

# 显示服务信息
echo -e "\n${BLUE}📊 服务信息汇总${NC}"
echo "============================================================"
echo -e "${GREEN}✅ AI分析系统${NC}"
echo "   地址: http://localhost:5000"
echo "   功能: 实时市场分析、AI模型预测、技术指标"
echo ""
echo -e "${GREEN}✅ FMZ集成API${NC}"
echo "   地址: http://localhost:5001"
echo "   功能: 连接FMZ平台、执行AI交易信号"
echo ""
echo -e "${GREEN}✅ FMZ集成测试服务${NC}"
echo "   功能: 监控AI信号、自动交易执行"
echo ""
echo -e "${YELLOW}📁 日志文件${NC}"
echo "   AI分析系统: logs/ai_system.log"
echo "   FMZ集成API: logs/fmz_api.log"
echo "   FMZ集成测试: logs/fmz_integration.log"

# 显示测试命令
echo -e "\n${BLUE}🧪 测试命令${NC}"
echo "============================================================"
echo "1. 测试AI分析系统:"
echo "   curl http://localhost:5000/api/analyze"
echo ""
echo "2. 测试FMZ集成API:"
echo "   curl http://localhost:5001/api/fmz/status"
echo ""
echo "3. 运行FMZ集成测试:"
echo "   python3 test_fmz_integration.py"
echo ""
echo "4. 运行简单测试:"
echo "   python3 test_fmz_simple.py"

# 显示停止命令
echo -e "\n${RED}🛑 停止所有服务${NC}"
echo "============================================================"
echo "运行以下命令停止所有服务:"
echo "   pkill -f 'python3 web_dashboard/app.py'"
echo "   pkill -f 'python3 src/fmz/fmz_api.py'"
echo "   pkill -f 'python3 src/fmz/ai_fmz_integration.py'"
echo ""
echo "或使用:"
echo "   ./stop_all_services.sh"

# 创建停止脚本
cat > stop_all_services.sh << 'EOF'
#!/bin/bash
# 停止所有服务脚本

echo "🛑 停止AI量化交易系统所有服务"
echo "============================================================"

# 停止AI分析系统
echo "停止AI分析系统..."
pkill -f "python3 web_dashboard/app.py"

# 停止FMZ集成API
echo "停止FMZ集成API..."
pkill -f "python3 src/fmz/fmz_api.py"

# 停止FMZ集成测试
echo "停止FMZ集成测试..."
pkill -f "python3 src/fmz/ai_fmz_integration.py"

# 删除PID文件
rm -f /tmp/*_pid.txt

echo "✅ 所有服务已停止"
EOF

chmod +x stop_all_services.sh

echo -e "\n${GREEN}✅ 所有服务启动完成！${NC}"
echo ""
echo -e "${YELLOW}💡 下一步操作:${NC}"
echo "1. 访问AI分析面板: http://localhost:5000"
echo "2. 配置FMZ平台交易所API"
echo "3. 启动FMZ托管者 (Docker)"
echo "4. 创建并运行AI交易策略"
echo ""
echo -e "${BLUE}📝 注意:${NC}"
echo "- 首次使用需要配置FMZ平台"
echo "- 建议先使用模拟账户测试"
echo "- 监控日志文件查看运行状态"

# 保持脚本运行（可选）
echo -e "\n按 Ctrl+C 停止所有服务并退出"
echo "============================================================"

# 等待用户中断
trap 'echo -e "\n${RED}正在停止所有服务...${NC}"; ./stop_all_services.sh; exit 0' INT

# 显示实时日志（可选）
echo -e "\n${YELLOW}📋 查看实时日志:${NC}"
echo "   终端1: tail -f logs/ai_system.log"
echo "   终端2: tail -f logs/fmz_api.log"
echo "   终端3: tail -f logs/fmz_integration.log"

# 保持脚本运行
while true; do
    sleep 60
    echo -e "\n${BLUE}⏰ 系统运行中... $(date)${NC}"
done