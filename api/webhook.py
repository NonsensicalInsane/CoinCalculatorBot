"""
Serverless webhook handler for Telegram Bot on Vercel
"""

import os
import json
import logging
import tempfile
from http import HTTPStatus
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# Configure a minimal environment for serverless
os.environ['MINIMAL_ASSETS'] = 'true'

# Import our core functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Source.python.env_config import load_environment, get_environment_variable

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_environment()

# Get bot token from environment
TOKEN = get_environment_variable('TELEGRAM', 'bot_token')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")

bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# Set up temp directory for serverless environment
TEMP_DIR = tempfile.gettempdir()
os.makedirs(os.path.join(TEMP_DIR, 'output'), exist_ok=True)

# Define command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_text(f'Hi {user.first_name}! I\'m your PnL Image Generator Bot.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 PnL Image Generator Bot Commands:\n\n"
        "/binance <pair> <leverage> <entry> <exit> <type> - Generate Binance image\n"
        "/mexc <pair> <leverage> <entry> <exit> <type> - Generate MEXC image\n"
        "/bitget <pair> <leverage> <entry> <exit> <type> [username] - Generate BitGet image\n\n"
        "/help - Show this help message\n\n"
        "Position type must be 'long' or 'short'"
    )
    update.message.reply_text(help_text)

def process_pnl_command(update: Update, context: CallbackContext, exchange: str) -> None:
    """Generic function to handle PnL image generation for any exchange."""
    try:
        # Extract parameters from command
        args = context.args
        if len(args) < 5:
            update.message.reply_text(f"Not enough arguments. Format: /{exchange} BTCUSDT 10 50000 55000 long")
            return

        trading_pair = args[0]
        leverage = int(args[1])
        entry_price = float(args[2])
        last_price = float(args[3])
        position_type = args[4].lower()
        
        # Optional username for BitGet
        handle_username = None
        if exchange == "bitget" and len(args) > 5:
            handle_username = args[5]
            
        referral_code = get_environment_variable('TELEGRAM', 'referral_code', '48604752')

        # Send a processing message
        message = update.message.reply_text(f"Generating {exchange.upper()} PnL image...")
        
        # In serverless environment, we'll use a minimal version without images
        # Just calculate the PnL and send a text response
        from Source.python.calculations import calculate_leveraged_pnl_percentage
        
        is_long = position_type.lower() == "long"
        pnl_percentage = calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long)
        
        # Format PnL with sign and 2 decimal places
        sign = "+" if pnl_percentage >= 0 else ""
        pnl_text = f"{sign}{pnl_percentage:.2f}%"
        
        # Create a text message with the PnL information
        response_text = (
            f"*{position_type.upper()} {trading_pair} {leverage}x*\n\n"
            f"📊 PnL: {pnl_text}\n"
            f"📈 Entry: {entry_price}\n"
            f"📉 Exit: {last_price}\n"
            f"⚡ Leverage: {leverage}x\n"
        )
        
        if handle_username:
            response_text += f"👤 Username: {handle_username}\n"
            
        response_text += f"\nExchange: {exchange.upper()}"
        
        # Delete the processing message
        bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
        
        # Send the text response
        update.message.reply_text(response_text)

    except Exception as e:
        logger.error(f"Error processing command: {e}")
        update.message.reply_text(f"Error: {str(e)}")

def generate_binance(update: Update, context: CallbackContext) -> None:
    """Generate a Binance PnL calculation."""
    process_pnl_command(update, context, "binance")

def generate_mexc(update: Update, context: CallbackContext) -> None:
    """Generate a MEXC PnL calculation."""
    process_pnl_command(update, context, "mexc")

def generate_bitget(update: Update, context: CallbackContext) -> None:
    """Generate a BitGet PnL calculation."""
    process_pnl_command(update, context, "bitget")

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("binance", generate_binance))
dispatcher.add_handler(CommandHandler("mexc", generate_mexc))
dispatcher.add_handler(CommandHandler("bitget", generate_bitget))

# Webhook handler
def webhook(request):
    """Handle webhook requests from Telegram."""
    try:
        request_body = request.json
        logger.info(f"Received update: {json.dumps(request_body)}")
        
        update = Update.de_json(request_body, bot)
        dispatcher.process_update(update)
        return {"statusCode": 200, "body": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}

# Handler for Vercel serverless function
def handler(request):
    """Main handler for Vercel serverless function."""
    # Check if it's a POST request with a webhook
    if request.method == "POST":
        return webhook(request)
        
    # For GET requests, return a simple status check
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "ok",
            "message": "PnL Calculator Bot API is running. Send requests to the webhook endpoint."
        })
    } 