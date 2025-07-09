import telebot
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

TOKEN = "7174297217:AAF-UolUISCMPhmEX8_7oU0cjVe5RJNmA7g"
GROUP_ID = -1002454855038
TOPICS_FILE = "topics.json"
BANNED_FILE = "banned_users.json"
NEWS_FILE = "news.json"
TEXTS_FILE = "texts.json"
ADMINS = [2133347662]

bot = telebot.TeleBot(TOKEN)
user_language = {}

def load_json_file(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_texts():
    return load_json_file(TEXTS_FILE, {})

def load_topics():
    return load_json_file(TOPICS_FILE, {})

def save_topics(data):
    save_json_file(TOPICS_FILE, data)

def load_banned_users():
    return load_json_file(BANNED_FILE, [])

def save_banned_users(data):
    save_json_file(BANNED_FILE, data)

def load_news():
    return load_json_file(NEWS_FILE, {
        "ua": {"text": "Новини відсутні", "comment": ""},
        "en": {"text": "No news available", "comment": ""}
    })

def save_news(data):
    save_json_file(NEWS_FILE, data)

def is_banned(user_id):
    return user_id in load_banned_users()

texts = load_texts()

def get_lang(user_id):
    return user_language.get(user_id, 'ua')

def get_text(key, user_id=None):
    lang = get_lang(user_id) if user_id else 'ua'
    return texts.get(key, {}).get(lang, f"[{key} not found]")

@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("\U0001F1FA\U0001F1E6 Українська"), KeyboardButton("\U0001F1EC\U0001F1E7 English"))
    bot.send_message(message.chat.id, get_text('welcome'), reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["\U0001F1FA\U0001F1E6 Українська", "\U0001F1EC\U0001F1E7 English"])
def language_select_handler(message):
    lang = 'ua' if "Українська" in message.text else 'en'
    user_language[message.from_user.id] = lang
    bot.send_message(message.chat.id, get_text('start', message.from_user.id))

@bot.message_handler(commands=['help'])
def help_handler(message):
    bot.send_message(message.chat.id, get_text('help', message.from_user.id))

@bot.message_handler(commands=['about'])
def about_handler(message):
    bot.send_message(message.chat.id, get_text('about', message.from_user.id))

@bot.message_handler(commands=['news'])
def news_handler(message):
    news_data = load_news()
    lang = get_lang(message.from_user.id)
    news_text = news_data.get(lang, {}).get("text", "Новини відсутні" if lang == "ua" else "No news available")
    bot.send_message(message.chat.id, news_text)

@bot.message_handler(commands=['contact'])
def contact_handler(message):
    user_id = message.from_user.id
    user_id_str = str(user_id)

    if message.chat.type != 'private':
        bot.send_message(message.chat.id, get_text('contact_private'))
        return

    if is_banned(user_id):
        bot.send_message(message.chat.id, get_text('banned', user_id))
        return

    topics = load_topics()
    thread_id = topics.get(user_id_str)

    if not isinstance(thread_id, int):
        try:
            username = message.from_user.username or message.from_user.first_name
            topic_name = f"Звернення: @{username} (id: {user_id})"
            topic = bot.create_forum_topic(GROUP_ID, name=topic_name)
            thread_id = topic.message_thread_id
            topics[user_id_str] = thread_id
            save_topics(topics)
        except Exception as e:
            bot.send_message(message.chat.id, get_text('contact_error', user_id).format(error=e))
            return

    warning = get_text('contact_warning', user_id)
    start_msg = get_text('contact_start', user_id)
    bot.send_message(message.chat.id, f"{start_msg}\n\n{warning}")

