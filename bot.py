import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import ccxt
import pandas as pd
import numpy as np

TOKEN = "8703615510:AAFXnJPUwcmvC1U0zRVN6gR-t1J_7KiOkvs"
TIMEFRAME = '4h'
MIN_CANDLES = 15
FIB_LEVEL = 0.5

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

def find_valid_legs(df):
    swings = []
    current_leg_start = 0
    direction = None
    
    for i in range(1, len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        prev_high = df['high'].iloc[i-1]
        prev_low = df['low'].iloc[i-1]
        
        if direction is None:
            if high > prev_high and low > prev_low:
                direction = 1
                current_leg_start = i-1
            elif high < prev_high and low < prev_low:
                direction = -1
                current_leg_start = i-1
            continue
        
        if direction == 1 and (low < prev_low):
            leg_length = i - current_leg_start
            if leg_length >= MIN_CANDLES:
                swings.append({
                    'start_idx': current_leg_start,
                    'end_idx': i-1,
                    'start_price': df['low'].iloc[current_leg_start],
                    'end_price': df['high'].iloc[i-1],
                    'direction': 'bullish',
                    'length': leg_length
                })
            direction = -1
            current_leg_start = i-1
            
        elif direction == -1 and (high > prev_high):
            leg_length = i - current_leg_start
            if leg_length >= MIN_CANDLES:
                swings.append({
                    'start_idx': current_leg_start,
                    'end_idx': i-1,
                    'start_price': df['high'].iloc[current_leg_start],
                    'end_price': df['low'].iloc[i-1],
                    'direction': 'bearish',
                    'length': leg_length
                })
            direction = 1
            current_leg_start = i-1
    
    return swings

def check_fib_retracement(df, leg, current_idx):
    if leg['direction'] == 'bullish':
        leg_range = leg['end_price'] - leg['start_price']
        fib_50 = leg['end_price'] - (leg_range * FIB_LEVEL)
        current_price = df['close'].iloc[current_idx]
        price_touched_fib = False
        for i in range(leg['end_idx'], current_idx + 1):
            if df['low'].iloc[i] <= fib_50 <= df['high'].iloc[i]:
                price_touched_fib = True
                break
        return price_touched_fib and current_price > fib_50 * 0.99
        
    elif leg['direction'] == 'bearish':
        leg_range = leg['start_price'] - leg['end_price']
        fib_50 = leg['end_price'] + (leg_range * FIB_LEVEL)
        current_price = df['close'].iloc[current_idx]
        price_touched_fib = False
        for i in range(leg['end_idx'], current_idx + 1):
            if df['low'].iloc[i] <= fib_50 <= df['high'].iloc[i]:
                price_touched_fib = True
                break
        return price_touched_fib and current_price < fib_50 * 1.01
    return False

async def scan_markets():
    try:
        markets = exchange.load_markets()
        usdt_pairs = [s for s in markets if s.endswith('/USDT') and markets[s]['future']]
        signals = []
        
        for symbol in usdt_pairs[:30]:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=200)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                legs = find_valid_legs(df)
                
                if legs:
                    last_leg = legs[-1]
                    if len(df) - last_leg['end_idx'] > 3:
                        if check_fib_retracement(df, last_leg, len(df)-1):
                            entry = df['close'].iloc[-1]
                            if last_leg['direction'] == 'bullish':
                                sl = last_leg['start_price'] * 0.99
                                tp = last_leg['end_price'] * 1.01
                                signal_type = "خرید 🟢"
                            else:
                                sl = last_leg['start_price'] * 1.01
                                tp = last_leg['end_price'] * 0.99
                                signal_type = "فروش 🔴"
                            
                            signals.append({
                                'symbol': symbol,
                                'type': signal_type,
                                'direction': last_leg['direction'],
                                'leg_length': last_leg['length'],
                                'entry': entry,
                                'stop_loss': sl,
                                'take_profit': tp
                            })
                await asyncio.sleep(0.3)
            except:
                continue
        return signals
    except Exception as e:
        print(f"Error: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 ربات تحلیل تایم فریم ۴ ساعته\n\n"
        "/scan - اسکن بازار\n"
        "/help - راهنما"
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="⏳ در حال تحلیل بازار...")
    
    signals = await scan_markets()
    
    if not signals:
        await context.bot.send_message(chat_id=chat_id, text="❌ هیچ فرصتی پیدا نشد!")
        return
    
    response = "📊 **فرصت‌های معاملاتی:**\n\n"
    for i, sig in enumerate(signals[:20], 1):
        response += (
            f"{i}. {sig['type']} - {sig['symbol']}\n"
            f"   • کندل‌های لگ: {sig['leg_length']}\n"
            f"   • ورود: {sig['entry']:.4f}\n"
            f"   • حد ضرر: {sig['stop_loss']:.4f}\n"
            f"   • حد سود: {sig['take_profit']:.4f}\n\n"
        )
    
    await context.bot.send_message(chat_id=chat_id, text=response)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📌 شرایط:\n"
        f"• تایم فریم: {TIMEFRAME}\n"
        f"• حداقل کندل: {MIN_CANDLES}\n"
        f"• فیبوناچی: {FIB_LEVEL*100}%\n\n"
        "/scan - شروع تحلیل"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("help", help_cmd))
    print("🤖 ربات اجرا شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
