"""
Core functionality for the PnL Calculator Bot
This module provides essential functions for the webhook handler
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Make sure the Source directory is in the path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import necessary modules
from Source.python.image_generator import generate_unified_pnl_image
from Source.python.env_config import load_environment, get_environment_variable

def generate_pnl_image(trading_pair, leverage, entry_price, last_price, 
                       referral_code, position_type, exchange='binance', 
                       output_filename=None, handle_username=None):
    """
    Wrapper function for generate_unified_pnl_image to ensure consistent API
    for webhook handler
    
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
        # Ensure environment is loaded
        load_environment()
        
        # Generate the image
        image_path = generate_unified_pnl_image(
            trading_pair=trading_pair,
            leverage=leverage,
            entry_price=entry_price,
            last_price=last_price,
            referral_code=referral_code,
            position_type=position_type,
            exchange=exchange,
            output_filename=output_filename,
            handle_username=handle_username
        )
        
        return image_path
    except Exception as e:
        logger.error(f"Error generating PnL image: {e}")
        raise 