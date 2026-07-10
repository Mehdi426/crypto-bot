import asyncio
import os
from bot import scan_markets
from telegram import Bot

async def main():
    bot = Bot(token=os.environ['BOT_TOKEN'])
    chat_id = '6932573031'
    
    await bot.send_message(chat_id=chat_id, text='⏳ اسکن خودکار بازار شروع شد...')
    signals = await scan_markets()
    
    if not signals:
        await bot.send_message(chat_id=chat_id, text='❌ هیچ فرصتی پیدا نشد!')
        return
    
    response = '📊 **فرصت‌های معاملاتی:**\n\n'
    for i, sig in enumerate(signals[:20], 1):
        response += (
            f"{i}. {sig['type']} - {sig['symbol']}\n"
            f"   • کندل‌های لگ: {sig['leg_length']}\n"
            f"   • ورود: {sig['entry']:.4f}\n"
            f"   • حد ضرر: {sig['stop_loss']:.4f}\n"
            f"   • حد سود: {sig['take_profit']:.4f}\n\n"
        )
    
    await bot.send_message(chat_id=chat_id, text=response)

asyncio.run(main())
