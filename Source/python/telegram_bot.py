"""
Telegram Bot for PnL Image Generator
A clean, integrated interface for generating trading position images via Telegram
"""


import logging
from datetime import datetime
import traceback
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackQueryHandler, CallbackContext
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Update imports to use newer modules instead of core.py
try:
    from Source.python.image_generator import generate_unified_pnl_image
    from Source.python.calculations import calculate_leveraged_pnl_percentage
except ImportError:
    try:
        # Try direct imports if Source.python path doesn't work
        from image_generator import generate_unified_pnl_image
        from calculations import calculate_leveraged_pnl_percentage
    except ImportError:
        logger.error("Failed to import required modules. Make sure image_generator.py and calculations.py exist.")
        raise

# Import scraper functionality
try:
    from Source.python.binance_scraper import get_max_leverage, update_symbol_leverage, get_available_symbols
    SCRAPER_AVAILABLE = True
    logger.info("Successfully imported Binance Scraper")
except ImportError:
    try:
        from binance_scraper import get_max_leverage, update_symbol_leverage, get_available_symbols
        SCRAPER_AVAILABLE = True
        logger.info("Successfully imported Binance Scraper")
    except ImportError:
        logger.warning("Binance Scraper not available - leverage data may be limited")
        SCRAPER_AVAILABLE = False

# Try to import API functionality as fallback
try:
    from Source.python.binance_api import get_current_price
    API_AVAILABLE = True
except ImportError:
    try:
        from binance_api import get_current_price
        API_AVAILABLE = True
    except ImportError:
        logger.warning("Binance API not available - price data will be limited")
        API_AVAILABLE = False

# Import configuration utilities
try:
    from Source.python.env_config import load_environment, get_environment_variable
except ImportError:
    try:
        from env_config import load_environment, get_environment_variable
    except ImportError:
        logger.warning("Environment config utilities not available - falling back to basic config")
        load_environment = lambda: None
        get_environment_variable = lambda section, key, default=None: None

