
import yfinance as yf
import pandas as pd
import numpy as np

def get_box_metrics(ticker, period="60d"):
    """
    BOX RANGE (박스 구간) = (20D High - 20D Low) / ATR(20)
    VOL MULT (거래량 배수) = 오늘 거래량 / 20D 평균
    DWELL (체류일) = 현재 박스 안에 머문 일수
    신뢰도: Yahoo Finance (거래소 원천) - 100%
    """
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 22:
            return None
        # ATR
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = (df['High'] - df['Close'].shift(1)).abs()
        df['L-PC'] = (df['Low'] - df['Close'].shift(1)).abs()
        df['TR'] = df[['H-L','H-PC','L-PC']].max(axis=1)
        df['ATR20'] = df['TR'].rolling(20).mean()
        
        last = df.iloc[-1]
        last_20 = df.iloc[-22:-2]  # 최근 20일 박스 (어제까지 기준)
        box_high = last_20['High'].max()
        box_low = last_20['Low'].min()
        atr = last_20['ATR20'].iloc[-1] if not pd.isna(last_20['ATR20'].iloc[-1]) else (box_high-box_low)/2
        
        box_range_pct = (box_high - box_low) / last['Close'] * 100 if last['Close'] else 0
        # 더 정확한 정의: (High-Low)/ATR 로도 계산
        box_range_atr = (box_high - box_low) / atr if atr else 0
        
        # VOL MULT
        vol_avg20 = df['Volume'].iloc[-21:-1].mean()
        vol_mult = last['Volume'] / vol_avg20 if vol_avg20 else 1.0
        
        # DWELL: 박스 안에 머문 일수
        dwell = 0
        for i in range(len(df)-1, -1, -1):
            c = df['Close'].iloc[i]
            if box_low <= c <= box_high:
                dwell += 1
            else:
                break
        # 점수용 박스 타이트니스 점수 (좁을수록 10점)
        # 1% 이하: 10점, 3%: 8점, 6%: 5점, 10% 이상: 1점
        box_score = max(0, 10 - (box_range_pct * 0.9))
        
        return {
            "box_range_pct": round(float(box_range_pct), 2),
            "box_range_atr": round(float(box_range_atr), 2),
            "vol_mult": round(float(vol_mult), 2),
            "dwell": int(dwell),
            "box_score": round(float(box_score), 2),
            "close": round(float(last['Close']), 2),
            "box_high": round(float(box_high), 2),
            "box_low": round(float(box_low), 2)
        }
    except Exception as e:
        print(f"[BOX] {ticker} error: {e}")
        return None
