# NewsLingo 📰🌍🎓

- **Use it now! https://t.me/NewsLingoBot**

Everyday news in a language you want to learn!

Reply to the bot with what you understood and receive feedback!

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

## License 📄

This project is licensed under the public domain (CC0)
