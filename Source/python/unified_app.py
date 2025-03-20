"""
Unified application that combines web scraping from web_interface.py 
and image generation from core.py
"""

import os
import sys
import configparser
from datetime import datetime

# Ensure Source.python is in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from both modules
from Source.python.image_generator import generate_unified_pnl_image, calculate_leveraged_pnl_percentage
from Source.python.env_config import load_environment, get_environment_variable

# Import web scraping functionality 
try:
    from Source.python.binance_scraper import get_available_symbols as scraper_get_symbols
    from Source.python.binance_scraper import get_max_leverage, update_symbol_leverage
    SCRAPER_AVAILABLE = True
    print("Successfully imported Binance Scraper")
except ImportError as e:
    print(f"Warning: Binance Scraper not available: {e}")
    SCRAPER_AVAILABLE = False

try:
    from Source.python.binance_api import get_available_symbols, get_current_price
    BINANCE_API_AVAILABLE = True
    print("Successfully imported Binance API")
except ImportError as e:
    print(f"Warning: Binance API not available: {e}")
    BINANCE_API_AVAILABLE = False

# Load environment variables
load_environment()

def get_symbols():
    """Get available trading symbols, prioritizing scraper"""
    if SCRAPER_AVAILABLE:
        try:
            symbols = scraper_get_symbols()
            if symbols:
                print(f"Using {len(symbols)} symbols from scraper")
                return sorted(symbols)
        except Exception as e:
            print(f"Scraper error: {e}")
    
    if BINANCE_API_AVAILABLE:
        try:
            symbols = get_available_symbols()
            print(f"Using {len(symbols)} symbols from API")
            return symbols
        except Exception as e:
            print(f"API error: {e}")
    
    # Default fallback
    print("Using default symbols list")
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT"]

def get_max_leverage_for_symbol(symbol):
    """Get max leverage for a symbol using best available method"""
    if SCRAPER_AVAILABLE:
        try:
            # Always update the symbol leverage data first to ensure it's fresh
            update_symbol_leverage(symbol)
            leverage = get_max_leverage(symbol)
            print(f"Max leverage for {symbol} from scraper: {leverage}x")
            return leverage
        except Exception as e:
            print(f"Scraper error for leverage: {e}")
    
    # Fall back to known common values
    common_leverages = {
        "BTCUSDT": 125, "ETHUSDT": 100, "BNBUSDT": 75, 
        "ADAUSDT": 75, "SOLUSDT": 50, "XRPUSDT": 75, 
        "DOGEUSDT": 75, "LINKUSDT": 75
    }
    
    if symbol in common_leverages:
        print(f"Using known leverage for {symbol}: {common_leverages[symbol]}x")
        return common_leverages[symbol]
    
    print(f"Using default leverage for {symbol}: 20x")
    return 20  # Default value

def update_symbol_data(symbol):
    """Get current price and max leverage for the symbol"""
    result = {"current_price": None, "max_leverage": 20}
    
    # Get max leverage
    result["max_leverage"] = get_max_leverage_for_symbol(symbol)
    
    # Try to get current price
    if BINANCE_API_AVAILABLE:
        try:
            price = get_current_price(symbol)
            if price:
                result["current_price"] = price
                print(f"Current price for {symbol}: ${price}")
        except Exception as e:
            print(f"API error getting price: {e}")
    
    return result

def generate_image(trading_pair, leverage, entry_price, last_price, 
                  referral_code, position_type, exchange, handle_username=None):
    """
    Generate PnL image using core.py's functionality
    
    Args:
        trading_pair: Trading pair (e.g., "BTCUSDT")
        leverage: Leverage value
        entry_price: Entry price
        last_price: Last price
        referral_code: Referral code
        position_type: "Long" or "Short"
        exchange: Exchange template (e.g., "binance", "mexc", "bitget") 
        handle_username: Username for BitGet template
        
    Returns:
        str: Path to generated image
    """
    try:
        print(f"Generating {exchange} PnL image for {trading_pair}...")
        
        # Ensure correct types and formats
        trading_pair = str(trading_pair).upper()
        leverage = int(leverage)
        entry_price = float(entry_price)
        last_price = float(last_price)
        
        # Make sure position_type is properly capitalized
        if isinstance(position_type, str):
            if position_type.lower() == "long":
                position_type = "Long"
            elif position_type.lower() == "short":
                position_type = "Short"
            else:
                raise ValueError(f"Position type must be 'Long' or 'Short', got '{position_type}'")
        else:
            raise ValueError(f"Position type must be a string, got {type(position_type)}")
        
        # Generate image using unified_pnl_image function from image_generator
        img_path = generate_unified_pnl_image(
            trading_pair=trading_pair,
            leverage=leverage,
            entry_price=entry_price,
            last_price=last_price,
            position_type=position_type,
            exchange=exchange,
            referral_code=referral_code,
            handle_username=handle_username if exchange == "bitget" else None
        )
        
        # Calculate PnL for status message
        is_long = position_type == "Long"
        pnl = calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long)
        sign = "+" if pnl >= 0 else ""
        status_message = f"{sign}{pnl:.2f}% PnL"
        
        print(f"Successfully generated image: {img_path}")
        return img_path, status_message
    except Exception as e:
        print(f"Error generating image: {e}")
        import traceback
        traceback.print_exc()
        return None, f"Error: {str(e)}"

