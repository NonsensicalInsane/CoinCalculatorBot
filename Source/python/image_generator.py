import os
import configparser
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Update this import to use the Source.python prefix if needed
try:
    from image_utils import PnLImageGenerator, reload_config  # Try direct import first
except ImportError:
    # If that fails, try with the Source.python prefix
    try:
        from Source.python.image_utils import PnLImageGenerator, reload_config
    except ImportError:
        logger.error("Failed to import PnLImageGenerator - both direct and Source.python prefixed imports failed")

import shutil
import sys

def find_any_usable_font():
    """Find any usable TrueType font on the system"""
    print("Looking for any usable font...")
    
    # Create fonts directory
    os.makedirs("./assets/fonts", exist_ok=True)
    
    # Try common system font locations
    system_font_paths = [
        # Linux
        "/usr/share/fonts/truetype",
        "/usr/share/fonts/TTF",
        # macOS
        "/Library/Fonts",
        "/System/Library/Fonts",
        # Windows
        "C:\\Windows\\Fonts"
    ]
    
    # Try to find any TTF font
    for font_dir in system_font_paths:
        if os.path.exists(font_dir):
            print(f"Checking system font directory: {font_dir}")
            try:
                # Look for any .ttf file
                for root, dirs, files in os.walk(font_dir):
                    ttf_files = [f for f in files if f.lower().endswith('.ttf')]
                    if ttf_files:
                        # Copy the first found font to our assets/fonts directory
                        source_path = os.path.join(root, ttf_files[0])
                        dest_path = os.path.join("./assets/fonts", "default_font.ttf")
                        shutil.copy2(source_path, dest_path)
                        print(f"Copied system font {ttf_files[0]} to assets/fonts/default_font.ttf")
                        
                        # Update config to use this font
                        config = configparser.ConfigParser()
                        config.read("config.cfg")
                        if config.has_section('FONTS'):
                            config.set('FONTS', 'main_font', "default_font.ttf")
                            config.set('FONTS', 'bold_font', "default_font.ttf")
                            config.set('FONTS', 'regular_font', "default_font.ttf")
                            with open("config.cfg", 'w') as f:
                                config.write(f)
                            print("Updated config.cfg to use default_font.ttf")
                        
                        return True
            except Exception as e:
                print(f"Error while searching for fonts: {e}")
    
    print("No system fonts found.")
    return False

def use_default_font():
    """Update config to use PIL's default font"""
    config = configparser.ConfigParser()
    if os.path.exists("config.cfg"):
        config.read("config.cfg")
        
        if config.has_section('FONTS'):
            # Set font path to current directory
            config.set('FONTS', 'path', '.')
            
            # Create an empty font file as placeholder
            with open("default_font.ttf", 'wb') as f:
                f.write(b'')  # Empty file
            
            # Update font references
            config.set('FONTS', 'main_font', "default_font.ttf")
            config.set('FONTS', 'bold_font', "default_font.ttf")
            config.set('FONTS', 'regular_font', "default_font.ttf")
            
            with open("config.cfg", 'w') as f:
                config.write(f)
            
            print("Updated config to use default font")
    
    return True

# Define a simplified calculation function
def calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long=True):
    """Calculate PnL percentage with leverage"""
    if is_long:
        pnl = (last_price - entry_price) / entry_price * 100 * leverage
    else:
        pnl = (entry_price - last_price) / entry_price * 100 * leverage
    return pnl

