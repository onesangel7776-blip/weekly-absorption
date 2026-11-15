
"""
이평봇 V5 - MA + Delta + Divergence + Ichimoku
유로봇 V9.30 SAFE CORE에서 뽑은 매매금지 필터 포함

유로봇 원본 필터:
- UseDailyLossLimit $700, UseDailyProfitCap $800 (CanOpenNewPosition, UpdateTradingDayAndDailyLimits)
- UseMffuTimeFilter 18:00-16:10 EST, PreClose 60분, BlockWeekend (IsSessionExitTime)
- Close-then-Reverse, Close-in-flight flag

이평봇 추가:
- Judas 15:30-16:15 / 21:00-21:45 KST 차단 (프랍 21 Ticker 보드에 있던거)
- News 고영향 ±30분 차단
- Zombie 0.7x + CVD 횡보 차단
- 23:50 강제청산
- 일일 최대이익 $500 신규
- WEEK -> DATE 일일매매
"""
from datetime import datetime, time
import pytz

# === 1. 유로봇에서 뽑은 일일 손실/이익 ===
class DailyLimit:
    def __init__(self, loss_limit=700, profit_cap=500):
        self.loss_limit = loss_limit
        self.profit_cap = profit_cap
        self.start_balance = None
        self.day = None
        self.loss_reached = False
        self.profit_reached = False

    def update_day(self, est_time, current_balance):
        # EST 기준 자정 넘기면 day 리셋 - 유로봇 UpdateTradingDayAndDailyLimits 로직
        day = est_time.date()
        if self.day != day:
            self.day = day
            self.start_balance = current_balance
            self.loss_reached = False
            self.profit_reached = False
        if self.start_balance is None:
            return
        if self.start_balance - current_balance >= self.loss_limit:
            self.loss_reached = True
        if current_balance - self.start_balance >= self.profit_cap:
            self.profit_reached = True

    def can_open(self):
        return not (self.loss_reached or self.profit_reached)

# === 2. 유로봇 세션 필터 ===
def is_session_exit(est_time, start_est="18:00", end_est="16:10", pre_close_min=60, block_weekend=True):
    if block_weekend and est_time.weekday() >= 5:  # 토,일
        return True
    def to_minutes(t):
        h,m = map(int, t.split(":"))
        return h*60+m
    s = to_minutes(start_est)
    e = to_minutes(end_est)
    cur = est_time.hour*60+est_time.minute
    pre = (e - pre_close_min) % (24*60)
    # 오버나잇 세션 18:00->16:10
    if s <= e:
        if cur < s or cur > e:
            return True
        return pre <= cur <= e
    else:
        if not (cur >= s or cur <= e):
            return True
        return pre <= cur <= e

# === 3. 프랍 5개 필터 (기존 21 Ticker 보드) ===
def is_judas(kst_time):
    # 15:30-16:15 / 21:00-21:45 KST 차단
    m = kst_time.hour*60 + kst_time.minute
    return (930 <= m <= 975) or (1260 <= m <= 1305)

def is_news_block(kst_time, news_times=[]):
    # 고영향 뉴스 ±30분 - Finnhub/GDELT에서 가져옴
    for nt in news_times:
        if abs((kst_time - nt).total_seconds()) <= 30*60:
            return True
    return False

def is_zombie(vol_mult, cvd_sideways):
    # 거래량 0.7x + CVD 횡보
    return vol_mult < 0.7 and cvd_sideways

def is_eod_close(kst_time):
    # 23:50 강제청산
    return kst_time.hour==23 and kst_time.minute>=50

# === 4. 이평봇 4기둥 ===
def check_ma_converge(mas):
    # mas = [ma2, ma4, ma8, ma16]
    spread = (max(mas)-min(mas))/min(mas)*100
    return 15 if spread < 0.15 else 0, spread

def check_location(loc_str):
    extreme = ["VAL","D-100","D-75","W-75","W-100","POC"]
    return 20 if any(e in loc_str for e in extreme) else 0

def check_daemok(delta_detail, daemok):
    if "대목" in delta_detail and daemok>=4000:
        return 20
    return 0

def check_cvd_flip(prev, now):
    if prev<0 and now>7000:
        return 15
    return 0

def check_vol(vol, vol_ma):
    return 10 if vol >= vol_ma*1.8 else 0

def check_vwap(close, vwap, side):
    if side=="LONG" and close>vwap: return 10
    if side=="SHORT" and close<vwap: return 10
    return 0

def total_score_v5(ticker_data, est_time, kst_time, daily, news_times, vol_ma):
    # 유로봇 일일 필터 먼저
    daily.update_day(est_time, ticker_data["balance"])
    if not daily.can_open():
        return {"ticker":ticker_data["ticker"],"total":0,"go":False,"reason":"Daily Limit"}
    if is_session_exit(est_time):
        return {"ticker":ticker_data["ticker"],"total":0,"go":False,"reason":"Session Exit"}
    if is_judas(kst_time): return {"ticker":ticker_data["ticker"],"total":0,"go":False,"reason":"Judas"}
    if is_news_block(kst_time, news_times): return {"ticker":ticker_data["ticker"],"total":0,"go":False,"reason":"News"}
    if is_zombie(ticker_data["vol"]/vol_ma, ticker_data["cvd_sideways"]): return {"ticker":ticker_data["ticker"],"total":0,"go":False,"reason":"Zombie"}
    if is_eod_close(kst_time): return {"ticker":ticker_data["ticker"],"total":0,"go":False,"reason":"EOD 23:50"}

    # 4기둥 점수
    loc = check_location(ticker_data["location"])
    dae = check_daemok(ticker_data["delta_detail"], ticker_data["daemok"])
    cvd = check_cvd_flip(ticker_data["cvd_prev"], ticker_data["cvd_now"])
    ma_s, _ = check_ma_converge([ticker_data["ma2"],ticker_data["ma4"],ticker_data["ma8"],ticker_data["ma16"]])
    vol_s = check_vol(ticker_data["vol"], vol_ma)
    vwap_s = check_vwap(ticker_data["close"], ticker_data["vwap"], ticker_data["side"])
    score155 = 10 if abs(ticker_data["score_long"]-ticker_data["score_short"])>=10 else 0
    total = loc+dae+cvd+ma_s+vol_s+vwap_s+score155
    return {"ticker":ticker_data["ticker"],"loc":loc,"daemok":dae,"cvd":cvd,"ma":ma_s,"vol":vol_s,"vwap":vwap_s,"score155":score155,"total":total,"go":total>=80}
