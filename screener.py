#!/usr/bin/env python3
"""
日本株スクリーナー - GitHub Actions 自動実行版
毎日 16:30 に実行
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# Google Sheets 認証
CREDENTIALS_JSON = os.getenv('GCP_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

creds_dict = json.loads(CREDENTIALS_JSON)
creds = Credentials.from_service_account_info(creds_dict, scopes=[
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
])
gc = gspread.authorize(creds)

# 監視銘柄
STOCKS = ['7011.T', '6502.T', '6758.T', '8035.T', '9984.T', '9020.T', '4502.T', '5401.T', '1605.T', '2914.T']

def calculate_rsi(prices, period=14):
    """RSI を計算"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_signal(df):
    """シグナル検出"""
    if len(df) < 30:
        return None
    
    close = df['Close']
    rsi = calculate_rsi(close)
    
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9).mean()
    
    sma10 = close.rolling(10).mean()
    sma25 = close.rolling(25).mean()
    
    idx = len(df) - 1
    
    signals = []
    
    # 買い
    buy_cond = []
    if rsi.iloc[idx] < 30:
        buy_cond.append('RSI<30')
    if macd.iloc[idx-1] < macd_signal.iloc[idx-1] and macd.iloc[idx] > macd_signal.iloc[idx]:
        buy_cond.append('MACDゴールデンクロス')
    if close.iloc[idx-1] <= sma25.iloc[idx-1] and close.iloc[idx] > sma25.iloc[idx]:
        buy_cond.append('SMA25反発')
    
    if len(buy_cond) >= 2:
        signals.append({
            'type': 'BUY',
            'conditions': ', '.join(buy_cond),
            'rsi': round(float(rsi.iloc[idx]), 2),
            'macd': round(float(macd.iloc[idx]), 6),
            'sma10': round(float(sma10.iloc[idx]), 2),
            'sma25': round(float(sma25.iloc[idx]), 2),
            'close': round(float(close.iloc[idx]), 2)
        })
    
    # 売り
    sell_cond = []
    if rsi.iloc[idx] > 70:
        sell_cond.append('RSI>70')
    if macd.iloc[idx-1] > macd_signal.iloc[idx-1] and macd.iloc[idx] < macd_signal.iloc[idx]:
        sell_cond.append('MACDデッドクロス')
    if sma10.iloc[idx-1] >= sma25.iloc[idx-1] and sma10.iloc[idx] < sma25.iloc[idx]:
        sell_cond.append('SMA10下抜け')
    
    if len(sell_cond) >= 2:
        signals.append({
            'type': 'SELL',
            'conditions': ', '.join(sell_cond),
            'rsi': round(float(rsi.iloc[idx]), 2),
            'macd': round(float(macd.iloc[idx]), 6),
            'sma10': round(float(sma10.iloc[idx]), 2),
            'sma25': round(float(sma25.iloc[idx]), 2),
            'close': round(float(close.iloc[idx]), 2)
        })
    
    return signals if signals else None

def main():
    print(f"スクリーン開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    buy_signals = []
    sell_signals = []
    
    for ticker in STOCKS:
        try:
            print(f"{ticker}...", end=" ", flush=True)
            df = yf.download(ticker, period='1y', progress=False, auto_adjust=True)
            
            if df is None or len(df) < 30:
                print("❌")
                continue
            
            signals = detect_signal(df)
            if signals:
                for sig in signals:
                    print(f"✅ {sig['type']}")
                    sig['ticker'] = ticker
                    if sig['type'] == 'BUY':
                        buy_signals.append(sig)
                    else:
                        sell_signals.append(sig)
            else:
                print(".")
        except Exception as e:
            print(f"❌")
    
    # Google Sheets に書き込み
    try:
        sheet = gc.open_by_key(SPREADSHEET_ID)
        ws = sheet.worksheet("本日のシグナル")
        ws.clear()
        ws.append_row(['日付', '銘柄', 'シグナル', '条件', '終値', 'RSI', 'MACD', 'SMA10', 'SMA25'])
        
        for sig in buy_signals + sell_signals:
            ws.append_row([
                str(datetime.now().date()),
                sig['ticker'],
                sig['type'],
                sig['conditions'],
                sig['close'],
                sig['rsi'],
                sig['macd'],
                sig['sma10'],
                sig['sma25']
            ])
        
        print(f"\n✅ 買い: {len(buy_signals)}件、売り: {len(sell_signals)}件")
        print("✅ Google Sheets に書き込み完了")
    except Exception as e:
        print(f"❌ Sheets エラー: {e}")

if __name__ == '__main__':
    main()
