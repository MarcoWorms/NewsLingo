import os
import sqlite3
import requests
import anthropic
import datetime
import logging
import time
from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER")
MODEL_NAME = os.getenv("MODEL_NAME")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

NEWS_API_ENDPOINT = "https://newsapi.org/v2/top-headlines"

if MODEL_PROVIDER == "openai":
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

LANGUAGES = {
    "🇺🇸 English": "🇺🇸 English",
    "🇪🇸 Español": "🇪🇸 Español",
    "🇫🇷 Français": "🇫🇷 Français",
    "🇮🇹 Italiano": "🇮🇹 Italiano",
    "🇩🇪 Deutsch": "🇩🇪 Deutsch",
    "🇧🇷 Português (Brasil)": "🇧🇷 Português pt-BR",
    "🇵🇹 Português (Portugal)": "🇵🇹 Português pt-PT",
    "🇯🇵 日本語": "🇯🇵 日本語",
    "🇨🇳 中文": "🇨🇳 中文",
    "🇰🇷 한국어": "🇰🇷 한국어",
    "🇷🇺 Русский": "🇷🇺 Русский",
    "🇬🇷 Ελληνικά": "🇬🇷 Ελληνικά",
    "🇸🇦 العربية": "🇸🇦 العربية",
}

def create_chat_completion(messages, max_tokens=1000, temperature=0, system=""):
    if MODEL_PROVIDER == "openai":
        if system:
            messages.append({"role": "system", "content": system})
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        content = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        return content, prompt_tokens, completion_tokens
    else:
        response = anthropic_client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            system=system,
        )
        content = response.content[0].text
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        return content, prompt_tokens, completion_tokens
    