def send_to_telegram(image_path):
    """Send image to Telegram using environment config"""
    if not image_path or not os.path.exists(image_path):
        return "No image to send!"
    
    try:
        # Try to import and use telegram_utils
        from Source.python.telegram_utils import send_to_telegram
        success, message = send_to_telegram(image_path=image_path)
        
        if success:
            return f"✅ Success! {message}"
        else:
            return f"❌ Failed: {message}"
    except ImportError:
        # Fall back to direct implementation
        try:
            # Load configuration
            bot_token = get_environment_variable('TELEGRAM', 'bot_token')
            chat_id = get_environment_variable('TELEGRAM', 'chat_id')
            
            if not bot_token or not chat_id:
                return "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file."
            
            import requests
            
            # Prepare request data
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            data = {'chat_id': chat_id}
            files = {'photo': open(image_path, 'rb')}
            
            # Send request
            print(f"Sending image to Telegram chat {chat_id}...")
            response = requests.post(url, data=data, files=files)
            
            # Check response
            if response.status_code == 200:
                return f"✅ Image successfully sent to Telegram chat {chat_id}"
            else:
                return f"❌ Failed to send image. Status code: {response.status_code}"
                
        except Exception as e:
            return f"❌ Error sending image to Telegram: {e}"
        finally:
            # Make sure to close the file if it was opened
            if 'files' in locals() and 'photo' in files:
                files['photo'].close()

