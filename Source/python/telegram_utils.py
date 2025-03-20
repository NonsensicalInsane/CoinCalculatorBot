import os
import configparser
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_to_telegram(image_path=None, message=None, caption=None):
    """
    Send an image or message to Telegram.
    
    Args:
        image_path (str, optional): Path to image file
        message (str, optional): Text message to send (if no image)
        caption (str, optional): Caption for image (if sending image)
        
    Returns:
        tuple: (success, response_text)
    """
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.cfg')
    
    if not config.has_section('TELEGRAM'):
        return False, "TELEGRAM section not found in config.cfg"
        
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')
    
    # Validate config
    if bot_token == 'YOUR_BOT_TOKEN_HERE' or chat_id == 'YOUR_CHAT_ID_HERE':
        return False, "Telegram bot token or chat ID not configured properly"
    
    # Prepare for debugging
    debug_info = f"Using bot token: {bot_token[:5]}...{bot_token[-5:]} and chat ID: {chat_id}"
    logger.info(debug_info)
    
    # Sending image
    if image_path:
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}"
            
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        data = {'chat_id': chat_id}
        
        if caption:
            data['caption'] = caption
            
        files = {'photo': open(image_path, 'rb')}
        
        try:
            response = requests.post(url, data=data, files=files)
            files['photo'].close()
            
            if response.status_code == 200:
                return True, f"Image successfully sent to chat {chat_id}"
            else:
                return False, f"Failed to send image. Status: {response.status_code}, Response: {response.text}"
        except Exception as e:
            return False, f"Error sending image: {e}"
        finally:
            if 'files' in locals() and 'photo' in files:
                files['photo'].close()
    
    # Sending message
    elif message:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                return True, f"Message successfully sent to chat {chat_id}"
            else:
                return False, f"Failed to send message. Status: {response.status_code}, Response: {response.text}"
        except Exception as e:
            return False, f"Error sending message: {e}"
    
    else:
        return False, "No image or message provided"

def test_telegram_connection():
    """Test the Telegram bot connection with a simple message"""
    success, response = send_to_telegram(message="🔄 Testing Telegram connection...")
    return success, response

def get_chat_info():
    """Get information about the configured chat"""
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.cfg')
    
    if not config.has_section('TELEGRAM'):
        return False, "TELEGRAM section not found in config.cfg"
        
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')
    
    # Validate config
    if bot_token == 'YOUR_BOT_TOKEN_HERE' or chat_id == 'YOUR_CHAT_ID_HERE':
        return False, "Telegram bot token or chat ID not configured properly"
    
    url = f"https://api.telegram.org/bot{bot_token}/getChat"
    data = {'chat_id': chat_id}
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return True, response.json().get('result', {})
        else:
            return False, f"Failed to get chat info. Status: {response.status_code}, Response: {response.text}"
    except Exception as e:
        return False, f"Error getting chat info: {e}"

if __name__ == "__main__":
    # Simple command-line interface for testing
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Send to Telegram')
    parser.add_argument('--image', type=str, help='Path to image file')
    parser.add_argument('--message', type=str, help='Text message to send')
    parser.add_argument('--caption', type=str, help='Caption for image')
    parser.add_argument('--test', action='store_true', help='Run a connection test')
    parser.add_argument('--info', action='store_true', help='Get info about the configured chat')
    
    args = parser.parse_args()
    
    if args.test:
        success, response = test_telegram_connection()
        print(f"Test {'successful' if success else 'failed'}: {response}")
        sys.exit(0 if success else 1)
    
    if args.info:
        success, info = get_chat_info()
        if success:
            print("Chat info:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print(f"Failed to get chat info: {info}")
        sys.exit(0 if success else 1)
    
    if not args.image and not args.message:
        parser.print_help()
        print("\nError: Either --image or --message must be provided")
        sys.exit(1)
    
    success, response = send_to_telegram(args.image, args.message, args.caption)
    print(response)
    sys.exit(0 if success else 1) 