import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


# ============================================================
# SETTINGS
# ============================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

WATCHLIST = {
    "NIFTY 50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "GOLD/USD": "GC=F",
    "BTC/USD": "BTC-USD",
    "SOL/USD": "SOL-USD",
    "ETH/USD": "ETH-USD",
    "XRP/USD": "XRP-USD",
    "DOGE/USD": "DOGE-USD"
}

TIMEFRAME = "5m"
LOOKBACK = "2d"


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=20
        )

        if response.status_code == 200:
            print("✅ Telegram message sent")
        else:
            print("❌ Telegram error:", response.text)

    except Exception as e:
        print("❌ Telegram connection error:", e)


# ============================================================
# ADX + DI
# ============================================================

def calculate_adx(df, period=14):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where(
        (plus_dm > minus_dm) & (plus_dm > 0),
        0
    )

    minus_dm = minus_dm.where(
        (minus_dm > plus_dm) & (minus_dm > 0),
        0
    )

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = true_range.rolling(period).mean()

    plus_di = (
        100 *
        plus_dm.rolling(period).mean() /
        atr
    )

    minus_di = (
        100 *
        minus_dm.rolling(period).mean() /
        atr
    )

    dx = (
        100 *
        abs(plus_di - minus_di) /
        (plus_di + minus_di)
    )

    adx = dx.rolling(period).mean()

    return adx, plus_di, minus_di


# ============================================================
# VWAP
# ============================================================

def calculate_vwap(df):

    typical_price = (
        df["High"] +
        df["Low"] +
        df["Close"]
    ) / 3

    volume = df["Volume"].replace(0, np.nan)

    vwap = (
        (typical_price * volume).cumsum()
        / volume.cumsum()
    )

    return vwap


# ============================================================
# CHECK ONE MARKET
# ============================================================

def check_symbol(name, symbol):

    try:

        print(f"\n🔎 Checking {name} ({symbol})")

        df = yf.download(
            symbol,
            period=LOOKBACK,
            interval=TIMEFRAME,
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            print(f"⚠️ {name}: No data")
            return

        # Yahoo Finance can sometimes return MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for column in required_columns:

            if column not in df.columns:
                print(
                    f"❌ {name}: Missing {column}"
                )
                return

        df = df.dropna(
            subset=required_columns
        )

        if len(df) < 40:
            print(
                f"⚠️ {name}: Not enough candles"
            )
            return

        # Calculate indicators
        df["ADX"], df["DI+"], df["DI-"] = calculate_adx(df)

        df["VWAP"] = calculate_vwap(df)

        # Last COMPLETED 5-minute candle
        candle = df.iloc[-2]

        price = float(candle["Close"])
        vwap = float(candle["VWAP"])
        adx = float(candle["ADX"])
        di_plus = float(candle["DI+"])
        di_minus = float(candle["DI-"])

        candle_time = str(df.index[-2])

        print(
            f"Price: {price:.2f} | "
            f"VWAP: {vwap:.2f} | "
            f"ADX: {adx:.2f} | "
            f"DI+: {di_plus:.2f} | "
            f"DI-: {di_minus:.2f}"
        )

        # ====================================================
        # SELL STRATEGY
        # ====================================================

        condition_1 = adx > 25
        condition_2 = di_minus > di_plus
        condition_3 = price < vwap

        if (
            condition_1
            and condition_2
            and condition_3
        ):

            message = (
                "🔴 SELL SIGNAL\n\n"
                f"📊 Market: {name}\n"
                f"⏱️ Timeframe: 5 Minutes\n"
                f"🕐 Candle: {candle_time}\n\n"
                f"💰 Price: {price:.2f}\n"
                f"📈 VWAP: {vwap:.2f}\n"
                f"📊 ADX: {adx:.2f}\n"
                f"🔻 DI-: {di_minus:.2f}\n"
                f"🔺 DI+: {di_plus:.2f}\n\n"
                "✅ SELL CONDITIONS\n"
                "ADX > 25 ✅\n"
                "DI- > DI+ ✅\n"
                "Price < VWAP ✅\n\n"
                "⚠️ SELL SIGNAL ONLY"
            )

            print(
                f"🚨 SELL SIGNAL: {name}"
            )

            send_telegram(message)

        else:

            print(
                f"⏸️ No SELL signal: {name}"
            )

    except Exception as e:

        print(
            f"❌ Error checking {name}: {e}"
        )


# ============================================================
# SCAN ALL MARKETS
# ============================================================

def scan():

    print("\n")
    print("=" * 60)
    print(
        "🚀 TRADING SCAN STARTED"
    )
    print(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )
    print("=" * 60)

    for name, symbol in WATCHLIST.items():

        check_symbol(
            name,
            symbol
        )

    print("=" * 60)
    print("✅ SCAN COMPLETED")
    print("=" * 60)


# ============================================================
# START
# ============================================================

print("🚀 Trading Alert Agent Started!")

scan()

print("✅ Scan completed successfully.")