@bot.message_handler(commands=['end'])
def end_contact_session(message):
    user_id_str = str(message.from_user.id)
    topics = load_topics()
    if user_id_str in topics:
        topics.pop(user_id_str)
        save_topics(topics)
        bot.send_message(message.chat.id, get_text('end_done', message.from_user.id))
    else:
        bot.send_message(message.chat.id, get_text('end_none', message.from_user.id))

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def forward_user_message(message):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    topics = load_topics()
    banned = load_banned_users()

    if user_id in banned:
        return

    thread_id = topics.get(user_id_str)

    if not isinstance(thread_id, int):
        try:
            username = message.from_user.username or message.from_user.first_name
            topic_name = f"Звернення: @{username} (id: {user_id})"
            topic = bot.create_forum_topic(GROUP_ID, name=topic_name)
            thread_id = topic.message_thread_id
            topics[user_id_str] = thread_id
            save_topics(topics)
        except Exception as e:
            bot.send_message(message.chat.id, f"Помилка створення теми: {e}")
            return

    try:
        if message.content_type == 'text':
            bot.send_message(GROUP_ID, f"\U0001F4E9 @{message.from_user.username or message.from_user.first_name} (id: {user_id}):\n{message.text}", message_thread_id=thread_id)
            bot.send_message(message.chat.id, get_text("contact_sent", user_id))
        else:
            bot.send_message(message.chat.id, get_text('unsupported_content', user_id))
    except Exception as e:
        if "message thread not found" in str(e).lower():
            topics.pop(user_id_str, None)
            save_topics(topics)
            bot.send_message(message.chat.id, get_text('topic_deleted', user_id))
        else:
            bot.send_message(message.chat.id, f"Помилка надсилання повідомлення адміну: {e}")

@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and m.message_thread_id is not None)
def admin_reply_handler(message):
    if message.from_user.id not in ADMINS:
        return

    topics = load_topics()
    for user_id_str, thread_id in topics.items():
        if thread_id == message.message_thread_id:
            user_id = int(user_id_str)

            if message.text and message.text.strip().lower() == "/ban":
                banned = load_banned_users()
                if user_id not in banned:
                    banned.append(user_id)
                    save_banned_users(banned)
                    bot.send_message(GROUP_ID, get_text("ban_success", user_id), message_thread_id=thread_id)
                else:
                    bot.send_message(GROUP_ID, get_text("already_banned", user_id), message_thread_id=thread_id)
                return

            if message.text and message.text.strip().lower() == "/unban":
                banned = load_banned_users()
                if user_id in banned:
                    banned.remove(user_id)
                    save_banned_users(banned)
                    bot.send_message(GROUP_ID, get_text("unban_success", user_id), message_thread_id=thread_id)
                else:
                    bot.send_message(GROUP_ID, get_text("not_banned", user_id), message_thread_id=thread_id)
                return

            try:
                if message.content_type == 'text':
                    bot.send_message(user_id, f"\U0001F4AC Адміністратор: {message.text}")
                else:
                    bot.send_message(user_id, get_text('admin_unknown', user_id))
            except Exception as e:
                print(f"[ERROR] Failed to send message to user {user_id}: {e}")
            break

# --- Новини: оновлення новин через послідовний ввід ---

@bot.message_handler(commands=['update_news'])
def update_news_handler(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.send_message(message.chat.id, "Вибач, ця команда тільки для адміністратора.")
        return

    msg = bot.send_message(message.chat.id, "Введи новий текст новини українською:")
    bot.register_next_step_handler(msg, process_news_ua)

def process_news_ua(message):
    ua_text = message.text
    msg = bot.send_message(message.chat.id, "Тепер введи коментар для новини українською:")
    bot.register_next_step_handler(msg, process_news_ua_comment, ua_text)

def process_news_ua_comment(message, ua_text):
    ua_comment = message.text
    msg = bot.send_message(message.chat.id, "Введи новий текст новини англійською:")
    bot.register_next_step_handler(msg, process_news_en, ua_text, ua_comment)

def process_news_en(message, ua_text, ua_comment):
    en_text = message.text
    msg = bot.send_message(message.chat.id, "Тепер введи коментар для новини англійською:")
    bot.register_next_step_handler(msg, process_news_en_comment, ua_text, ua_comment, en_text)

def process_news_en_comment(message, ua_text, ua_comment, en_text):
    en_comment = message.text

    news = load_news()
    news['ua']['text'] = ua_text
    news['ua']['comment'] = ua_comment
    news['en']['text'] = en_text
    news['en']['comment'] = en_comment

    save_news(news)
    bot.send_message(message.chat.id, "✅ Новини успішно оновлено!")

bot.infinity_polling()
