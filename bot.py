import os
import telebot

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "🇺🇸 Welcome to USA.USD!\n\n"
        "🚀 Your digital journey starts here."
    )

bot.infinity_polling()
