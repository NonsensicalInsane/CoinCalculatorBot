"""
Minimal serverless webhook handler for Telegram Bot on Vercel
"""

import os
import json
import logging
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, CallbackContext

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Get bot token from environment
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")

bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# Calculate PnL percentage
def calculate_pnl_percentage(entry_price, last_price, is_long=True):
    """Calculate base PnL percentage"""
    if is_long:
        pnl = ((last_price - entry_price) / entry_price) * 100
    else:
        pnl = ((entry_price - last_price) / entry_price) * 100
    return pnl

def calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long=True):
    """Calculate leveraged PnL percentage"""
    base_pnl = calculate_pnl_percentage(entry_price, last_price, is_long)
    return base_pnl * leverage

# Define command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_text(f'Hi {user.first_name}! I\'m your PnL Calculator Bot.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 PnL Calculator Bot Commands:\n\n"
        "/binance <pair> <leverage> <entry> <exit> <type> - Calculate Binance PnL\n"
        "/mexc <pair> <leverage> <entry> <exit> <type> - Calculate MEXC PnL\n"
        "/bitget <pair> <leverage> <entry> <exit> <type> [username] - Calculate BitGet PnL\n\n"
        "/help - Show this help message\n\n"
        "Position type must be 'long' or 'short'"
    )
    update.message.reply_text(help_text)

def process_pnl_command(update: Update, context: CallbackContext, exchange: str) -> None:
    """Generic function to handle PnL calculation for any exchange."""
    try:
        # Extract parameters from command
        args = context.args
        if len(args) < 5:
            update.message.reply_text(f"Not enough arguments. Format: /{exchange} BTCUSDT 10 50000 55000 long")
            return

        trading_pair = args[0].upper()
        leverage = int(args[1])
        entry_price = float(args[2])
        last_price = float(args[3])
        position_type = args[4].lower()
        
        # Optional username for BitGet
        handle_username = None
        if exchange == "bitget" and len(args) > 5:
            handle_username = args[5]
            
        referral_code = os.environ.get('TELEGRAM_REFERRAL_CODE', '48604752')

        # Calculate PnL
        is_long = position_type.lower() == "long"
        pnl_percentage = calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long)
        
        # Format PnL with sign and 2 decimal places
        sign = "+" if pnl_percentage >= 0 else ""
        pnl_text = f"{sign}{pnl_percentage:.2f}%"
        
        # Create a text message with the PnL information
        response_text = (
            f"📊 *{position_type.upper()} {trading_pair}*\n\n"
            f"PnL: {pnl_text}\n"
            f"Entry: {entry_price}\n"
            f"Exit: {last_price}\n"
            f"Leverage: {leverage}x\n"
        )
        
        if handle_username:
            response_text += f"Username: {handle_username}\n"
            
        response_text += f"\nExchange: {exchange.upper()}"
        
        # Send the text response
        update.message.reply_text(response_text)

    except Exception as e:
        logger.error(f"Error processing command: {e}")
        update.message.reply_text(f"Error: {str(e)}")

def generate_binance(update: Update, context: CallbackContext) -> None:
    """Calculate Binance PnL."""
    process_pnl_command(update, context, "binance")

def generate_mexc(update: Update, context: CallbackContext) -> None:
    """Calculate MEXC PnL."""
    process_pnl_command(update, context, "mexc")

def generate_bitget(update: Update, context: CallbackContext) -> None:
    """Calculate BitGet PnL."""
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
        if request is None or not hasattr(request, 'json'):
            return {"statusCode": 400, "body": "Invalid request format"}
            
        request_body = request.json
        if not request_body:
            return {"statusCode": 400, "body": "Empty request body"}
            
        update = Update.de_json(request_body, bot)
        dispatcher.process_update(update)
        return {"statusCode": 200, "body": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}

# Handler for Vercel serverless function
def handler(request):
    """Main handler for Vercel serverless function."""
    if request.method == "POST":
        return webhook(request)
    
    # For GET requests, return a simple status message
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "ok",
            "message": "PnL Calculator Bot is running"
        })
    } 