# Web仪表板 - 虚拟币分析系统

基于Flask的Web界面，可视化展示虚拟币分析结果。

## 功能特性

### 📊 数据可视化
- **市场总结**: 恐慌贪婪指数、信号分布、市场情绪
- **币种分析**: 各币种价格、信号、支撑阻力位
- **价格图表**: 交互式图表展示价格走势
- **风险评估**: 下跌风险、上涨潜力、风险回报比

### 🔄 实时交互
- **自动刷新**: 每30秒自动更新数据
- **手动分析**: 一键运行新的分析
- **数据导出**: 导出CSV格式分析结果
- **币种详情**: 点击查看详细分析

### 🎨 现代化界面
- **响应式设计**: 支持桌面和移动设备
- **深色主题**: 专业交易界面风格
- **信号颜色**: 5级信号用不同颜色区分
- **图表交互**: 鼠标悬停查看详细数据

## 快速开始

### 1. 启动仪表板
```bash
cd web_dashboard
chmod +x start.sh
./start.sh
```

### 2. 访问界面
打开浏览器访问: http://localhost:5000

### 3. 使用功能
- **查看市场总结**: 首页顶部显示整体市场情绪
- **查看币种分析**: 中间区域显示各币种信号
- **查看价格图表**: 底部显示价格走势图
- **查看系统状态**: 右侧边栏显示分析统计
- **查看币种详情**: 点击任意币种卡片

## API接口

### 主要接口
- `GET /api/latest` - 获取最新分析结果
- `GET /api/market_summary` - 获取市场总结
- `GET /api/coin/<symbol>` - 获取币种详情
- `GET /api/run_analysis` - 运行新的分析
- `GET /api/status` - 获取系统状态
- `GET /api/history` - 获取分析历史

### 数据格式示例
```json
{
  "timestamp": "2026-04-16T04:11:43.579760",
  "price_data": {
    "BTC": {
      "price": 74529.56,
      "change_percent": 1.037
    }
  },
  "composite_signals": {
    "BTC": {
      "signal": "NEUTRAL",
      "composite_score": 57,
      "support": 70803.082,
      "resistance": 78256.038
    }
  }
}
```

## 界面说明

### 1. 导航栏
- 系统标题和最后更新时间
- 重新分析按钮

### 2. 市场总结卡片
- **恐慌贪婪指数**: 0-100值，标记当前情绪
- **信号分布**: 各信号级别的币种数量
- **交易建议**: 基于市场情绪的建议
- **最强/最弱币种**: 识别表现最佳和最差的币种

### 3. 币种分析卡片
每个币种显示:
- **币种符号**和信号描述
- **当前价格**和24小时变化
- **综合分数**和成交量
- **支撑/阻力位**

### 4. 价格图表
- **柱状图**: 各币种价格对比
- **折线图**: 24小时变化百分比
- **交互功能**: 鼠标悬停查看详细数据

### 5. 右侧边栏
- **系统状态**: 最后分析时间、分析次数、数据大小
- **信号说明**: 各信号级别的含义
- **快速操作**: 查看所有信号、导出数据、查看历史

### 6. 币种详情模态框
点击币种卡片弹出:
- **详细信号分析**: 信号描述和分数分解
- **关键价位**: 支撑位、阻力位、距离百分比
- **风险评估**: 下跌风险、上涨潜力、风险回报比
- **交易建议**: 具体的目标价位和止损位

## 技术架构

### 前端技术
- **HTML5/CSS3**: 页面结构和样式
- **JavaScript**: 交互逻辑和数据绑定
- **Bootstrap 5**: 响应式框架
- **Chart.js**: 数据可视化图表
- **Font Awesome**: 图标库

### 后端技术
- **Flask**: Python Web框架
- **RESTful API**: 数据接口设计
- **JSON**: 数据交换格式
- **文件系统**: 结果持久化存储

### 数据流
```
分析系统 → JSON结果 → Flask API → 前端界面
   ↓           ↓           ↓          ↓
Python脚本   results/    RESTful    HTML/JS
            latest.json  接口        Chart.js
```

## 部署说明

### 开发环境
```bash
# 直接运行
python3 app.py

# 或使用启动脚本
./start.sh
```

### 生产环境
```bash
# 使用Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 使用systemd服务
sudo cp crypto-analyzer-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crypto-analyzer-web
sudo systemctl start crypto-analyzer-web
```

### Nginx反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 自定义配置

### 修改端口
编辑 `app.py`:
```python
app.run(host='0.0.0.0', port=8080, debug=False)
```

### 修改刷新频率
编辑 `index.html`:
```javascript
setInterval(loadData, 60000); // 改为60秒刷新
```

### 添加新功能
1. 在 `app.py` 中添加新的API接口
2. 在 `index.html` 中添加界面元素
3. 在JavaScript中添加交互逻辑

## 故障排除

### 常见问题
1. **无法访问界面**
   - 检查防火墙设置
   - 确认端口5000未被占用
   - 查看Flask日志输出

2. **数据不显示**
   - 检查 `../results/latest.json` 是否存在
   - 查看浏览器开发者工具控制台
   - 检查API接口是否正常响应

3. **图表不显示**
   - 检查网络连接，确保能访问CDN
   - 查看Chart.js是否加载成功
   - 检查数据格式是否正确

4. **分析失败**
   - 检查Python依赖是否安装
   - 查看分析系统日志
   - 确认网络连接正常

### 日志查看
```bash
# Flask日志
tail -f nohup.out

# 分析系统日志
tail -f ../logs/analysis.log

# 系统日志
journalctl -u crypto-analyzer-web -f
```

## 扩展开发

### 添加新图表
1. 在HTML中添加canvas元素
2. 在JavaScript中初始化Chart.js实例
3. 在API中添加对应的数据接口

### 添加新页面
1. 在 `templates/` 中添加新的HTML模板
2. 在 `app.py` 中添加路由处理
3. 在导航栏中添加链接

### 集成新数据源
1. 在分析系统中添加数据获取逻辑
2. 更新结果数据格式
3. 在前端界面中添加展示

## 性能优化

### 前端优化
- 使用CDN加载静态资源
- 启用浏览器缓存
- 压缩JavaScript和CSS
- 懒加载非关键资源

### 后端优化
- 启用Gzip压缩
- 使用缓存中间件
- 数据库连接池
- 异步任务处理

### 数据优化
- 分页加载历史数据
- 增量数据更新
- 数据预加载
- 结果缓存

## 安全建议

### 生产部署
1. 禁用调试模式
2. 使用HTTPS加密
3. 设置访问权限
4. 定期更新依赖

### 数据安全
1. API密钥安全存储
2. 输入验证和过滤
3. 防止SQL注入
4. 限制API调用频率

## 许可证

本项目基于MIT许可证开源，可自由使用和修改。