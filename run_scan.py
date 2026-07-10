import os
from telegram import Bot

bot = Bot(token=os.environ['BOT_TOKEN'])
bot.send_message(chat_id='6932573031', text='✅ ربات آنلاین و آماده است!')
