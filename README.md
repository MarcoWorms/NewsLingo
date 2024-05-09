# NewsLingo 📰🌍🎓

NewsLingo is a Telegram bot that helps you learn a new language by sending you short daily news articles written in it. You can reply to the bot with what you understood from the article, and it will provide you with personalized feedback to help you improve your language skills. 📝💡

## Features ✨

- 🌐 Supports multiple languages:
  - 🇺🇸 English
  - 🇧🇷 Portuguese (Brazil)
  - 🇵🇹 Portuguese (Portugal)
  - 🇯🇵 Japanese
  - 🇪🇸 Spanish
  - 🇫🇷 French
  - 🇷🇺 Russian
- 🗞️ Fetches the latest world news from newsapi.org
- 🤖 Utilizes Anthropic's Claude AI to translate and summarize news articles for beginner learners
- 💬 Provides personalized feedback on your understanding of the article in your native language
- 📅 Sends a new article every day to keep you engaged and learning consistently

## Getting Started 🚀

To run the NewsLingo bot locally using Docker, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/newslingo.git
   cd newslingo
   ```

2. Create a `.env` file in the project root directory with the following environment variables:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ANTHROPIC_API_KEY=your_anthropic_api_key
   NEWS_API_KEY=your_news_api_key
   DB_NAME=newslingo.db
   ```

3. Build the Docker image:
   ```
   docker build -t newslingo-bot .
   ```

4. Run the Docker container:
   ```
   docker run -d --name newslingo-bot newslingo-bot
   ```

5. Start chatting with your NewsLingo bot on Telegram! 🎉

## Technologies Used 🛠️

- 🐍 Python
- 🤖 python-telegram-bot
- 🧠 Anthropic Claude AI
- 📡 News API
- 🐳 Docker
- 💾 SQLite

## Contributing 🤝

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.

## License 📄

This project is licensed under the public domain (CC0)
