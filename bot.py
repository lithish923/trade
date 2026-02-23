import requests
import pandas as pd
import numpy as np
import time
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime
import json
import os

# ==========================================
# CONFIG
# ==========================================
BASE_URL = "https://demo-api.binance.com/api"
API_KEY = "Rsgl7YSLsU2nFtUVNu8tdmnpfS1CFTUqA2nr2rRRpo2xzwOXiBcFR0gHYHcjyQKE"
API_SECRET = "pZ9TdxZzjbuhguIMcvIYqfShKgWr1Jy0S6vYax6ZPLOWmrC3nKNCLYSv0esTaQVk"

SYMBOL = "BTCUSDT"
INTERVAL = "1h"
RISK_PERCENT = 0.01   # 1% capital risk
CAPITAL = 10000       # Demo capital assumption

# ==========================================
# SIGNED REQUEST
# ==========================================
def sign_params(params):
    query = urlencode(params)
    signature = hmac.new(
        API_SECRET.encode(),
        query.encode(),
        hashlib.sha256
    ).hexdigest()
    return query + "&signature=" + signature


def send_signed_request(method, endpoint, params={}):
    headers = {"X-MBX-APIKEY": API_KEY}
    params["timestamp"] = int(time.time() * 1000)

    query = sign_params(params)
    url = BASE_URL + endpoint + "?" + query

    if method == "POST":
        response = requests.post(url, headers=headers)
    elif method == "GET":
        response = requests.get(url, headers=headers)
    else:
        return None

    return response.json()


# ==========================================
# GET SPOT KLINES
# ==========================================
def get_klines():
    url = BASE_URL + "/v3/klines"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": 200
    }

    response = requests.get(url, params=params).json()

    df = pd.DataFrame(response, columns=[
        "openTime","open","high","low","close","volume",
        "closeTime","qav","numTrades","tbbav","tbqav","ignore"
    ])

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df


# ==========================================
# INDICATORS
# ==========================================
def apply_strategy(df):

    df["ema200"] = df["close"].ewm(span=200).mean()
    df["HH20"] = df["high"].rolling(20).max().shift(1)
    df["LL20"] = df["low"].rolling(20).min().shift(1)

    df.dropna(inplace=True)

    last = df.iloc[-1]

    if last["close"] > last["HH20"] and last["close"] > last["ema200"]:
        return "BUY"

    elif last["close"] < last["LL20"] and last["close"] < last["ema200"]:
        return "SELL"

    return None



def log_to_dashboard(order, side, price):
    file_path = 'trades.json'
    
    # Structure data for the dashboard
    trade_data = {
        "timestamp": int(time.time()),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": order.get('symbol', 'BTCUSDT'),
        "side": side,
        "price": price, # Approximate price or filled price
        "qty": order.get('origQty', 0),
        "status": order.get('status', 'FILLED')
    }

    # Load existing data
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                history = json.load(f)
        except:
            history = []
    else:
        history = []

    # Append new trade
    history.append(trade_data)

    # Save back to file
    with open(file_path, 'w') as f:
        json.dump(history, f, indent=4)


# ==========================================
# BALANCE CHECK
# ==========================================
def get_balance(asset="USDT"):
    account = send_signed_request("GET", "/v3/account")
    for bal in account["balances"]:
        if bal["asset"] == asset:
            return float(bal["free"])
    return 0


# ==========================================
# PLACE ORDER
# ==========================================
def place_market_order(side, quantity):
    params = {
        "symbol": SYMBOL,
        "side": side,
        "type": "MARKET",
        "quantity": quantity
    }

    order = send_signed_request("POST", "/v3/order", params)
    return order


# ==========================================
# POSITION CHECK
# ==========================================
def check_open_position():
    account = send_signed_request("GET", "/v3/account")
    for bal in account["balances"]:
        if bal["asset"] == "BTC":
            if float(bal["free"]) > 0:
                return True
    return False


# ==========================================
# EXECUTION ENGINE
# ==========================================
def execute():

    df = get_klines()
    signal = apply_strategy(df)

    if not signal:
        print("No signal.")
        return

    print("Signal:", signal)

    usdt_balance = get_balance("USDT")
    btc_balance = get_balance("BTC")

    last_price = df["close"].iloc[-1]

    if signal == "BUY" and usdt_balance > 10:

        risk_amount = usdt_balance * RISK_PERCENT
        qty = round(risk_amount / last_price, 5)

        order = place_market_order("BUY", qty)
        print("BUY ORDER:", order)

        log_to_dashboard(order, "BUY", last_price) 

    elif signal == "SELL" and btc_balance > 0:

        qty = round(btc_balance, 5)
        order = place_market_order("SELL", qty)
        print("SELL ORDER:", order)

        log_to_dashboard(order, "SELL", last_price)

    else:
        print("No action taken.")


# ==========================================
# RUN LOOP
# ==========================================
while True:
    try:
        execute()
        print("Waiting 1 hour...")
        time.sleep(3600)
    except Exception as e:
        print("Error:", e)
        time.sleep(10)