# 虚拟币分析指标产品

基于DeepSeek + MiniMax双模型的技术分析系统，每小时生成BTC/ETH/SOL的交易信号报告。

## 功能特性

1. **双AI模型分析**: DeepSeek + MiniMax互补分析
2. **技术指标评分**: 基于现有评分体系
3. **恐慌情绪计算**: 综合市场情绪分析
4. **支撑阻力位**: 专业级技术位计算
5. **1小时报表**: 结构化数据输出

## 系统架构

```
数据源层 → 分析层 → 信号层 → 输出层
   ↓         ↓         ↓         ↓
 Binance   技术指标  综合信号   报表/API
   ↓        AI模型   置信度    可视化
 价格数据  情绪分析  支撑阻力  数据库
```

## 安装部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API密钥
cp config/api_keys.example.yaml config/api_keys.yaml
# 编辑配置文件，填入DeepSeek、MiniMax、Binance等API密钥

# 3. 运行测试
python scripts/test_connection.py

# 4. 启动调度服务
python scripts/scheduler_service.py
```

## 输出格式

每小时生成JSON报告，包含：
- 三种币种(BTC/ETH/SOL)的实时分析
- 技术评分 + AI置信度
- 支撑阻力位
- 综合交易信号
- 详细分析摘要