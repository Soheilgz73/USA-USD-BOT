import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@USA_USD_chanel"
CHANNEL_LINK = "https://t.me/USA_USD_chanel"

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

bot = telebot.TeleBot(TOKEN)

PLANS = [10, 30, 50, 85, 100, 150, 350, 500, 900, 1500, 3000, 5000]

def is_member(user_id):
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

def join_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🇺🇸 JOIN CHANNEL", url=CHANNEL_LINK))
    kb.add(InlineKeyboardButton("✅ VERIFY MEMBERSHIP", callback_data="verify"))
    return kb

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    items = [
        ("💎 PLANS", "plans"),
        ("💰 MY WALLET", "wallet"),
        ("👤 PROFILE", "profile"),
        ("🎁 INVITE FRIENDS", "invite"),
        ("📊 CALCULATOR", "calculator"),
        ("📞 SUPPORT", "support")
    ]
    kb.add(*[InlineKeyboardButton(a, callback_data=b) for a, b in items])
    return kb

def home(chat_id):
    bot.send_message(
        chat_id,
        "🇺🇸 USA.USD\n"
        "🦅 WELCOME TO YOUR DIGITAL DASHBOARD\n\n"
        "BLUE • RED • GOLD\n"
        "Choose an option below:",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=["start"])
def start(message):
    if not is_member(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🇺🇸 Welcome to USA.USD!\n\n"
            "Join our official channel to continue.",
            reply_markup=join_menu()
        )
    else:
        home(message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    data = call.data

    if data == "verify":
        if is_member(uid):
            bot.answer_callback_query(call.id, "Membership verified!")
            home(call.message.chat.id)
        else:
            bot.answer_callback_query(
                call.id, "Please join the channel first.", show_alert=True
            )
        return

    if not is_member(uid):
        bot.answer_callback_query(call.id, "Join the channel first!", show_alert=True)
        return

    if data == "plans":
        kb = InlineKeyboardMarkup(row_width=2)
        for amount in PLANS:
            kb.add(InlineKeyboardButton(
                f"💵 ${amount:,}",
                callback_data=f"plan_{amount}"
            ))
        bot.send_message(
            call.message.chat.id,
            "💎 USA.USD DEMO PLANS\n\n"
            "Illustrative daily calculation: 1.5%\n"
            "No actual investment or guaranteed returns.",
            reply_markup=kb
        )

    elif data.startswith("plan_"):
        amount = int(data.split("_")[1])
        daily = amount * 0.015
        monthly = daily * 30
        bot.send_message(
            call.message.chat.id,
            f"🇺🇸 USA.USD PLAN\n\n"
            f"Amount: ${amount:,}\n"
            f"Illustrative daily calculation: ${daily:.3f}\n"
            f"30-day simple calculation: ${monthly:.2f}\n\n"
            "⚠️ Simulation only. No real deposit or payout."
        )

    elif data == "wallet":
        bot.send_message(
            call.message.chat.id,
            "💰 MY WALLET\n\nDemo balance: $0.00"
        )

    elif data == "profile":
        user = call.from_user
        bot.send_message(
            call.message.chat.id,
            f"👤 PROFILE\n\nName: {user.first_name}\nID: {uid}"
        )

    elif data == "invite":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(
            call.message.chat.id,
            f"🎁 YOUR INVITE LINK\n\n{link}"
        )

    elif data == "calculator":
        bot.send_message(
            call.message.chat.id,
            "📊 Calculator uses illustrative simple calculations only."
        )

    elif data == "support":
        bot.send_message(
            call.message.chat.id,
            "📞 USA.USD SUPPORT\n\nContact the official support team."
        )

    bot.answer_callback_query(call.id)

bot.infinity_polling(skip_pending=True)
