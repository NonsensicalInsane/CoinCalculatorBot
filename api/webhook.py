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

# Import our core functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Source.python.core import generate_pnl_image
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
        "🤖 *PnL Image Generator Bot Commands:*\n\n"
        "/binance <pair> <leverage> <entry> <exit> <type> - Generate Binance image\n"
        "/mexc <pair> <leverage> <entry> <exit> <type> - Generate MEXC image\n"
        "/bitget <pair> <leverage> <entry> <exit> <type> [username] - Generate BitGet image\n\n"
        "/stockmarket - Show available stockmarkets\n"
        "/help - Show this help message\n\n"
        "*Position type* must be 'long' or 'short'\n"
        "*Username* is only used for BitGet template"
    )
    update.message.reply_text(help_text)

def generate_binance(update: Update, context: CallbackContext) -> None:
    """Generate a Binance PnL image."""
    try:
        # Extract parameters from command
        args = context.args
        if len(args) < 5:
            update.message.reply_text("Not enough arguments. Format: /binance BTCUSDT 10 50000 55000 long")
            return

        trading_pair = args[0]
        leverage = int(args[1])
        entry_price = float(args[2])
        last_price = float(args[3])
        position_type = args[4].lower()
        referral_code = get_environment_variable('TELEGRAM', 'referral_code', '48604752')

        # Send a processing message
        message = update.message.reply_text("Generating Binance PnL image...")

        # Override output directory for serverless environment
        os.environ['OUTPUT_DIR'] = os.path.join(TEMP_DIR, 'output')
        
        # Generate image
        image_path = generate_pnl_image(
            trading_pair=trading_pair,
            leverage=leverage,
            entry_price=entry_price,
            last_price=last_price,
            referral_code=referral_code,
            position_type=position_type,
            exchange="binance"
        )

        # Send the image
        with open(image_path, 'rb') as img:
            bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img,
                caption=f"{trading_pair} {leverage}x {position_type.capitalize()} • Entry: {entry_price} • Exit: {last_price}"
            )
        
        # Delete the processing message
        bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
        
        # Clean up the temporary file
        try:
            os.remove(image_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {e}")

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        update.message.reply_text(f"Error generating image: {str(e)}")

def generate_mexc(update: Update, context: CallbackContext) -> None:
    """Generate a MEXC PnL image."""
    try:
        # Extract parameters from command
        args = context.args
        if len(args) < 5:
            update.message.reply_text("Not enough arguments. Format: /mexc BTCUSDT 10 50000 55000 long")
            return

        trading_pair = args[0]
        leverage = int(args[1])
        entry_price = float(args[2])
        last_price = float(args[3])
        position_type = args[4].lower()
        referral_code = get_environment_variable('TELEGRAM', 'referral_code', '48604752')

        # Send a processing message
        message = update.message.reply_text("Generating MEXC PnL image...")

        # Override output directory for serverless environment
        os.environ['OUTPUT_DIR'] = os.path.join(TEMP_DIR, 'output')
        
        # Generate image
        image_path = generate_pnl_image(
            trading_pair=trading_pair,
            leverage=leverage,
            entry_price=entry_price,
            last_price=last_price,
            referral_code=referral_code,
            position_type=position_type,
            exchange="mexc"
        )

        # Send the image
        with open(image_path, 'rb') as img:
            bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img,
                caption=f"{trading_pair} {leverage}x {position_type.capitalize()} • Entry: {entry_price} • Exit: {last_price}"
            )
        
        # Delete the processing message
        bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
        
        # Clean up the temporary file
        try:
            os.remove(image_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {e}")

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        update.message.reply_text(f"Error generating image: {str(e)}")

def generate_bitget(update: Update, context: CallbackContext) -> None:
    """Generate a BitGet PnL image."""
    try:
        # Extract parameters from command
        args = context.args
        if len(args) < 5:
            update.message.reply_text("Not enough arguments. Format: /bitget BTCUSDT 10 50000 55000 long [username]")
            return

        trading_pair = args[0]
        leverage = int(args[1])
        entry_price = float(args[2])
        last_price = float(args[3])
        position_type = args[4].lower()
        # Optional username for BitGet
        handle_username = args[5] if len(args) > 5 else None
        referral_code = get_environment_variable('TELEGRAM', 'referral_code', '48604752')

        # Send a processing message
        message = update.message.reply_text("Generating BitGet PnL image...")

        # Override output directory for serverless environment
        os.environ['OUTPUT_DIR'] = os.path.join(TEMP_DIR, 'output')
        
        # Generate image
        image_path = generate_pnl_image(
            trading_pair=trading_pair,
            leverage=leverage,
            entry_price=entry_price,
            last_price=last_price,
            referral_code=referral_code,
            position_type=position_type,
            exchange="bitget",
            handle_username=handle_username
        )

        # Send the image
        with open(image_path, 'rb') as img:
            bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img,
                caption=f"{trading_pair} {leverage}x {position_type.capitalize()} • Entry: {entry_price} • Exit: {last_price}"
            )
        
        # Delete the processing message
        bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
        
        # Clean up the temporary file
        try:
            os.remove(image_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {e}")

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        update.message.reply_text(f"Error generating image: {str(e)}")

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
    
    # Return a simple health check for GET requests
    return {
        "statusCode": HTTPStatus.OK,
        "body": json.dumps({
            "status": "ok",
            "message": "Telegram bot webhook is active",
            "bot_info": bot.get_me().to_dict()
        })
    } 