class PnLTelegramBot:
    """Telegram Bot for generating PnL visualization images"""
    
    def __init__(self, config_path='config.cfg'):
        """Initialize the bot with configuration"""
        # Load environment variables
        load_environment()
        
        # Get the referral code from environment variables
        self.referral_code = get_environment_variable('TELEGRAM', 'referral_code', '48604752')
        
        # Try to get configuration from environment variables first
        self.bot_token = get_environment_variable('TELEGRAM', 'bot_token')
        self.chat_id = get_environment_variable('TELEGRAM', 'chat_id')        
        # Fall back to config file if environment variables not found
        if not self.bot_token or not self.chat_id:
            logger.info("Environment variables not found, trying config file")

        # Check if we have the required configuration
        if not self.bot_token or not self.chat_id:
            logger.error("Missing required Telegram configuration")
            raise ValueError("Missing required Telegram configuration")
        
        # Initialize the updater and dispatcher
        self.updater = Updater(self.bot_token)
        self.dispatcher = self.updater.dispatcher
        
        # Default exchange template
        self.default_exchange = get_environment_variable('EXCHANGE_TEMPLATES', 'default', 'binance')
        
        # Get available exchanges from config
        templates_str = get_environment_variable('EXCHANGE_TEMPLATES', 'templates', 'binance,mexc,bitget')
        self.available_exchanges = [t.strip() for t in templates_str.split(',') if t.strip()]
        
        # Register command handlers
        self.register_handlers()
        
        logger.info("PnL Telegram Bot initialized")
    
    def update_leverage_data(self, symbol):
        """Update leverage data for a symbol using scraper"""
        if SCRAPER_AVAILABLE:
            try:
                # Force update the leverage data for this symbol
                logger.info(f"Force-updating leverage data for {symbol}")
                update_symbol_leverage(symbol)
                
                # Get the updated max leverage
                max_leverage = get_max_leverage(symbol)
                logger.info(f"Updated max leverage for {symbol}: {max_leverage}x")
                return max_leverage
            except Exception as e:
                logger.error(f"Error updating leverage with scraper: {e}")
        
        # Default values for common coins if scraping failed
        common_leverages = {
            "BTCUSDT": 125, "ETHUSDT": 100, "BNBUSDT": 75, 
            "ADAUSDT": 75, "SOLUSDT": 50, "XRPUSDT": 75, 
            "DOGEUSDT": 75, "LINKUSDT": 75, "ZETAUSDT": 75,
            "DOTUSD": 75, "MATICUSDT": 50, "AVAXUSDT": 50
        }
        
        if symbol.upper() in common_leverages:
            logger.info(f"Using known common leverage for {symbol}: {common_leverages[symbol.upper()]}x")
            return common_leverages[symbol.upper()]
        
        logger.info(f"Using default leverage for {symbol}: 20x")
        return 20
    
    def get_current_market_price(self, symbol):
        """Get current market price for a symbol"""
        if API_AVAILABLE:
            try:
                price = get_current_price(symbol)
                if price:
                    logger.info(f"Got current price for {symbol}: ${price}")
                    return price
            except Exception as e:
                logger.error(f"Error getting price from API: {e}")
        
        return None
    
    def generate_pnl_image(self, update, trading_pair, leverage, entry_price, last_price, 
                          position_type, exchange, handle_username=None, referral_code=None):
        """Generate a PnL image and send it to the chat"""
        # Send a "processing" message first
        processing_message = update.message.reply_text("🔄 Generating PnL image...")
        
        try:
            # Ensure the leverage doesn't exceed the maximum for this symbol
            max_leverage = self.update_leverage_data(trading_pair)
            if leverage > max_leverage:
                update.message.reply_text(
                    f"⚠️ Warning: The maximum leverage for {trading_pair} is {max_leverage}x. "
                    f"Limiting leverage to {max_leverage}x."
                )
                leverage = max_leverage
            
            # Generate the image using the updated image_generator function
            img_path = generate_unified_pnl_image(
                trading_pair=trading_pair,
                leverage=leverage,
                entry_price=entry_price,
                last_price=last_price,
                referral_code=referral_code,
                position_type=position_type,
                exchange=exchange,
                handle_username=handle_username
            )
            
            # Calculate PnL percentage
            is_long = position_type.lower() == "long"
            pnl = calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long)
            pnl_formatted = f"+{pnl:.2f}%" if pnl >= 0 else f"{pnl:.2f}%"
            
            # Get current market price if available
            current_price = self.get_current_market_price(trading_pair)
            current_price_info = ""
            if current_price:
                price_diff = ((current_price - last_price) / last_price) * 100
                price_diff_formatted = f"+{price_diff:.2f}%" if price_diff >= 0 else f"{price_diff:.2f}%"
                current_price_info = f"\nCurrent market price: ${current_price} ({price_diff_formatted} from last price)"
            
            # Create caption with details
            caption = (
                f"*{trading_pair}* ({position_type}) with *{leverage}x* leverage\n"
                f"Entry: ${entry_price:.2f}  |  Last: ${last_price:.2f}\n"
                f"PnL: *{pnl_formatted}*{current_price_info}"
            )
            
            # Delete "processing" message
            processing_message.delete()
            
            # Send the image with caption
            with open(img_path, 'rb') as photo:
                update.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
            
            # Add buttons for other exchange templates
            if len(self.available_exchanges) > 1:
                buttons = []
                for template in self.available_exchanges:
                    if template != exchange:
                        # Create callback data with all params
                        callback_data = f"gen|{trading_pair}|{leverage}|{entry_price}|{last_price}|{position_type}|{referral_code}|{template}"
                        buttons.append(InlineKeyboardButton(f"{template.capitalize()}", callback_data=callback_data))
                
                if buttons:
                    keyboard = InlineKeyboardMarkup([buttons])
                    update.message.reply_text(
                        "Generate with different exchange template:",
                        reply_markup=keyboard
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating PnL image: {e}")
            import traceback
            traceback.print_exc()
            
            # Delete "processing" message
            try:
                processing_message.delete()
            except:
                pass
                
            # Send error message
            update.message.reply_text(f"❌ Error generating image: {str(e)}")
            return False

    def register_handlers(self):
        """Register all command handlers"""
        # Register command handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CommandHandler("stockmarket", self.stockmarket_command))
        
        # Add handlers for each exchange template
        for template in self.available_exchanges:
            self.dispatcher.add_handler(CommandHandler(template, self.template_shortcut))
        
        # Add callback query handler for buttons
        self.dispatcher.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add general message handler
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        # Add error handler
        self.dispatcher.add_error_handler(self.error_handler)
        
        logger.info(f"Bot initialized with {len(self.available_exchanges)} exchange templates: {', '.join(self.available_exchanges)}")
    
    def start_command(self, update: Update, context: CallbackContext):
        """Handle the /start command"""
        user = update.effective_user
        update.message.reply_text(
            f"Hello {user.first_name}! I'm your PnL Image Generator Bot.\n\n"
            f"Use /generate command to create PnL visualizations for your trades.\n"
            f"Use /help to see all available commands."
        )
    
    def help_command(self, update: Update, context: CallbackContext):
        """Handle the /help command"""
        help_text = (
            "🤖 PnL Image Generator Bot Commands:\n\n"
            "/binance <pair> <leverage> <entry> <exit> <type> <referral_code> - Generate Binance image\n"
            "/mexc <pair> <leverage> <entry> <exit> <type> <referral_code> - Generate MEXC image\n"
            "/bitget <pair> <leverage> <entry> <exit> <type> <referral_code> [username] - Generate BitGet image\n\n"
            "Example: /binance BTCUSDT 20 50000 55000 long 48604752\n\n"
            "/stockmarket - Show available stockmarkets\n"
            "/help - Show this help message\n\n"
            "Position type must be 'long' or 'short'\n"
            "Exchange can be: " + ", ".join(self.available_exchanges) + "\n"
            "Username is only used for BitGet template"
        )
        
        update.message.reply_text(help_text)
    
    def template_shortcut(self, update: Update, context: CallbackContext):
        """Handle exchange-specific shortcut commands like /binance, /mexc, etc."""
        # Extract the exchange name from the command
        command = update.message.text.strip().split()[0][1:]  # Remove the / prefix
        
        # Check if the command is a valid template
        if command not in self.available_exchanges:
            update.message.reply_text(f"Unknown stockmarket: {command}")
            return
        
        # Special handling for BitGet with username
        if command == "bitget" and len(context.args) >= 7:
            # Extract the username and create proper args list
            username = context.args[6]
            # Create new args list with the command injected before the username
            new_args = context.args[:6] + [command, username]
            context.args = new_args
        elif context.args:
            # For other templates, add the exchange as the 6th argument
            context.args = list(context.args) + [command]
        else:
            # If no args, show help for this specific template
            template_help = (
                f"{command.capitalize()} Stockmarket Usage:\n\n"
                f"/{command} <pair> <leverage> <entry> <exit> <type> <referral_code>"
            )
            if command == "bitget":
                template_help += " [username]"
            
            template_help += (
                f"\n\nExample: /{command} BTCUSDT 20 50000 55000 long 48604752"
            )
            
            update.message.reply_text(template_help)
            return
            
        # Process as a regular generate command
        self.generate_command(update, context)
    
    def generate_command(self, update: Update, context: CallbackContext):
        """Handle the /generate command"""
        if not context.args or len(context.args) < 5:
            update.message.reply_text(
                "❌ Not enough arguments.\n\nUsage: /generate <pair> <leverage> <entry> <exit> <type> [exchange] [username]"
            )
            return
        
        try:
            # Parse the arguments
            trading_pair = context.args[0].upper()
            leverage = int(context.args[1])
            entry_price = float(context.args[2])
            last_price = float(context.args[3])
            position_type = context.args[4].lower()
            referral_code = context.args[5]  
            # Validate position type
            if position_type not in ["long", "short"]:
                update.message.reply_text("Position type must be 'long' or 'short'")
                return
            
            # Check for optional exchange parameter
            exchange = self.default_exchange
            if len(context.args) >= 6:
                requested_exchange = context.args[6].lower()
                if requested_exchange in self.available_exchanges:
                    exchange = requested_exchange
                else:
                    update.message.reply_text(f"Unknown stockmarket: {requested_exchange}. Using default: {exchange}")
            
            # Check for BitGet username parameter
            handle_username = None
            if exchange == "bitget" and len(context.args) >= 7:
                handle_username = context.args[7]
                logger.info(f"Using BitGet username: {handle_username}")
            
            # Send a status message
            status_message = update.message.reply_text(
                f"⏳ Generating {exchange.upper()} PnL image for {trading_pair}... Please wait."
            )
            
            # Calculate PnL percentage for the caption
            is_long = position_type == "long"
            pnl_percentage = calculate_leveraged_pnl_percentage(
                entry_price, last_price, leverage, is_long
            )
            sign = "+" if pnl_percentage >= 0 else ""
            
            try:
                # Generate the PnL image
                image_path = generate_unified_pnl_image(
                    trading_pair=trading_pair,
                    leverage=leverage,
                    entry_price=entry_price,
                    last_price=last_price,
                    referral_code=referral_code,
                    position_type=position_type,
                    exchange=exchange,
                    handle_username=handle_username
                )
                
                # Create a caption
                caption = f"*{position_type.upper()} {trading_pair} {leverage}x:* {sign}{pnl_percentage:.2f}% PnL"
                
                # Add buttons for quick actions
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Reverse Position", 
                                            callback_data=f"reverse_{trading_pair}_{leverage}_{entry_price}_{last_price}_{position_type}_{exchange}")
                    ],
                    [
                        InlineKeyboardButton("📊 New Image", 
                                           callback_data=f"new_{exchange}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send the generated image
                with open(image_path, 'rb') as img_file:
                    update.message.reply_photo(
                        photo=img_file,
                        caption=caption, 
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                
                # Delete the status message
                status_message.delete()
                
            except Exception as e:
                logger.error(f"Error generating image: {e}")
                logger.error(traceback.format_exc())
                update.message.reply_text(f"❌ Error generating image: {str(e)}")
                if status_message:
                    status_message.delete()
                
        except ValueError as e:
            update.message.reply_text(f"❌ Invalid number format: {str(e)}")
        except Exception as e:
            logger.error(f"Error in generate_command: {e}")
            logger.error(traceback.format_exc())
            update.message.reply_text(f"❌ Error: {str(e)}")
    
    def stockmarket_command(self, update: Update, context: CallbackContext):
        """Handle the /stockmarket command to show available exchange templates"""
        template_buttons = []
        row = []
        
        # Create buttons for each template
        for template in self.available_exchanges:
            if len(row) < 2:
                if template == "bitget":
                    row.append(InlineKeyboardButton(template.upper(), callback_data=f"new_{template}"))
                else:
                    row.append(InlineKeyboardButton(template.upper(), callback_data=f"new_{template}"))
            else:
                template_buttons.append(row)
                row = [InlineKeyboardButton(template.upper(), callback_data=f"new_{template}")]
        
        # Add the last row if it's not empty
        if row:
            template_buttons.append(row)
        
        reply_markup = InlineKeyboardMarkup(template_buttons)
        
        update.message.reply_text(
            "📊 *Available Stockmarkets:*\n\n"
            "Select a stockmarket to create a new PnL image:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def button_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        query.answer()
        
        # Get callback data
        data = query.data
        
        # Handle "reverse position" callback
        if data.startswith("reverse_"):
            # Parse the callback data
            parts = data.split("_")
            if len(parts) >= 7:
                _, trading_pair, leverage, entry_price, last_price, position_type, referral_code, exchange = parts
                
                # Swap the position type
                new_position_type = "short" if position_type == "long" else "long"
                
                # Update the message
                query.edit_message_caption(
                    caption=f"Generating reversed position: {new_position_type.upper()} {trading_pair}...",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                try:
                    # Generate the new image
                    image_path = generate_unified_pnl_image(
                        trading_pair=trading_pair,
                        leverage=int(leverage),
                        entry_price=float(entry_price),
                        last_price=float(last_price),
                        referral_code=referral_code,
                        position_type=new_position_type,
                        exchange=exchange
                    )
                    
                    # Calculate PnL percentage for the caption
                    is_long = new_position_type == "long"
                    pnl_percentage = calculate_leveraged_pnl_percentage(
                        float(entry_price), float(last_price), int(leverage), is_long
                    )
                    sign = "+" if pnl_percentage >= 0 else ""
                    
                    # Create a caption
                    caption = f"*{new_position_type.upper()} {trading_pair} {leverage}x:* {sign}{pnl_percentage:.2f}% PnL"
                    
                    # Add buttons for quick actions
                    keyboard = [
                        [
                            InlineKeyboardButton("🔄 Reverse Position", 
                                               callback_data=f"reverse_{trading_pair}_{leverage}_{entry_price}_{last_price}_{new_position_type}_{exchange}")
                        ],
                        [
                            InlineKeyboardButton("📊 New Image", 
                                               callback_data=f"new_{exchange}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send the new image
                    with open(image_path, 'rb') as img_file:
                        query.message.reply_photo(
                            photo=img_file,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=reply_markup
                        )
                    
                except Exception as e:
                    logger.error(f"Error generating reversed position: {e}")
                    query.message.reply_text(f"❌ Error generating reversed position: {str(e)}")
        
        # Handle "new image" callback
        elif data.startswith("new_"):
            exchange = data.split("_")[1]
            
            # Show a form for entering new image details
            message_text = (
                f"📝 Generate new {exchange.upper()} PnL image\n\n"
                f"Please send your trade details in this format:\n"
                f"BTCUSDT 20 50000 55000 long\n\n"
                f"Format: <pair> <leverage> <entry> <exit> <type>"
            )
            
            if exchange == "bitget":
                message_text += " [username]"
                
            # Store the exchange in user_data for later use
            context.user_data["awaiting_trade_details"] = exchange
            
            query.message.reply_text(message_text)
    
    def handle_message(self, update: Update, context: CallbackContext):
        """Handle regular text messages"""
        # Check if we're waiting for trade details
        if context.user_data.get("awaiting_trade_details"):
            exchange = context.user_data["awaiting_trade_details"]
            text = update.message.text.strip()
            
            # Try to parse as trade details
            parts = text.split()
            if len(parts) >= 5:
                try:
                    trading_pair = parts[0].upper()
                    leverage = int(parts[1])
                    entry_price = float(parts[2])
                    last_price = float(parts[3])
                    position_type = parts[4].lower()
                    referral_code = parts[5]
                    # Check for BitGet username
                    handle_username = None
                    if exchange == "bitget" and len(parts) >= 7:
                        handle_username = parts[6]
                    
                    # Validate position type
                    if position_type not in ["long", "short"]:
                        update.message.reply_text("Position type must be 'long' or 'short'")
                        return
                    
                    # Clear the awaiting flag
                    del context.user_data["awaiting_trade_details"]
                    
                    # Send status message
                    status_message = update.message.reply_text(
                        f"⏳ Generating {exchange.upper()} PnL image for {trading_pair}... Please wait."
                    )
                    
                    try:
                        # Generate the PnL image
                        image_path = generate_unified_pnl_image(
                            trading_pair=trading_pair,
                            leverage=leverage,
                            entry_price=entry_price,
                            last_price=last_price,
                            referral_code=referral_code,
                            position_type=position_type,
                            exchange=exchange,
                            handle_username=handle_username
                        )
                        
                        # Calculate PnL percentage for the caption
                        is_long = position_type == "long"
                        pnl_percentage = calculate_leveraged_pnl_percentage(
                            entry_price, last_price, leverage, is_long
                        )
                        sign = "+" if pnl_percentage >= 0 else ""
                        
                        # Create a caption
                        caption = f"*{position_type.upper()} {trading_pair} {leverage}x:* {sign}{pnl_percentage:.2f}% PnL"
                        
                        # Add buttons for quick actions
                        keyboard = [
                            [
                                InlineKeyboardButton("🔄 Reverse Position", 
                                                   callback_data=f"reverse_{trading_pair}_{leverage}_{entry_price}_{last_price}_{position_type}_{exchange}")
                            ],
                            [
                                InlineKeyboardButton("📊 New Image", 
                                                   callback_data=f"new_{exchange}")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Send the generated image
                        with open(image_path, 'rb') as img_file:
                            update.message.reply_photo(
                                photo=img_file,
                                caption=caption,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                        
                        # Delete the status message
                        status_message.delete()
                        
                    except Exception as e:
                        logger.error(f"Error generating image: {e}")
                        update.message.reply_text(f"❌ Error generating image: {str(e)}")
                        if status_message:
                            status_message.delete()
                
                except ValueError:
                    update.message.reply_text("❌ Invalid format. Please use numbers for leverage, entry and exit prices.")
                except Exception as e:
                    logger.error(f"Error parsing trade details: {e}")
                    update.message.reply_text(f"❌ Error: {str(e)}")
            else:
                update.message.reply_text(
                    "❌ Invalid format. Please use:\n"
                    "<pair> <leverage> <entry> <exit> <type>\n\n"
                    "Example: BTCUSDT 20 50000 55000 long"
                )
                
        else:
            # Try to interpret common patterns
            text = update.message.text.strip().upper()
            
            # Look for trading pair patterns
            if text.endswith('USDT') and len(text) >= 6:
                keyboard = [
                    [
                        InlineKeyboardButton(f"Generate {text} Long", callback_data=f"pair_{text}_long"),
                        InlineKeyboardButton(f"Generate {text} Short", callback_data=f"pair_{text}_short")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                update.message.reply_text(
                    f"Would you like to generate a PnL image for {text}?",
                    reply_markup=reply_markup
                )
    
    def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors in the dispatcher"""
        logger.error(f"Error: {context.error} - {update}")
        
        # Send a message to the user
        if update and update.effective_message:
            update.effective_message.reply_text(
                "❌ Sorry, an error occurred while processing your request."
            )
    
    def start_polling(self):
        """Start the bot polling"""
        self.updater.start_polling()
        logger.info("Bot started polling")
        
        # Run the bot until the user presses Ctrl-C
        self.updater.idle()
    
    def start_webhook(self, webhook_url, port=8443, cert=None, key=None):
        """Start the bot using webhooks"""
        self.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=self.bot_token,
            webhook_url=f"{webhook_url}/{self.bot_token}",
            cert=cert,
            key=key
        )
        logger.info(f"Bot started webhook on port {port}")
    
    def stop(self):
        """Stop the bot"""
        self.updater.stop()
        logger.info("Bot stopped")


# Run the bot if this file is executed directly
if __name__ == "__main__":
    # Create the bot
    bot = PnLTelegramBot()
    
    print("🤖 Starting PnL Telegram Bot...")
    
    # Start polling
    bot.start_polling()