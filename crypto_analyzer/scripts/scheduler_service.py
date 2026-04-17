#!/usr/bin/env python3
"""
调度服务
每小时自动运行分析任务
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.hourly_analysis import HourlyAnalyzer


class AnalysisScheduler:
    """分析任务调度器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化调度器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir or str(project_root / 'config')
        self._setup_logging()
        
        # 创建分析器
        self.analyzer = HourlyAnalyzer(self.config_dir)
        
        # 创建调度器
        self.scheduler = BackgroundScheduler()
        
        # 配置
        self.schedule_config = {
            'analysis_interval_hours': 1,  # 每小时运行一次
            'run_at_minute': 0,  # 在每小时的第0分钟运行
            'timezone': 'Asia/Shanghai'
        }
        
        logger.info("分析调度器初始化完成")
    
    def _setup_logging(self):
        """配置日志"""
        global logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(project_root / 'logs' / 'scheduler.log'),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        
        # 创建日志目录
        (project_root / 'logs').mkdir(exist_ok=True)
    
    def run_analysis(self):
        """运行分析任务"""
        logger.info("开始执行分析任务...")
        start_time = time.time()
        
        try:
            # 执行分析
            results = self.analyzer.analyze_all_symbols(['BTC', 'ETH', 'SOL'])
            
            # 记录执行结果
            end_time = time.time()
            execution_time = end_time - start_time
            
            success_count = results.get('metadata', {}).get('success_count', 0)
            total_count = len(results.get('results', {}))
            
            logger.info(f"分析任务完成，耗时: {execution_time:.1f}秒")
            logger.info(f"成功分析: {success_count}/{total_count}个币种")
            
            # 记录市场情绪
            market_sentiment = results.get('market_summary', {}).get('market_sentiment', 'unknown')
            logger.info(f"市场情绪: {market_sentiment}")
            
            # 记录各币种信号
            for symbol, result in results.get('results', {}).items():
                if result.get('error', False):
                    logger.warning(f"{symbol}: 分析失败 - {result.get('error_message', '未知错误')}")
                else:
                    signal = result.get('trading_signal', {}).get('signal', 'UNKNOWN')
                    score = result.get('trading_signal', {}).get('score', 0)
                    logger.info(f"{symbol}: {signal} (分数: {score})")
            
            return True
            
        except Exception as e:
            logger.error(f"分析任务执行失败: {e}")
            return False
    
    def schedule_hourly_analysis(self):
        """调度每小时分析任务"""
        # 创建cron触发器，每小时的第0分钟运行
        trigger = CronTrigger(
            minute=self.schedule_config['run_at_minute'],
            timezone=self.schedule_config['timezone']
        )
        
        # 添加任务
        self.scheduler.add_job(
            self.run_analysis,
            trigger=trigger,
            id='hourly_analysis',
            name='每小时虚拟币分析',
            replace_existing=True
        )
        
        logger.info(f"已调度每小时分析任务，将在每小时的第{self.schedule_config['run_at_minute']}分钟运行")
    
    def schedule_daily_report(self, hour: int = 9, minute: int = 0):
        """调度每日报告任务"""
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=self.schedule_config['timezone']
        )
        
        self.scheduler.add_job(
            self.generate_daily_report,
            trigger=trigger,
            id='daily_report',
            name='每日分析报告',
            replace_existing=True
        )
        
        logger.info(f"已调度每日报告任务，将在每天{hour:02d}:{minute:02d}运行")
    
    def generate_daily_report(self):
        """生成每日报告"""
        logger.info("开始生成每日报告...")
        
        try:
            # 获取最近24小时的分析结果
            report_data = self._collect_daily_data()
            
            # 生成报告
            report = self._create_daily_report(report_data)
            
            # 保存报告
            self._save_daily_report(report)
            
            logger.info("每日报告生成完成")
            return True
            
        except Exception as e:
            logger.error(f"生成每日报告失败: {e}")
            return False
    
    def _collect_daily_data(self):
        """收集每日数据"""
        results_dir = project_root / 'results'
        
        if not results_dir.exists():
            return {}
        
        # 获取最近24小时的文件
        daily_files = []
        now = datetime.now()
        
        for file in results_dir.glob('analysis_*.json'):
            try:
                # 从文件名提取时间
                filename = file.stem
                timestamp_str = filename.replace('analysis_', '')
                file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                # 检查是否在最近24小时内
                if now - file_time <= timedelta(hours=24):
                    daily_files.append((file_time, file))
            except:
                continue
        
        # 按时间排序
        daily_files.sort(key=lambda x: x[0])
        
        return {
            'files': daily_files,
            'count': len(daily_files),
            'period': '24h'
        }
    
    def _create_daily_report(self, data):
        """创建每日报告"""
        import json
        
        files = data.get('files', [])
        
        if not files:
            return {
                'timestamp': datetime.now().isoformat(),
                'period': '24h',
                'analysis_count': 0,
                'message': '过去24小时内无分析数据'
            }
        
        # 读取所有文件
        all_results = []
        for file_time, file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    result['file_time'] = file_time.isoformat()
                    all_results.append(result)
            except:
                continue
        
        # 分析趋势
        trends = self._analyze_trends(all_results)
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'period': '24h',
            'analysis_count': len(all_results),
            'symbols_analyzed': ['BTC', 'ETH', 'SOL'],
            'trends': trends,
            'summary': self._generate_daily_summary(trends),
            'recommendations': self._generate_daily_recommendations(trends),
            'files_analyzed': [str(f[1]) for f in files]
        }
        
        return report
    
    def _analyze_trends(self, all_results):
        """分析趋势"""
        trends = {
            'BTC': {'signals': [], 'scores': []},
            'ETH': {'signals': [], 'scores': []},
            'SOL': {'signals': [], 'scores': []}
        }
        
        for result in all_results:
            for symbol, data in result.get('results', {}).items():
                if symbol in trends and not data.get('error', False):
                    signal = data.get('trading_signal', {})
                    trends[symbol]['signals'].append(signal.get('signal', 'NEUTRAL'))
                    trends[symbol]['scores'].append(signal.get('score', 50))
        
        # 计算统计信息
        for symbol in trends:
            signals = trends[symbol]['signals']
            scores = trends[symbol]['scores']
            
            if signals:
                trends[symbol]['signal_count'] = len(signals)
                trends[symbol]['avg_score'] = sum(scores) / len(scores) if scores else 0
                
                # 计算信号一致性
                buy_count = signals.count('BUY') + signals.count('STRONG_BUY')
                sell_count = signals.count('SELL') + signals.count('STRONG_SELL')
                total = len(signals)
                
                trends[symbol]['buy_ratio'] = buy_count / total if total > 0 else 0
                trends[symbol]['sell_ratio'] = sell_count / total if total > 0 else 0
                trends[symbol]['consistency'] = max(buy_count, sell_count) / total if total > 0 else 0
                
                # 确定趋势
                if buy_count > sell_count:
                    trends[symbol]['trend'] = 'bullish'
                elif sell_count > buy_count:
                    trends[symbol]['trend'] = 'bearish'
                else:
                    trends[symbol]['trend'] = 'neutral'
        
        return trends
    
    def _generate_daily_summary(self, trends):
        """生成每日总结"""
        summary = []
        
        for symbol, data in trends.items():
            if 'trend' in data:
                trend = data['trend']
                avg_score = data.get('avg_score', 0)
                consistency = data.get('consistency', 0) * 100
                
                if trend == 'bullish':
                    summary.append(f"{symbol}: 看涨趋势，平均分数{avg_score:.1f}，一致性{consistency:.1f}%")
                elif trend == 'bearish':
                    summary.append(f"{symbol}: 看跌趋势，平均分数{avg_score:.1f}，一致性{consistency:.1f}%")
                else:
                    summary.append(f"{symbol}: 震荡趋势，平均分数{avg_score:.1f}，无明显方向")
        
        return summary
    
    def _generate_daily_recommendations(self, trends):
        """生成每日建议"""
        recommendations = []
        
        for symbol, data in trends.items():
            if 'trend' in data:
                trend = data['trend']
                consistency = data.get('consistency', 0)
                
                if trend == 'bullish' and consistency > 0.7:
                    recommendations.append(f"{symbol}: 趋势明确看涨，可考虑逢低买入")
                elif trend == 'bearish' and consistency > 0.7:
                    recommendations.append(f"{symbol}: 趋势明确看跌，建议减仓或观望")
                elif consistency < 0.5:
                    recommendations.append(f"{symbol}: 信号矛盾，建议轻仓或等待明确方向")
                else:
                    recommendations.append(f"{symbol}: 趋势不明，以技术分析为主")
        
        return recommendations
    
    def _save_daily_report(self, report):
        """保存每日报告"""
        reports_dir = project_root / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d')
        report_path = reports_dir / f'daily_report_{timestamp}.json'
        
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"每日报告已保存: {report_path}")
    
    def start(self):
        """启动调度器"""
        logger.info("启动分析调度器...")
        
        # 添加任务
        self.schedule_hourly_analysis()
        self.schedule_daily_report()
        
        # 立即运行一次分析（测试）
        logger.info("执行初始分析...")
        self.run_analysis()
        
        # 启动调度器
        self.scheduler.start()
        logger.info("调度器已启动")
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("收到停止信号，正在关闭调度器...")
            self.stop()
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已停止")


def main():
    """主函数"""
    print("=" * 60)
    print("虚拟币分析指标产品 - 调度服务")
    print("=" * 60)
    print("服务将每小时自动运行分析任务")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    
    # 创建调度器
    scheduler = AnalysisScheduler()
    
    # 启动服务
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()