# CoinCalculatorBot

A powerful tool for generating cryptocurrency trading position images with profit and loss visualization. Supports multiple exchanges including Binance, BitGet, and MEXC.

## Features

- **Multi-Exchange Support**: Generate PnL images for Binance, BitGet, MEXC and more
- **Customizable Templates**: Each exchange has its own visual style and layout
- **Leverage Calculation**: Accurately calculates PnL with leverage
- **QR Code Generation**: Includes referral QR codes
- **Telegram Bot Integration**: Generate and share images directly through Telegram
- **Web Interface**: User-friendly Gradio web UI
- **BitGet Username Support**: Special handling for BitGet templates with usernames
- **Vercel Deployment**: Ready for serverless deployment on Vercel

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/CoinCalculatorBot.git
   cd CoinCalculatorBot
   ```

2. Create a .env file with your API keys:

   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

3. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up your Telegram bot:

   ```bash
   python Source/python/setup_telegram.py
   ```

5. Run the application:

   ```bash
   python Source/python/web_interface.py
   ```

## Telegram Bot Usage

Start the Telegram bot:

```bash
python Source/python/run_telegram_bot.py
```

Commands:
- `/help` - Show available commands
- `/stockmarket` - Show available exchanges
- `/binance BTCUSDT 20 50000 55000 long` - Generate a Binance PnL image
- `/bitget BTCUSDT 20 50000 55000 long BGUSER-M2TRXC4` - Generate a BitGet PnL image with username
- `/mexc SOLUSDT 10 100 110 long` - Generate a MEXC PnL image

## Deployment to Vercel

This project is ready for serverless deployment on Vercel:

1. Fork or clone this repository to your GitHub account

2. Connect your repository to Vercel

3. Configure environment variables in Vercel:
   - Add all the variables from your `.env` file to Vercel's environment variables

4. Deploy the project

5. Use the API endpoint:
   ```
   POST https://your-vercel-url.vercel.app/
   
   {
     "trading_pair": "BTCUSDT",
     "leverage": 20,
     "entry_price": 50000,
     "last_price": 55000,
     "position_type": "long",
     "exchange": "binance"
   }
   ```

## Environment Variables

For security, all API keys and sensitive data should be stored in environment variables:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID where bot should send messages |
| `TELEGRAM_API_ID` | Telegram API ID for client applications |
| `TELEGRAM_API_HASH` | Telegram API hash for client applications |
| `BINANCE_API_KEY` | Binance API key for market data |
| `BINANCE_API_SECRET` | Binance API secret |

## Security Notes

- Never commit your `.env` file to version control
- Always use environment variables for sensitive information
- On Vercel, use the environment variables section in the project settings

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

## Acknowledgments

- [Binance API](https://binance-docs.github.io/apidocs/futures/en/)
- [Gradio](https://gradio.app/)
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/)