def generate_unified_pnl_image(trading_pair, leverage, entry_price, last_price,
                              referral_code, position_type, exchange='binance', output_filename=None, handle_username=None):
    """
    Universal function to generate a PnL visualization image - used by both web interface and Telegram bot
    to ensure consistent output.
    
    Args:
        trading_pair (str): The trading pair (e.g., "BTCUSDT")
        leverage (int): The leverage multiplier
        entry_price (float): The entry price
        last_price (float): The current/last price
        referral_code (str): The referral code
        position_type (str): "Long" or "Short"
        exchange (str): Exchange name to use (e.g., 'binance', 'mexc', 'bitget')
        output_filename (str, optional): Custom filename for the output image
        handle_username (str, optional): BitGet handle username (only used for bitget template)
        
    Returns:
        str: Path to the generated image file
    """
    try:
        # Ensure consistent data types
        if exchange=="binance":
            trading_pair = str(trading_pair).upper() + " Perpetual"
        elif exchange=="mexc":
            trading_pair = str(trading_pair).upper() + " Perpetual"
        elif exchange=="bitget":
            trading_pair = str(trading_pair).upper()
        leverage = int(leverage)
        entry_price = float(entry_price)
        last_price = float(last_price)
        referral_code = str(referral_code)
        
        # Normalize position_type capitalization
        if isinstance(position_type, str):
            if position_type.lower() == "long":
                position_type = "Long"
                is_long = True
            elif position_type.lower() == "short":
                position_type = "Short"
                is_long = False
            else:
                raise ValueError(f"Position type must be 'Long' or 'Short', got '{position_type}'")
        else:
            raise ValueError(f"Position type must be a string, got {type(position_type)}")
        
        # DIRECT CONFIG LOADING - ALWAYS USE EXCHANGE-SPECIFIC CONFIG
        exchange_config_path = f'config_{exchange}.cfg'
        logger.info(f"Exchange selected: {exchange}, using config: {exchange_config_path}")
        
        if not os.path.exists(exchange_config_path):
            raise ValueError(f"Exchange config file not found: {exchange_config_path}")
        
        # Force reload the config every time
        config = reload_config(exchange_config_path)
        
        if not config:
            raise ValueError(f"Failed to load config from {exchange_config_path}")
        
        logger.info(f"Successfully loaded exchange config with sections: {config.sections()}")
        
        # Calculate PnL percentage
        pnl_percentage = calculate_leveraged_pnl_percentage(
            entry_price, last_price, leverage, is_long
        )
        
        # Create image generator with ONLY the exchange-specific config
        image_generator = PnLImageGenerator(config)
        
        # Generate the image
        # Format the shared date according to exchange requirements
        shared_date = None
        if exchange == 'mexc':
            # Format: 2025-03-14 21:41:30
            shared_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif exchange == 'bitget':
            # Format: 2025-03-16 21:18(UTC+3)
            # Get UTC offset
            utc_offset = datetime.now().astimezone().strftime('%z')
            utc_hour = int(utc_offset[1:3])
            utc_sign = '+' if utc_offset[0] == '+' else '-'
            shared_date = datetime.now().strftime("%Y-%m-%d %H:%M") + f"(UTC{utc_sign}{utc_hour})"
        
        output_path = image_generator.generate_pnl_image(
            trading_pair, leverage, entry_price, last_price,
            referral_code, pnl_percentage, is_long, 
            handle_username=handle_username if exchange == 'bitget' else None,
            shared_date=shared_date,
            handle_username_at=(handle_username is not None) if exchange == 'bitget' else None,
            exchange=exchange
        )
        
        logger.info(f"Successfully generated PnL image: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating unified image: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error image with detailed error message
        img = Image.new('RGB', (800, 400), color=(50, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Error: {str(e)}", fill="white")
        
        output_path = os.path.join('output', f"error_{exchange}.png")
        if not os.path.exists('output'):
            os.makedirs('output')
        img.save(output_path)
        return output_path

def generate_template_image(template_name, trading_pair, leverage, entry_price, last_price,
                          referral_code, position_type, exchange, **kwargs):
    """
    Generate an image using the specified template.
    
    Args:
        template_name (str): The name of the template to use (e.g., 'binance', 'mexc', 'bitget', 'liquidity')
        trading_pair (str): The trading pair (e.g., "BTCUSDT")
        leverage (int): The leverage multiplier
        entry_price (float): The entry price
        last_price (float): The current/last price
        referral_code (str): The referral code
        position_type (str): "Long" or "Short"
        **kwargs: Additional parameters for specific templates
    
    Returns:
        str: Path to the generated image
    """
    try:
        # DIRECT CONFIG LOADING - ALWAYS USE TEMPLATE-SPECIFIC CONFIG
        template_config_path = f'config_{template_name}.cfg'
        print(f"\n===== DIRECT TEMPLATE CONFIG LOADING =====")
        print(f"Template selected: {template_name}")
        print(f"Using ONLY config file: {template_config_path}")
        
        if not os.path.exists(template_config_path):
            raise ValueError(f"Template config file not found: {template_config_path}")
        
        # Create a new ConfigParser object ONLY for this config file
        config = configparser.ConfigParser()
        # Read ONLY the template-specific config
        config.read(template_config_path)
        
        print(f"Successfully loaded template config with sections: {config.sections()}")
        print(f"===== END DIRECT TEMPLATE CONFIG LOADING =====\n")
        
        # Calculate PnL percentage
        is_long = position_type.lower() == "long"
        pnl_percentage = calculate_leveraged_pnl_percentage(
            entry_price, last_price, leverage, is_long
        )
        
        # For liquidity template, use the extended generator
        if template_name.lower() == 'liquidity':
            from liquidity_generator import LiquidityImageGenerator
            
            # Create liquidity image generator
            image_generator = LiquidityImageGenerator(config)
            
            # Get liquidity specific parameters with defaults
            unrealized_pnl = kwargs.get('unrealized_pnl', 0.0)
            roi = kwargs.get('roi', 0.0)
            size = kwargs.get('size', 0.0)
            margin = kwargs.get('margin', 0.0)
            margin_ratio = kwargs.get('margin_ratio', 0.0)
            mark_price = kwargs.get('mark_price', last_price)
            positions = kwargs.get('positions', 1)
            open_orders = kwargs.get('open_orders', 0)
            
            # Generate image with liquidity details
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"liquidity_{trading_pair}_{timestamp}.png"
            
            img = image_generator.generate_liquidity_image(
                trading_pair, 
                position_type,
                pnl_percentage,
                unrealized_pnl,
                roi,
                size,
                margin,
                margin_ratio,
                entry_price,
                mark_price,
                positions,
                open_orders,
                referral_code,
                output_filename
            )
        else:
            # For standard templates, create an image generator with the specific config
            image_generator = PnLImageGenerator(config)
            
            # Generate the standard PnL image
            img = image_generator.generate_pnl_image(
                trading_pair, leverage, entry_price, last_price,
                referral_code, pnl_percentage, is_long, 
                exchange=template_name  # Pass template_name as the exchange parameter
            )
            
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"pnl_{template_name}_{trading_pair}_{timestamp}.png"
            
            output_dir = config.get('OUTPUT', 'dir')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            output_path = os.path.join(output_dir, output_filename)
            img.save(output_path, format=config.get('OUTPUT', 'format', fallback='PNG'))
        
        return output_path
        
    except Exception as e:
        print(f"Error generating image with template {template_name}: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error image
        img = Image.new('RGB', (800, 400), color=(50, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Error: {str(e)}", fill="white")
        
        output_path = os.path.join('output', f"error_{template_name}.png")
        if not os.path.exists('output'):
            os.makedirs('output')
        img.save(output_path)
        return output_path 