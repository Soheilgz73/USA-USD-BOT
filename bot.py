import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

TOKEN=os.environ["BOT_TOKEN"]
APP_URL=os.environ.get("WEBAPP_URL","https://REPLACE_WITH_YOUR_HTTPS_DOMAIN")
CHANNEL="@USA_USD_chanel"
CHANNEL_LINK="https://t.me/USA_USD_chanel"
bot=telebot.TeleBot(TOKEN)

def is_member(uid):
    try: return bot.get_chat_member(CHANNEL,uid).status in ("member","administrator","creator")
    except Exception: return False

def menu():
    kb=InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🇺🇸 OPEN USA.USD APP",web_app=WebAppInfo(url=APP_URL)))
    kb.add(InlineKeyboardButton("📢 OFFICIAL CHANNEL",url=CHANNEL_LINK))
    return kb

@bot.message_handler(commands=["start"])
def start(m):
    if not is_member(m.from_user.id):
        kb=InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("JOIN CHANNEL",url=CHANNEL_LINK))
        kb.add(InlineKeyboardButton("VERIFY",callback_data="verify"))
        bot.send_message(m.chat.id,"🇺🇸 Welcome to USA.USD. Join the official channel first.",reply_markup=kb)
    else:
        bot.send_message(m.chat.id,"🇺🇸 USA.USD\nYour digital dashboard is ready.",reply_markup=menu())

@bot.callback_query_handler(func=lambda c:c.data=="verify")
def verify(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id,"Membership verified")
        bot.send_message(c.message.chat.id,"Welcome to USA.USD",reply_markup=menu())
    else: bot.answer_callback_query(c.id,"Please join the channel first",show_alert=True)

bot.infinity_polling(skip_pending=True)
