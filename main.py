import os
import sqlite3
import requests
import anthropic
import datetime
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

NEWS_API_ENDPOINT = "https://newsapi.org/v2/top-headlines"

LANGUAGES = {
    "🇺🇸 English": "🇺🇸 English",
    "🇧🇷 Português (Brasil)": "🇧🇷 Português pt-BR",
    "🇵🇹 Português (Portugal)": "🇵🇹 Português pt-PT",
    "🇯🇵 日本語": "🇯🇵 日本語",
    "🇪🇸 Español": "🇪🇸 Español",
    "🇫🇷 Français": "🇫🇷 Français",
    "🇷🇺 Русский": "🇷🇺 Русский",
}

def get_db_connection():
    conn = sqlite3.connect(os.getenv("DB_NAME"), check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            known_language TEXT,
            target_language TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            conversation TEXT
        )
    """)
    conn.commit()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            user_id INTEGER PRIMARY KEY,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0
        )
    """)

    return conn

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def start_command(update: Update, context):
    logger.debug(f"User {update.effective_user.id} started the bot")
    keyboard = [
        [KeyboardButton(language)] for language in LANGUAGES.keys()
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Please select your known language:\n\n🇧🇷 🇵🇹 Por favor, selecione seu idioma conhecido:\n\n🇯🇵 既知の言語を選択してください:\n\n🇪🇸 Por favor, seleccione su idioma conocido:\n\n🇫🇷 Veuillez sélectionner votre langue connue:\n\n🇷🇺 Пожалуйста, выберите известный вам язык:", reply_markup=reply_markup)
    return "known_language"

def known_language_selection(update: Update, context):
    user_id = update.effective_user.id
    user_input = update.message.text

    if user_input not in LANGUAGES:
        logger.debug(f"User {user_id} selected an invalid known language: {user_input}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Please select a valid known language.\n\n🇧🇷 🇵🇹 Por favor, selecione um idioma conhecido válido.\n\n🇯🇵 有効な既知の言語を選択してください。\n\n🇪🇸 Por favor, seleccione un idioma conocido válido.\n\n🇫🇷 Veuillez sélectionner une langue connue valide.\n\n🇷🇺 Пожалуйста, выберите действительный известный язык.")
        return "known_language"

    known_language = LANGUAGES[user_input]
    logger.debug(f"User {user_id} selected known language: {known_language}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, known_language) VALUES (?, ?)", (user_id, known_language))
    conn.commit()
    conn.close()

    keyboard = [
        [KeyboardButton(language)] for language in LANGUAGES.keys()
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Please select the news language:\n\n🇧🇷 🇵🇹 Por favor, selecione o idioma das notícias:\n\n🇯🇵 ニュースの言語を選択してください:\n\n🇪🇸 Por favor, seleccione el idioma de las noticias:\n\n🇫🇷 Veuillez sélectionner la langue des actualités:\n\n🇷🇺 Пожалуйста, выберите язык новостей:", reply_markup=reply_markup)
    return "target_language"

def target_language_selection(update: Update, context):
    user_id = update.effective_user.id
    user_input = update.message.text

    if user_input not in LANGUAGES:
        logger.debug(f"User {user_id} selected an invalid target language: {user_input}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Please select a valid news language.\n\n🇧🇷 🇵🇹 Por favor, selecione um idioma de notícias válido.\n\n🇯🇵 有効なニュースの言語を選択してください。\n\n🇪🇸 Por favor, seleccione un idioma de noticias válido.\n\n🇫🇷 Veuillez sélectionner une langue d'actualités valide.\n\n🇷🇺 Пожалуйста, выберите действительный язык новостей.")
        return "target_language"

    target_language = LANGUAGES[user_input]
    logger.debug(f"User {user_id} selected target language: {target_language}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET target_language = ? WHERE user_id = ?", (target_language, user_id))
    conn.commit()
    cursor.execute("SELECT known_language FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Loading...\n\n🇧🇷 🇵🇹 Carregando...\n\n🇯🇵 読み込み中...\n\n🇪🇸 Cargando...\n\n🇫🇷 Chargement...\n\n🇷🇺 Загрузка...")

        news = fetch_news()
        translated_news = translate_and_summarize(news, user_data[0], target_language, user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO chats (chat_id, user_id, conversation) VALUES (?, ?, ?)",
                       (user_id, user_id, str([{"role": "assistant", "content": translated_news}])))
        conn.commit()
        conn.close()

        context.bot.send_message(chat_id=update.effective_chat.id, text=translated_news)

    return ConversationHandler.END

def fetch_news():
    logger.debug("Fetching news from News API")
    response = requests.get(NEWS_API_ENDPOINT, params={"apiKey": NEWS_API_KEY, "language": "en"})
    articles = response.json()["articles"]
    
    if articles:
        title = articles[0].get("title", "")
        description = articles[0].get("description", "")
        logger.debug(f"Fetched news: {title}")
        return f"{title}\n\n{description}"
    else:
        logger.debug("No news available")
        return "No news available at the moment."

def translate_and_summarize(news, known_language, target_language, user_id):
    logger.debug(f"Translating and summarizing news from {known_language} to {target_language}")
    prompt = f"Translate the following news to {target_language} and summarize it for a beginner learner that is natively coming from {known_language} but it should be written in {target_language}, only reply with the title and summary directly (don't write TITLE besides the title for example) and do NOT add your comments or thoughts, make sure it contains the complete core of the news but also try to reduce complex words and length where possible, two paragraphs is enough:\n\n{news}"
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        temperature=0,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO token_usage (user_id, input_tokens, output_tokens)
        VALUES (?, COALESCE((SELECT input_tokens FROM token_usage WHERE user_id = ?), 0) + ?,
                   COALESCE((SELECT output_tokens FROM token_usage WHERE user_id = ?), 0) + ?)
    """, (user_id, user_id, input_tokens, user_id, output_tokens))
    conn.commit()
    conn.close()

    logger.debug(f"Translated and summarized news: {response.content[0].text}")

    # Add a message in the user's target language to prompt them to write back what they understood
    prompt_message = {
        "🇺🇸 English": "🇺🇸 Please write back what you understood about the above news.",
        "🇧🇷 Português pt-BR": "🇧🇷 Por favor, escreva de volta o que você entendeu sobre as notícias acima.",
        "🇵🇹 Português pt-PT": "🇵🇹 Por favor, escreva de volta o que você entendeu sobre as notícias acima.",
        "🇯🇵 日本語": "🇯🇵 上記のニュースについて理解したことを書き返してください。",
        "🇪🇸 Español": "🇪🇸 Por favor, escriba de vuelta lo que entendió sobre las noticias anteriores.",
        "🇫🇷 Français": "🇫🇷 Veuillez écrire en retour ce que vous avez compris des nouvelles ci-dessus.",
        "🇷🇺 Русский": "🇷🇺 Пожалуйста, напишите обратно, что вы поняли из приведенных выше новостей.",
    }

    return f"{target_language}\n\n{response.content[0].text}\n\n-----\n\n{prompt_message[known_language]}"

def provide_feedback(user_message, chat_history, known_language, target_language, user_id):
    logger.debug(f"Providing feedback for user message: {user_message}")
    messages = [
        {"role": "user", "content": f"User's known language: {known_language}, Target language: {target_language}"},
    ]

    messages.extend(chat_history)

    logger.debug(f"Chat history: {messages}")

    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        temperature=0,
        system=f"Provide feedback to the user based on their understanding of the summarized news article, remember the user is learning a new language (the one the article was written in, his understanding is after the ----- prompt asking him to do it). Let them know which parts of the article they understood correctly and which parts they missed. You MUST reply using the user native language: {known_language}. If user wrote back to you in the same language as the article it means they are trying hard to learn so provide extra feedback on their grammar in this case!",
        messages=messages,
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO token_usage (user_id, input_tokens, output_tokens)
        VALUES (?, COALESCE((SELECT input_tokens FROM token_usage WHERE user_id = ?), 0) + ?,
                   COALESCE((SELECT output_tokens FROM token_usage WHERE user_id = ?), 0) + ?)
    """, (user_id, user_id, input_tokens, user_id, output_tokens))
    conn.commit()
    conn.close()

    return response.content[0].text


def handle_user_message(update: Update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user_message = update.message.text
    logger.debug(f"User {user_id} sent message: {user_message}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT known_language, target_language FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        known_language, target_language = user_data

        cursor.execute("SELECT conversation FROM chats WHERE chat_id = ?", (chat_id,))
        chat_data = cursor.fetchone()

        if chat_data:
            conversation = eval(chat_data[0])
        else:
            conversation = []

        conversation.append({"role": "user", "content": user_message})
        feedback = provide_feedback(user_message, conversation, known_language, target_language, user_id)
        conversation.append({"role": "assistant", "content": feedback})

        cursor.execute("UPDATE chats SET conversation = ? WHERE chat_id = ?", (str(conversation), chat_id))
        conn.commit()

        context.bot.send_message(chat_id=chat_id, text=feedback)

    conn.close()

def daily_job(context):
    logger.debug("Running daily job")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, target_language, known_language FROM users")
    users = cursor.fetchall()
    conn.close()

    news = fetch_news()

    for user_id, known_language, target_language in users:
        translated_news = translate_and_summarize(news, known_language, target_language, user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE chats SET conversation = ? WHERE chat_id = ?", (str([{"role": "assistant", "content": translated_news}]), user_id))
        conn.commit()
        conn.close()

        context.bot.send_message(chat_id=user_id, text=translated_news)

def main():
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    config_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            "known_language": [MessageHandler(Filters.text & ~Filters.command, known_language_selection)],
            "target_language": [MessageHandler(Filters.text & ~Filters.command, target_language_selection)],
        },
        fallbacks=[CommandHandler("start", start_command)],
    )

    dispatcher.add_handler(config_handler)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_message))

    job_queue = updater.job_queue
    job_queue.run_daily(daily_job, time=datetime.time(hour=13, minute=0, second=0))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()