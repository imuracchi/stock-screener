#!/usr/bin/env python3
"""
日本株スクリーナー - 勝率統計自動記録版 - 206銘柄
買いシグナル: SMA10>SMA20>SMA75 + RSI40-55反発 + MACDゴールデンクロス
売りシグナル: SMA10<SMA20<SMA75 + RSI60-50下げ + MACDデッドクロス
勝率統計を自動記録・更新
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import traceback
import sys

SERVICE_ACCOUNT_FILE = 'trading-493802-dc7fdcabd29e.json'
SPREADSHEET_ID = '13VGvzxKR8nNRm29NjlM2Nj-vA7D9yateXFm_szUJGW8'

print("=" * 80)
print("日本株スクリーナー - 勝率統計自動記録版 - 206銘柄 - 開始")
print("=" * 80)

try:
    with open(SERVICE_ACCOUNT_FILE) as f:
        creds_dict = json.load(f)
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ])
    gc = gspread.authorize(creds)
    print("✅ Google Sheets 認証成功\n")
except Exception as e:
    print(f"❌ 認証エラー: {e}")
    traceback.print_exc()
    input("\nEnterキーを押して終了...")
    sys.exit(1)

STOCKS = [
    '1301.T', '1305.T', '1306.T', '1308.T', '1309.T', '1311.T', '1319.T', '1320.T', '1321.T', '1322.T',
    '1324.T', '1325.T', '1326.T', '1328.T', '1329.T', '1330.T', '1332.T', '1333.T', '1335.T', '1340.T',
    '1343.T', '1345.T', '1346.T', '1348.T', '1349.T', '1356.T', '1357.T', '1358.T', '1360.T', '1365.T',
    '1366.T', '1367.T', '1368.T', '1369.T', '1375.T', '1380.T', '1381.T', '1382.T', '1383.T', '1384.T',
    '1397.T', '1398.T', '1399.T', '1401.T', '1407.T', '1414.T', '1417.T', '1418.T', '1419.T', '1420.T',
    '1429.T', '1430.T', '1431.T', '1432.T', '1433.T', '1434.T', '1435.T', '1436.T', '1438.T', '1443.T',
    '1444.T', '1445.T', '1446.T', '1447.T', '1450.T', '1605.T', '1808.T', '1925.T', '2001.T', '2002.T',
    '2003.T', '2004.T', '2009.T', '2011.T', '2012.T', '2013.T', '2014.T', '2015.T', '2016.T', '2017.T',
    '2018.T', '2019.T', '2108.T', '2109.T', '2112.T', '2114.T', '2117.T', '2120.T', '2121.T', '2122.T',
    '2124.T', '2201.T', '2204.T', '2206.T', '2207.T', '2208.T', '2209.T', '2211.T', '2212.T', '2215.T',
    '2216.T', '2217.T', '2220.T', '2221.T', '2222.T', '2224.T', '2226.T', '2229.T', '2914.T', '3001.T',
    '3002.T', '3003.T', '3004.T', '3010.T', '3011.T', '3020.T', '3101.T', '3103.T', '3104.T', '3105.T',
    '3106.T', '3107.T', '3109.T', '3110.T', '3111.T', '3113.T', '3116.T', '3121.T', '3123.T', '3382.T',
    '3407.T', '4004.T', '4005.T', '4008.T', '4011.T', '4012.T', '4013.T', '4014.T', '4015.T', '4016.T',
    '4017.T', '4019.T', '4020.T', '4064.T', '4100.T', '4102.T', '4107.T', '4204.T', '4205.T', '4208.T',
    '4324.T', '4502.T', '4503.T', '4506.T', '4519.T', '4689.T', '5000.T', '5010.T', '5101.T', '5103.T',
    '5105.T', '5108.T', '5401.T', '5411.T', '5631.T', '5801.T', '6594.T', '6674.T', '6701.T', '6758.T',
    '6861.T', '7011.T', '7201.T', '7202.T', '7205.T', '7211.T', '7270.T', '7272.T', '7309.T', '8035.T',
    '8053.T', '8058.T', '8308.T', '8309.T', '8411.T', '8801.T', '8802.T', '8830.T', '8938.T', '8960.T',
    '8968.T', '9005.T', '9006.T', '9007.T', '9008.T', '9009.T', '9010.T', '9020.T', '9022.T', '9064.T',
    '9101.T', '9104.T', '9107.T', '9766.T', '9983.T', '9984.T',
]

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_signal(df):
    if df is None or df.empty or len(df) < 80:
        return None
    
    close = df['Close']
    sma10 = close.rolling(10).mean()
    sma20 = close.rolling(20).mean()
    sma75 = close.rolling(75).mean()
    rsi = calculate_rsi(close)
    
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9).mean()
    
    idx = len(df) - 1
    signals = []
    
    # 買いシグナル
    if (sma10.iloc[idx] > sma20.iloc[idx] > sma75.iloc[idx] and
        40 <= rsi.iloc[idx] <= 55 and
        rsi.iloc[idx-1] < rsi.iloc[idx] and
        macd.iloc[idx-1] < macd_signal.iloc[idx-1] and
        macd.iloc[idx] > macd_signal.iloc[idx]):
        
        signals.append({
            'type': 'BUY',
            'conditions': f'トレンド上昇+RSI反発({rsi.iloc[idx]:.1f})+MACDゴールデンクロス',
            'entry_price': round(float(close.iloc[idx]), 2),
            'sma10': round(float(sma10.iloc[idx]), 2),
            'sma20': round(float(sma20.iloc[idx]), 2),
            'sma75': round(float(sma75.iloc[idx]), 2),
            'rsi': round(float(rsi.iloc[idx]), 2),
            'macd': round(float(macd.iloc[idx]), 6),
        })
    
    # 売りシグナル
    if (sma10.iloc[idx] < sma20.iloc[idx] < sma75.iloc[idx] and
        50 <= rsi.iloc[idx] <= 60 and
        rsi.iloc[idx-1] > rsi.iloc[idx] and
        macd.iloc[idx-1] > macd_signal.iloc[idx-1] and
        macd.iloc[idx] < macd_signal.iloc[idx]):
        
        signals.append({
            'type': 'SELL',
            'conditions': f'トレンド下降+RSI下げ({rsi.iloc[idx]:.1f})+MACDデッドクロス',
            'entry_price': round(float(close.iloc[idx]), 2),
            'sma10': round(float(sma10.iloc[idx]), 2),
            'sma20': round(float(sma20.iloc[idx]), 2),
            'sma75': round(float(sma75.iloc[idx]), 2),
            'rsi': round(float(rsi.iloc[idx]), 2),
            'macd': round(float(macd.iloc[idx]), 6),
        })
    
    return signals if signals else None

def update_signal_history(sheet, buy_signals, sell_signals):
    """シグナル履歴を追加"""
    try:
        ws = sheet.worksheet("シグナル履歴")
    except:
        # シート未作成なら作成
        ws = sheet.add_worksheet(title="シグナル履歴", rows=1000, cols=10)
        ws.append_row(['日付', '銘柄', 'シグナル', 'エントリー価格', '条件', 'SMA10', 'SMA20', 'SMA75', 'RSI', 'MACD'])
    
    today = str(datetime.now().date())
    
    for sig in buy_signals + sell_signals:
        ws.append_row([
            today,
            sig['ticker'],
            sig['type'],
            sig['entry_price'],
            sig['conditions'],
            sig['sma10'],
            sig['sma20'],
            sig['sma75'],
            sig['rsi'],
            sig['macd']
        ])

def evaluate_past_signals(sheet):
    """過去のシグナルを評価し、勝率統計を更新"""
    try:
        hist_ws = sheet.worksheet("シグナル履歴")
        records = hist_ws.get_all_records()
    except:
        return
    
    if not records:
        return
    
    # 過去 5 日間のシグナルを評価
    five_days_ago = datetime.now() - timedelta(days=5)
    
    win_count = 0
    lose_count = 0
    total_profit_rate = 0
    
    for record in records[-50:]:  # 直近 50 件を評価
        try:
            signal_date = datetime.strptime(record['日付'], '%Y-%m-%d')
            if signal_date < five_days_ago:
                continue
            
            ticker = record['銘柄']
            entry_price = float(record['エントリー価格'])
            signal_type = record['シグナル']
            
            # 現在価格を取得
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period='5d')
            
            if df.empty:
                continue
            
            current_price = float(df['Close'].iloc[-1])
            profit_rate = ((current_price - entry_price) / entry_price) * 100
            
            # 買いシグナルの場合
            if signal_type == 'BUY':
                if profit_rate > 0:
                    win_count += 1
                else:
                    lose_count += 1
                total_profit_rate += profit_rate
            
            # 売りシグナルの場合
            elif signal_type == 'SELL':
                if profit_rate < 0:
                    win_count += 1
                else:
                    lose_count += 1
                total_profit_rate -= profit_rate
        
        except:
            continue
    
    # 勝率統計を更新
    try:
        stat_ws = sheet.worksheet("勝率統計")
    except:
        stat_ws = sheet.add_worksheet(title="勝率統計", rows=100, cols=10)
        stat_ws.append_row(['更新日時', '勝ち数', '負け数', '勝率(%)', '平均利益率(%)'])
    
    total = win_count + lose_count
    win_rate = (win_count / total * 100) if total > 0 else 0
    avg_profit = (total_profit_rate / total) if total > 0 else 0
    
    stat_ws.append_row([
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        win_count,
        lose_count,
        round(win_rate, 2),
        round(avg_profit, 2)
    ])

def main():
    print(f"スクリーン開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"スキャン対象銘柄数: {len(STOCKS)}\n")
    
    buy_signals = []
    sell_signals = []
    
    for symbol in STOCKS:
        try:
            print(f"{symbol}...", end=" ", flush=True)
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period='1y')
            
            signals = detect_signal(df)
            if signals:
                for sig in signals:
                    print(f"✅ {sig['type']}")
                    sig['ticker'] = symbol
                    if sig['type'] == 'BUY':
                        buy_signals.append(sig)
                    else:
                        sell_signals.append(sig)
            else:
                print(".")
        except:
            print(f"❌")
    
    print("\n" + "=" * 80)
    print(f"シグナル数: 買い {len(buy_signals)}件、売り {len(sell_signals)}件\n")
    
    try:
        sheet = gc.open_by_key(SPREADSHEET_ID)
        print(f"✅ スプレッドシート取得成功")
        
        # 本日のシグナルを更新
        ws = sheet.worksheet("本日のシグナル")
        ws.clear()
        ws.append_row(['日付', '銘柄', 'シグナル', '条件', 'エントリー価格', 'SMA10', 'SMA20', 'SMA75', 'RSI', 'MACD'])
        
        for sig in buy_signals + sell_signals:
            ws.append_row([
                str(datetime.now().date()),
                sig['ticker'],
                sig['type'],
                sig['conditions'],
                sig['entry_price'],
                sig['sma10'],
                sig['sma20'],
                sig['sma75'],
                sig['rsi'],
                sig['macd']
            ])
        
        print(f"✅ 本日のシグナルに書き込み完了")
        
        # シグナル履歴に追加
        update_signal_history(sheet, buy_signals, sell_signals)
        print(f"✅ シグナル履歴に追加完了")
        
        # 過去のシグナルを評価して勝率統計を更新
        evaluate_past_signals(sheet)
        print(f"✅ 勝率統計を更新完了")
        
        print(f"\n✅✅ スクリーン完了 ✅✅")
        print(f"買い: {len(buy_signals)}件、売り: {len(sell_signals)}件")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    input("Enterキーを押して終了...")

if __name__ == '__main__':
    main()
