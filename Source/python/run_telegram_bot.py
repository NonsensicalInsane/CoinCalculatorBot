"""
Launcher script for the PnL Telegram Bot
"""

import os
import sys
import logging
import configparser

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add parent directory to path to help with imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Try to import from the corrected modules
try:
    from Source.python.telegram_bot import PnLTelegramBot
    from Source.python.env_config import load_environment, get_environment_variable
except ImportError:
    try:
        from telegram_bot import PnLTelegramBot
        try:
            from env_config import load_environment, get_environment_variable
        except ImportError:
            load_environment = lambda: None
            get_environment_variable = lambda section, key, default=None: None
    except ImportError as e:
        logger.error(f"Failed to import PnLTelegramBot: {e}")
        logger.error("Make sure all required modules are available.")
        sys.exit(1)

def check_telegram_config():
    """Check if Telegram configuration exists and is valid in environment variables"""
    # Load environment variables first
    load_environment()
    
    # Check environment variables
    bot_token = get_environment_variable('TELEGRAM', 'bot_token')
    chat_id = get_environment_variable('TELEGRAM', 'chat_id')
    
    # If both are present in environment variables, we're good to go
    if bot_token and chat_id and bot_token != 'YOUR_BOT_TOKEN_HERE' and chat_id != 'YOUR_CHAT_ID_HERE':
        print("✅ Telegram configuration found in environment variables.")
        return True
    
    # Fall back to checking the config file (for backward compatibility)
    config = configparser.ConfigParser()
    
    # Check if config file exists
    if not os.path.exists('config.cfg'):
        print("❌ Config file not found and environment variables are missing.")
        print("Creating sample configuration...")
        
        # Create a sample config file
        config.add_section('TELEGRAM')
        config.set('TELEGRAM', 'bot_token', 'YOUR_BOT_TOKEN_HERE')
        config.set('TELEGRAM', 'chat_id', 'YOUR_CHAT_ID_HERE')
        config.set('TELEGRAM', 'referral_code', '48604752')
        
        with open('config.cfg', 'w') as f:
            config.write(f)
        
        print("\n⚠️ Please set your Telegram bot token and chat ID either:")
        print("1. In your .env file as TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (recommended)")
        print("2. In config.cfg in the TELEGRAM section")
        return False
    
    # Load config
    config.read('config.cfg')
    
    # Check if TELEGRAM section exists
    if not config.has_section('TELEGRAM'):
        print("❌ No TELEGRAM section in config file and environment variables are missing.")
        print("Adding TELEGRAM section to config.cfg...")
        
        config.add_section('TELEGRAM')
        config.set('TELEGRAM', 'bot_token', 'YOUR_BOT_TOKEN_HERE')
        config.set('TELEGRAM', 'chat_id', 'YOUR_CHAT_ID_HERE')
        config.set('TELEGRAM', 'referral_code', '48604752')
        
        with open('config.cfg', 'w') as f:
            config.write(f)
        
        print("\n⚠️ Please set your Telegram bot token and chat ID either:")
        print("1. In your .env file as TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (recommended)")
        print("2. In config.cfg in the TELEGRAM section")
        return False
    
    # Check for placeholder values in config
    cfg_bot_token = config.get('TELEGRAM', 'bot_token', fallback='')
    cfg_chat_id = config.get('TELEGRAM', 'chat_id', fallback='')
    
    if cfg_bot_token == 'YOUR_BOT_TOKEN_HERE' or cfg_chat_id == 'YOUR_CHAT_ID_HERE':
        print("⚠️ Telegram configuration contains placeholder values.")
        print("Please set your configuration with REAL values using one of these methods:")
        print("1. In your .env file (recommended):")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("   TELEGRAM_CHAT_ID=your_chat_id_here")
        print("2. In config.cfg:")
        if cfg_bot_token == 'YOUR_BOT_TOKEN_HERE':
            print("   bot_token: Get this from @BotFather on Telegram")
        if cfg_chat_id == 'YOUR_CHAT_ID_HERE':
            print("   chat_id: Start a chat with your bot or use @userinfobot")
        return False
        
    return True

if __name__ == "__main__":
    print("🚀 Launching PnL Telegram Bot")
    
    # Check configuration first
    if not check_telegram_config():
        print("\n⚠️ Please update your configuration and try again.")
        exit(1)
    
    try:
        # Create and start the bot
        bot = PnLTelegramBot()
        print("✅ Bot initialized successfully")
        print("🤖 Starting bot - press Ctrl+C to stop")
        bot.start_polling()
    except KeyboardInterrupt:
        print("\n✋ Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        
        # Offer some common troubleshooting steps
        if "Connection refused" in str(e):
            print("\nTroubleshooting:")
            print("- Check your internet connection")
            print("- Make sure Telegram API is accessible from your network")
        elif "Unauthorized" in str(e) or "Not Found" in str(e):
            print("\nTroubleshooting:")
            print("- Your bot token may be invalid. Double-check it from @BotFather")
            print("- If you just created the bot, wait a few minutes and try again")
        elif "chat not found" in str(e).lower():
            print("\nTroubleshooting:")
            print("- Make sure the chat_id is correct")
            print("- Your bot must be a member of the chat/group specified") 