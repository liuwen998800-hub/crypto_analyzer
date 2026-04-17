#!/usr/bin/env python3
"""
BTC 5分钟市场上古器 - Polymarket
抓取所有历史BTC 5分钟市场的结算数据
"""
import requests
import re
import json
import time
import os
from datetime import datetime, timezone, timedelta

DATA_FILE = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/btc_5m_all_markets.json'
PROGRESS_FILE = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/btc_5m_progress.json'

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html',
}

def extract_market_data(html, market_id):
    data = {
        'id': market_id,
        'window_start': None,
        'closed': False,
        'resolved': None,
        'price_to_beat': None,
        'final_price': None,
        'volume': None
    }
    
    em_match = re.search(r'"eventMetadata"\s*:\s*\{[^}]*?"finalPrice"\s*:\s*([0-9.]+)[^}]*?"priceToBeat"\s*:\s*([0-9.]+)[^}]*\}', html)
    if em_match:
        data['final_price'] = float(em_match.group(1))
        data['price_to_beat'] = float(em_match.group(2))
        if data['final_price'] is not None:
            data['resolved'] = 'Up' if data['final_price'] >= data['price_to_beat'] else 'Down'
    
    data['closed'] = '"closed":true' in html
    
    start_match = re.search(r'"startTime"\s*:\s*"([^"]+)"', html)
    if start_match:
        data['window_start'] = start_match.group(1)
    
    vol_match = re.search(r'"volume"\s*:\s*([0-9.]+)', html)
    if vol_match:
        data['volume'] = float(vol_match.group(1))
    
    return data

def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'last_idx': 0, 'total_fetched': 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def load_existing_data():
    """加载已有的市场数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_market_ids(start_date, end_date):
    """生成指定日期范围内的市场IDs"""
    ids = []
    current = end_date
    while current >= start_date:
        ts = int(current.timestamp())
        ids.append(ts)
        current -= timedelta(minutes=5)
    return ids

def run_scraper(days_back=30):
    """抓取指定天数的历史数据"""
    end_time = datetime(2026, 4, 16, 15, 0, tzinfo=timezone.utc)
    start_time = end_time - timedelta(days=days_back)
    
    market_ids = get_market_ids(start_time, end_time)
    print(f"总市场数: {len(market_ids)}")
    
    existing = load_existing_data()
    existing_ids = {r['id'] for r in existing}
    print(f"已存在数据: {len(existing)}")
    
    progress = load_progress()
    start_idx = progress['last_idx']
    
    all_results = existing.copy()
    new_count = 0
    errors = 0
    
    for i, mid in enumerate(market_ids[start_idx:], start=start_idx):
        if mid in existing_ids:
            continue
            
        url = f"https://polymarket.com/event/btc-updown-5m-{mid}"
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                data = extract_market_data(r.text, mid)
                if data['closed']:
                    all_results.append(data)
                    new_count += 1
        except:
            errors += 1
        
        # 每500个保存一次
        if (i + 1) % 500 == 0:
            save_data(all_results)
            progress['last_idx'] = i + 1
            progress['total_fetched'] = len(all_results)
            save_progress(progress)
            pct = (i+1)/len(market_ids)*100
            print(f"进度: {i+1}/{len(market_ids)} ({pct:.1f}%), 新增: {new_count}, 错误: {errors}")
        
        time.sleep(0.1)
    
    # 最终保存
    save_data(all_results)
    progress['last_idx'] = len(market_ids)
    progress['total_fetched'] = len(all_results)
    save_progress(progress)
    
    print(f"\n完成! 总共获取 {len(all_results)} 个市场 (新增 {new_count})")
    
    # 统计
    ups = sum(1 for r in all_results if r['resolved'] == 'Up')
    downs = sum(1 for r in all_results if r['resolved'] == 'Down')
    total_vol = sum(r['volume'] for r in all_results if r['volume'])
    
    print(f"\n统计:")
    print(f"  总市场数: {len(all_results)}")
    print(f"  Up: {ups} ({ups/len(all_results)*100:.2f}%)")
    print(f"  Down: {downs} ({downs/len(all_results)*100:.2f}%)")
    print(f"  总成交量: ${total_vol:,.2f}")
    
    return all_results

if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_scraper(days)