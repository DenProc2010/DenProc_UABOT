import telebot
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "1"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask).start()

# === Telegram БОТ ===

bot = telebot.TeleBot("7174297217:AAG1CVX2m35Uo0rUSwk7RIS_6y__zI7-AMg")  # 🔁 Заміни на свій токен

user_language = {}
contact_sessions = {}
ADMINS = [2133347662]

def load_news():
    try:
        with open("news.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "ua": {"text": "Новини відсутні", "comment": ""},
            "en": {"text": "No news available", "comment": ""}
        }

def save_news(data):
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_banned(user_id):
    return user_id in load_banned_users()

def load_banned_users():
    try:
        with open("banned_users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_banned_users(banned_list):
    with open("banned_users.json", "w", encoding="utf-8") as f:
        json.dump(banned_list, f)

def load_texts():
    with open("texts.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_lang(user_id):
    return user_language.get(user_id, 'ua')

def get_text(key, user_id):
    lang = get_lang(user_id)
    return texts.get(key, {}).get(lang, '')

texts = load_texts()

@bot.message_handler(func=lambda message: is_banned(message.from_user.id))
def banned_user_handler(message):
    bot.send_message(message.chat.id, get_text('banned', message.from_user.id))

@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("🇺🇦 Українська"), KeyboardButton("🇬🇧 English"))
    bot.send_message(message.chat.id, texts['welcome']['ua'], reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🇺🇦 Українська", "🇬🇧 English"])
def language_select_handler(message):
    lang = 'ua' if "Українська" in message.text else 'en'
    user_language[message.from_user.id] = lang
    bot.send_message(message.chat.id, texts['start'][lang])

@bot.message_handler(commands=['news'])
def news_handler(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    news_data = load_news()
    news_text = news_data.get(lang, {}).get("text", "Новини відсутні" if lang == "ua" else "No news available")
    bot.send_message(message.chat.id, news_text)

@bot.message_handler(commands=['help'])
def help_handler(message):
    bot.send_message(message.chat.id, get_text('help', message.from_user.id))

@bot.message_handler(commands=['about'])
def about_handler(message):
    bot.send_message(message.chat.id, get_text('about', message.from_user.id))

@bot.message_handler(commands=['contact'])
def contact_handler(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(message.chat.id, get_text('banned', user_id))
        return
    contact_sessions[user_id] = True
    bot.send_message(message.chat.id, get_text('contact_start', user_id))

@bot.message_handler(commands=['end'])
def end_contact_session(message):
    user_id = message.from_user.id
    if user_id in contact_sessions:
        contact_sessions.pop(user_id)
        bot.send_message(message.chat.id, get_text('end_done', user_id))
    else:
        bot.send_message(message.chat.id, get_text('end_none', user_id))

@bot.message_handler(func=lambda m: m.from_user.id in contact_sessions)
def handle_contact_session(message):
    user_id = message.from_user.id
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, get_text('contact_command_blocked', user_id))
        return
    user_name = message.from_user.username or message.from_user.first_name
    for admin_id in ADMINS:
        bot.send_message(admin_id, f"📩 Повідомлення від @{user_name} (id: {user_id}):\n\n{message.text}")
    bot.send_message(message.chat.id, get_text('contact_sent', user_id))

@bot.message_handler(commands=['reply'])
def reply_handler(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.send_message(message.chat.id, get_text('admin_only', user_id))
        return
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            raise ValueError("Недостатньо аргументів")
        target_user_id = int(parts[1])
        reply_text = parts[2]
    except:
        bot.send_message(message.chat.id, get_text('reply_usage', user_id))
        return
    try:
        bot.send_message(target_user_id, f"📬 {get_text('admin_reply_prefix', target_user_id)}\n\n{reply_text}")
        bot.send_message(message.chat.id, get_text('reply_success', user_id).format(user_id=target_user_id))
    except Exception as e:
        bot.send_message(message.chat.id, get_text('reply_fail', user_id).format(error=e))

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, get_text('admin_only', message.from_user.id))
        return
    try:
        target_id = int(message.text.split()[1])
        if target_id in ADMINS:
            bot.send_message(message.chat.id, get_text('cannot_ban_admin', message.from_user.id))
            return
        banned = load_banned_users()
        if target_id not in banned:
            banned.append(target_id)
            save_banned_users(banned)
            bot.send_message(message.chat.id, get_text('ban_success', message.from_user.id).format(user_id=target_id))
        else:
            bot.send_message(message.chat.id, get_text('already_banned', message.from_user.id).format(user_id=target_id))
    except:
        bot.send_message(message.chat.id, get_text('ban_usage', message.from_user.id))

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, get_text('admin_only', message.from_user.id))
        return
    try:
        target_id = int(message.text.split()[1])
        banned = load_banned_users()
        if target_id in banned:
            banned.remove(target_id)
            save_banned_users(banned)
            bot.send_message(message.chat.id, get_text('unban_success', message.from_user.id).format(user_id=target_id))
        else:
            bot.send_message(message.chat.id, get_text('not_banned', message.from_user.id).format(user_id=target_id))
    except:
        bot.send_message(message.chat.id, get_text('unban_usage', message.from_user.id))

# === Запуск бота ===
bot.infinity_polling()
