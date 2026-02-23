from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = 'trades.json'

def get_trades():
    """Reads the trades from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Sort by time descending (newest first)
            return sorted(data, key=lambda x: x.get('timestamp', 0), reverse=True)
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

def calculate_stats(trades):
    """Calculates basic stats for the dashboard cards."""
    total_trades = len(trades)
    buy_trades = sum(1 for t in trades if t['side'] == 'BUY')
    sell_trades = sum(1 for t in trades if t['side'] == 'SELL')
    last_trade = trades[0] if trades else None
    
    return {
        "total": total_trades,
        "buys": buy_trades,
        "sells": sell_trades,
        "last_trade_time": last_trade['time'] if last_trade else "No trades yet"
    }

@app.route('/')
def dashboard():
    trades = get_trades()
    stats = calculate_stats(trades)
    return render_template('dashboard.html', trades=trades, stats=stats)

if __name__ == '__main__':
    # host='0.0.0.0' allows access from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=True)