def get_db_connection():
    conn = sqlite3.connect(os.getenv("DB_NAME"), check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        known_language TEXT,
        target_language TEXT,
        news_count INTEGER DEFAULT 0
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

def start_command(update: Update, context):
    logger.debug(f"User {update.effective_user.id} started the bot")
    keyboard = [
        [KeyboardButton(language)] for language in LANGUAGES.keys()
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 What is your native language?\n\n🇧🇷 🇵🇹 Qual é a sua língua nativa?\n\n🇯🇵 あなたの母語は何ですか？\n\n🇪🇸 ¿Cuál es su idioma nativo?\n\n🇫🇷 Quelle est votre langue maternelle ?\n\n🇷🇺 Какой ваш родной язык?\n\n🇮🇹 Qual è la tua lingua madre?\n\n🇩🇪 Was ist Ihre Muttersprache?\n\n🇨🇳 你的母语是什么？\n\n🇰🇷 당신의 모국어는 무엇입니까?\n\n🇬🇷 Ποια είναι η μητρική σας γλώσσα;\n\n🇸🇦 ما هي لغتك الأم؟", reply_markup=reply_markup)
    return "known_language"

def known_language_selection(update: Update, context):
    user_id = update.effective_user.id
    user_input = update.message.text

    if user_input not in LANGUAGES:
        logger.debug(f"User {user_id} selected an invalid known language: {user_input}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Please select a valid native language.\n\n🇧🇷 🇵🇹 Selecione um idioma nativo válido.\n\n🇯🇵 有効な母語を選択してください。\n\n🇪🇸 Seleccione un idioma nativo válido.\n\n🇫🇷 Veuillez sélectionner une langue maternelle valide.\n\n🇷🇺 Пожалуйста, выберите действительный родной язык.\n\n🇮🇹 Seleziona una lingua madre valida.\n\n🇩🇪 Bitte wählen Sie eine gültige Muttersprache aus.\n\n🇨🇳 请选择一种有效的母语。\n\n🇰🇷 유효한 모국어를 선택하십시오.\n\n🇬🇷 Επιλέξτε μια έγκυρη μητρική γλώσσα.\n\n🇸🇦 الرجاء اختيار لغة أم صالحة.")
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
    context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 What language are you learning?\n\n🇧🇷 🇵🇹 Que idioma você está aprendendo?\n\n🇯🇵 どの言語を学んでいますか？\n\n🇪🇸 ¿Qué idioma estás aprendiendo?\n\n🇫🇷 Quelle langue apprenez-vous ?\n\n🇷🇺 Какой язык вы изучаете?\n\n🇮🇹 Che lingua stai imparando?\n\n🇩🇪 Welche Sprache lernst du?\n\n🇨🇳 你在学什么语言？\n\n🇰🇷 어떤 언어를 배우고 계십니까?\n\n🇬🇷 Ποια γλώσσα μαθαίνετε;\n\n🇸🇦 ما هي اللغة التي تتعلمها؟", reply_markup=reply_markup)
    return "target_language"

def target_language_selection(update: Update, context):
    user_id = update.effective_user.id
    user_input = update.message.text

    if user_input not in LANGUAGES:
        logger.debug(f"User {user_id} selected an invalid target language: {user_input}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="🇺🇸 Please select a valid learning language.\n\n🇧🇷 🇵🇹 Selecione um idioma de aprendizagem válido.\n\n🇯🇵 有効な学習言語を選択してください。\n\n🇪🇸 Seleccione un idioma de aprendizaje válido.\n\n🇫🇷 Veuillez sélectionner une langue d'apprentissage valide.\n\n🇷🇺 Пожалуйста, выберите действительный язык обучения.\n\n🇮🇹 Seleziona una lingua di apprendimento valida.\n\n🇩🇪 Bitte wählen Sie eine gültige Lernsprache aus.\n\n🇨🇳 请选择一种有效的学习语言。\n\n🇰🇷 유효한 학습 언어를 선택하십시오.\n\n🇬🇷 Επιλέξτε μια έγκυρη γλώσσα εκμάθησης.\n\n🇸🇦 الرجاء اختيار لغة تعلم صالحة.")
        return "target_language"

    target_language = LANGUAGES[user_input]
    logger.debug(f"User {user_id} selected target language: {target_language}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET target_language = ?, news_count = 1 WHERE user_id = ?", (target_language, user_id))
    conn.commit()
    cursor.execute("SELECT known_language FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:

        loading_messages = {
            "🇺🇸 English": "Loading...",
            "🇧🇷 Português pt-BR": "Carregando...",
            "🇵🇹 Português pt-PT": "Carregando...",
            "🇯🇵 日本語": "読み込み中...",
            "🇪🇸 Español": "Cargando...",
            "🇫🇷 Français": "Chargement...",
            "🇷🇺 Русский": "Загрузка...",
            "🇮🇹 Italiano": "Caricamento...",
            "🇩🇪 Deutsch": "Wird geladen...",
            "🇨🇳 中文": "加载中...",
            "🇰🇷 한국어": "로딩 중...",
            "🇬🇷 Ελληνικά": "Φόρτωση...",
            "🇸🇦 العربية": "جار التحميل...",
        }
        
        context.bot.send_message(chat_id=update.effective_chat.id, text=loading_messages.get(user_data[0]))

        news = fetch_news()
        print(news)
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
    prompt = f"Translate the following news to {target_language} and summarize it for a beginner learner that is natively coming from {known_language} but it should be written in {target_language}, only reply with title and a single paragraph like title\n\nsummary, do NOT add your comments or thoughts (don't write TITLE besides the title for example), make sure it contains the complete core of the news but also try to reduce complex words and length where possible, two paragraphs is enough:\n\n{news}"
    content, input_tokens, output_tokens = create_chat_completion(
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO token_usage (user_id, input_tokens, output_tokens)
        VALUES (?, COALESCE((SELECT input_tokens FROM token_usage WHERE user_id = ?), 0) + ?,
                   COALESCE((SELECT output_tokens FROM token_usage WHERE user_id = ?), 0) + ?)
    """, (user_id, user_id, input_tokens, user_id, output_tokens))
    conn.commit()
    conn.close()

    logger.debug(f"Translated and summarized news: {content}")

    prompt_message = {
        "🇺🇸 English": "🇺🇸 Please write back what you understood about the news.",
        "🇧🇷 Português pt-BR": "🇧🇷 Escreva o que você entendeu sobre as notícias.",
        "🇵🇹 Português pt-PT": "🇵🇹 Escreva o que você entendeu sobre as notícias.",
        "🇯🇵 日本語": "🇯🇵 ニュースについて理解したことを書いてください。",
        "🇪🇸 Español": "🇪🇸 Escriba lo que entendió sobre las noticias.",
        "🇫🇷 Français": "🇫🇷 Écrivez ce que vous avez compris des nouvelles.",
        "🇷🇺 Русский": "🇷🇺 Напишите, что вы поняли из новостей.",
        "🇮🇹 Italiano": "🇮🇹 Scrivi cosa hai capito delle notizie.",
        "🇩🇪 Deutsch": "🇩🇪 Schreiben Sie auf, was Sie von den Nachrichten verstanden haben.",
        "🇨🇳 中文": "🇨🇳 请写下你对新闻的理解。",
        "🇰🇷 한국어": "🇰🇷 뉴스에 대해 이해한 내용을 적어주세요.",
        "🇬🇷 Ελληνικά": "🇬🇷 Γράψτε τι καταλάβατε για τα νέα.",
        "🇸🇦 العربية": "🇸🇦 اكتب ما فهمته عن الأخبار.",
    }

    return f"{target_language}\n\n{content}\n\n-----\n\n{prompt_message[known_language]}"

def provide_feedback(user_message, chat_history, known_language, target_language, user_id):
    logger.debug(f"Providing feedback for user message: {user_message}")
    messages = [
        {"role": "user", "content": f"User's known language: {known_language}, Target language: {target_language}"},
    ]

    messages.extend(chat_history)

    logger.debug(f"Chat history: {messages}")

    content, input_tokens, output_tokens = create_chat_completion(
        max_tokens=1000,
        temperature=0,
        system=f"Provide feedback to the user based on their understanding of the summarized news article, remember the user is learning a new language (the one the article was written in, his understanding is after the ----- prompt asking him to do it). Let them know which parts of the article they understood correctly and which parts they missed. You MUST reply using the user native language: {known_language}. If user wrote back to you in the same language as the article it means they are trying hard to learn so provide extra feedback on their grammar in this case!",
        messages=messages,
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO token_usage (user_id, input_tokens, output_tokens)
        VALUES (?, COALESCE((SELECT input_tokens FROM token_usage WHERE user_id = ?), 0) + ?,
                   COALESCE((SELECT output_tokens FROM token_usage WHERE user_id = ?), 0) + ?)
    """, (user_id, user_id, input_tokens, user_id, output_tokens))
    conn.commit()
    conn.close()

    return content


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
    cursor.execute("SELECT user_id, known_language, target_language FROM users")
    users = cursor.fetchall()

    news = fetch_news()

    batch_size = 10
    delay_between_batches = 3

    for i in range(0, len(users), batch_size):
        batch_users = users[i:i+batch_size]

        for user_id, known_language, target_language in batch_users:
            translated_news = translate_and_summarize(news, known_language, target_language, user_id)
            cursor.execute("UPDATE chats SET conversation = ? WHERE chat_id = ?", (str([{"role": "assistant", "content": translated_news}]), user_id))
            cursor.execute("UPDATE users SET news_count = news_count + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            context.bot.send_message(chat_id=user_id, text=translated_news)

        time.sleep(delay_between_batches)

    conn.close()

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