# For Gradio web interface, import these additional dependencies
def create_web_interface():
    """Create a Gradio web interface for the PnL generator"""
    import gradio as gr
    
    # Get all available trading pairs
    all_symbols = get_symbols()
    print(f"Loaded {len(all_symbols)} trading pairs for dropdown")
    
    # Get available exchange templates
    exchange_templates = ["binance", "mexc", "bitget"]
    
    # Try to get from config
    try:
        config = configparser.ConfigParser()
        if os.path.exists('config.cfg'):
            config.read('config.cfg')
            if config.has_section('EXCHANGE_TEMPLATES') and config.has_option('EXCHANGE_TEMPLATES', 'templates'):
                templates_str = config.get('EXCHANGE_TEMPLATES', 'templates')
                exchange_templates = [t.strip() for t in templates_str.split(',') if t.strip()]
    except:
        pass
    
    def on_trading_pair_change(trading_pair):
        """Handler for when trading pair changes"""
        if not trading_pair:
            return gr.update(maximum=20, value=20)
            
        # Ensure coin has USDT suffix
        if not trading_pair.endswith('USDT'):
            trading_pair = f"{trading_pair}USDT"
        
        try:
            # Force update of leverage data from scraper
            if SCRAPER_AVAILABLE:
                try:
                    print(f"Updating leverage data for {trading_pair}...")
                    update_symbol_leverage(trading_pair)
                except Exception as e:
                    print(f"Error updating symbol leverage: {e}")
            
            # Get max leverage for this symbol
            max_lev = get_max_leverage_for_symbol(trading_pair)
            
            # Return the updated maximum and value for the leverage slider
            return gr.update(maximum=max_lev, value=min(max_lev, 20))
        except Exception as e:
            print(f"Error updating leverage for {trading_pair}: {e}")
            return gr.update(maximum=20, value=20)  # Default value if there's an error
    
    with gr.Blocks(title="PnL Image Generator") as iface:
        gr.Markdown("# Cryptocurrency PnL Image Generator")
        gr.Markdown("Generate custom PnL (Profit and Loss) visualization images")
        
        # Status message for updates
        update_status = gr.Textbox(label="Status", value="Ready", visible=True)
        
        with gr.Tab("Standard PnL"):
            with gr.Row():
                with gr.Column(scale=2):
                    exchange = gr.Dropdown(
                        label="Exchange Template", 
                        choices=exchange_templates,
                        value=exchange_templates[0]
                    )
                    
                    trading_pair = gr.Dropdown(
                        label="Trading Pair", 
                        choices=all_symbols, 
                        value="BTCUSDT"
                    )
                    
                    leverage = gr.Slider(minimum=1, maximum=125, value=20, step=1, label="Leverage")
                    entry_price = gr.Number(label="Entry Price", value=50000)
                    last_price = gr.Number(label="Last Price", value=55000)
                    referral_code = gr.Textbox(label="Referral Code", value="48604752")
                    position_type = gr.Radio(["Long", "Short"], label="Position Type", value="Long")
                    
                    # BitGet handle username field
                    handle_username = gr.Textbox(
                        label="BitGet Handle (only for BitGet template)", 
                        value="BGUSER-M2TRXC4", 
                        visible=False
                    )
                    
                    with gr.Row():
                        generate_btn = gr.Button("Generate PnL Image", variant="primary")
                        telegram_btn = gr.Button("Send to Telegram", variant="secondary")
                
                with gr.Column(scale=3):
                    output_image = gr.Image(type="filepath", label="Generated PnL Image")
            
            # Show/hide BitGet username field based on exchange selection
            def update_visibility(exchange_value):
                return gr.update(visible=exchange_value == "bitget")
                
            exchange.change(
                update_visibility,
                inputs=[exchange],
                outputs=[handle_username]
            )
            
            # Update leverage based on trading pair
            trading_pair.change(
                on_trading_pair_change,
                inputs=[trading_pair],
                outputs=[leverage]
            )
            
            # After selecting a pair, update the price if possible
            def update_price_info(trading_pair):
                if not trading_pair:
                    return gr.update(), gr.update()
                
                # Use the API to get current price if available
                if BINANCE_API_AVAILABLE:
                    try:
                        current_price = get_current_price(trading_pair)
                        if current_price:
                            return gr.update(value=current_price), gr.update(value=f"Updated price for {trading_pair}: ${current_price}")
                    except Exception as e:
                        return gr.update(), gr.update(value=f"Error getting price: {e}")
                
                return gr.update(), gr.update()
            
            trading_pair.change(
                update_price_info,
                inputs=[trading_pair],
                outputs=[last_price, update_status]
            )
            
            # Generate image button functionality
            generate_btn.click(
                fn=generate_image,
                inputs=[
                    trading_pair,
                    leverage,
                    entry_price,
                    last_price,
                    referral_code,
                    position_type,
                    exchange,
                    handle_username
                ],
                outputs=[
                    output_image,
                    update_status
                ]
            )
            
            # Send to Telegram button
            def send_selected_image(image_path):
                if image_path:
                    return send_to_telegram(image_path)
                return "No image selected!"
            
            telegram_btn.click(
                fn=send_selected_image,
                inputs=[output_image],
                outputs=[update_status]
            )
            
            # Add example inputs
            gr.Examples(
                examples=[
                    ["BTCUSDT", 10, 50000, 55000, "48604752", "Long", "binance"],
                    ["ETHUSDT", 15, 3000, 2800, "48604752", "Short", "mexc"],
                    ["SOLUSDT", 20, 100, 120, "48604752", "Long", "bitget", "BGUSER-M2TRXC4"]
                ],
                inputs=[trading_pair, leverage, entry_price, last_price, referral_code, position_type, exchange, handle_username],
                outputs=output_image,
                fn=generate_image
            )
    
    return iface

# Run as main script
if __name__ == "__main__":
    print("Starting Unified PnL Image Generator...")
    
    # Create directories if needed
    os.makedirs("./assets/fonts", exist_ok=True)
    os.makedirs("./assets/templates", exist_ok=True)
    os.makedirs("./output", exist_ok=True)
    
    # Either run in web interface mode
    try:
        import gradio as gr
        iface = create_web_interface()
        iface.launch(share=True)
    except ImportError:
        print("Gradio not installed. Running in CLI mode.")
        
        # Or run in command-line mode if gradio not available
        import argparse
        
        parser = argparse.ArgumentParser(description='Unified PnL Image Generator')
        parser.add_argument('--pair', type=str, required=True, help='Trading pair (e.g., BTCUSDT)')
        parser.add_argument('--leverage', type=int, required=True, help='Leverage multiplier')
        parser.add_argument('--entry', type=float, required=True, help='Entry price')
        parser.add_argument('--last', type=float, required=True, help='Last/current price')
        parser.add_argument('--position', type=str, default='Long', choices=['Long', 'Short'], help='Position type')
        parser.add_argument('--exchange', type=str, default='binance', choices=['binance', 'mexc', 'bitget'], help='Exchange template')
        parser.add_argument('--referral', type=str, default='48604752', help='Referral code')
        parser.add_argument('--username', type=str, help='BitGet username (only for BitGet template)')
        parser.add_argument('--telegram', action='store_true', help='Send to Telegram after generating')
        
        args = parser.parse_args()
        
        # Generate the image
        img_path, status = generate_image(
            args.pair, args.leverage, args.entry, args.last, 
            args.referral, args.position, args.exchange,
            args.username if args.exchange == 'bitget' else None
        )
        
        print(status)
        print(f"Image path: {img_path}")
        
        # Send to Telegram if requested
        if args.telegram and img_path:
            result = send_to_telegram(img_path)
            print(result) 