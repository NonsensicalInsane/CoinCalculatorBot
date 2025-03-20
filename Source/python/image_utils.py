"""
Utility classes and functions for image generation
"""

import os
import configparser
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reload_config(config_path):
    """Force reload a config file to ensure we have the latest version"""
    print(f"🔄 Reloading config from: {config_path}")
    config = configparser.ConfigParser()
    
    # Critical fix: Add case-sensitive parsing to handle font filenames properly
    config.optionxform = str
    
    if os.path.exists(config_path):
        try:
            config.read(config_path)
            print(f"✅ Config reloaded with sections: {config.sections()}")
            return config
        except Exception as e:
            print(f"❌ Error reading config file: {e}")
            return None
    else:
        print(f"❌ Config file not found: {config_path}")
        return None

class PnLImageGenerator:
    """Base class for generating PnL visualization images"""
    
    def __init__(self, config_path_or_object=None):
        """
        Initialize the PnL Image Generator.
        
        Args:
            config_path_or_object: Either a path to config file (str) or a ConfigParser object
        """
        # If we already have a ConfigParser object, use it
        if isinstance(config_path_or_object, configparser.ConfigParser):
            self.config = config_path_or_object
            print(f"📋 Using provided ConfigParser object with sections: {self.config.sections()}")
        else:
            # Otherwise, treat it as a path and create a new ConfigParser
            self.config = configparser.ConfigParser()
            # Critical fix: Add case-sensitive parsing to handle font filenames properly
            self.config.optionxform = str
            
            if config_path_or_object and os.path.exists(config_path_or_object):
                try:
                    self.config.read(config_path_or_object)
                    print(f"📋 Loaded config from {config_path_or_object} with sections: {self.config.sections()}")
                except Exception as e:
                    logger.error(f"Error reading config file: {e}")
            else:
                logger.warning(f"Config file not found: {config_path_or_object}")
                
        # Load font configuration
        self.fonts = {}
        self.load_fonts()
    
    def load_fonts(self):
        """Load fonts based on updated configuration"""
        try:
            if not self.config.has_section('FONTS'):
                logger.warning("No FONTS section in config")
                return
                
            font_path = self.config.get('FONTS', 'path', fallback='./assets/fonts')
            logger.info(f"Loading fonts from path: {font_path}")
            
            # Ensure font directory exists
            os.makedirs(font_path, exist_ok=True)
            
            # Load primary font definitions
            primary_font_types = [
                'main_font', 'bold_font', 'regular_font', 'medium_font', 
                'semibold_font', 'light_font', 'extrabold_font', 'heavy_font'
            ]
            
            # Load all available primary fonts
            for font_type in primary_font_types:
                if self.config.has_option('FONTS', font_type):
                    font_file = self.config.get('FONTS', font_type)
                    full_path = os.path.join(font_path, font_file)
                    
                    # Store the font path for later use with specific sizes
                    self.fonts[font_type + '_path'] = full_path
                    logger.info(f"Registered {font_type} path: {full_path}")
                    
                    # Check if the font file exists
                    if not os.path.exists(full_path):
                        logger.warning(f"Font file does not exist: {full_path}")
            
            # Now load all element-specific fonts with their sizes
            element_fonts = [
                'position_type', 'leverage', 'trading_pair', 'pnl_percentage',
                'entry_price_label', 'entry_price_value', 'last_price_label', 'last_price_value',
                'referral_code_label', 'referral_code_value', 'app_link',
                'shared_date', 'handle_username', 'handle_username_at', 'referral_message', 'signup_text'
            ]
            
            for element in element_fonts:
                # Get the font reference and size
                logger.info(f"Attempting to load font for element: {element}")
                if not (self.config.has_option('FONTS', f'{element}_font') and 
                        self.config.has_option('FONTS', f'{element}_size')):
                    logger.warning(f"Missing font configuration for {element}, either {element}_font or {element}_size not found")
                    continue
                    
                font_ref = self.config.get('FONTS', f'{element}_font')
                size = int(self.config.get('FONTS', f'{element}_size'))
                logger.info(f"For {element}: font_ref={font_ref}, size={size}")
                
                # Check if the font_ref is a reference to another font
                if font_ref in primary_font_types and font_ref + '_path' in self.fonts:
                    font_path = self.fonts[font_ref + '_path']
                    try:
                        font = self.load_font_safely(font_path, size)
                        self.fonts[element] = font
                        logger.info(f"Loaded {element} font: {font_path} at size {size}")
                    except Exception as e:
                        logger.error(f"Failed to load font {font_path} for {element}: {e}")
                else:
                    # It might be a direct font file path
                    try:
                        full_path = os.path.join(font_path, font_ref)
                        logger.info(f"Trying direct font path: {full_path}")
                        if not os.path.exists(full_path):
                            logger.warning(f"Font file does not exist: {full_path}")
                        font = self.load_font_safely(full_path, size)
                        self.fonts[element] = font
                        logger.info(f"Loaded {element} font (direct): {full_path} at size {size}")
                    except Exception as e:
                        logger.error(f"Failed to load direct font {font_ref} for {element}: {e}")
            
            logger.info(f"Completed font loading. Loaded fonts: {list(self.fonts.keys())}")
                    
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_color(self, color_str):
        """Parse color string in different formats (hex, rgb, etc)"""
        try:
            if color_str.startswith('#'):
                # Hex color
                return color_str
            elif color_str.lower().startswith('rgb'):
                # RGB color format - extract the values
                # Handle both comma and space delimited formats
                rgb_values = color_str.strip().lower().replace('rgb(', '').replace(')', '')
                if ',' in rgb_values:
                    r, g, b = [int(x.strip()) for x in rgb_values.split(',')]
                else:
                    # Handle space-delimited format
                    r, g, b = [int(x.strip()) for x in rgb_values.split()]
                return (r, g, b)
            else:
                # Default to white if format is unknown
                logger.warning(f"Unknown color format: {color_str}")
                return (255, 255, 255)
        except Exception as e:
            logger.warning(f"Could not parse color: {color_str} - Error: {e}")
            return (255, 255, 255)  # Default to white
    
    def _get_color(self, color_key, is_profit=None, is_long=None):
        """Get color from config based on key and context"""
        try:
            # Special handling for position type colors based on long/short
            if color_key == 'position_type':
                if is_long:
                    color_key = 'position_type_long_color'
                else:
                    color_key = 'position_type_short_color'
            
            # Special handling for PnL colors based on profit/loss
            elif color_key == 'pnl_percentage':
                if is_profit:
                    color_key = 'profit_color'
                else:
                    color_key = 'loss_color'
            
            # Get the color from config
            if self.config.has_section('COLORS') and self.config.has_option('COLORS', color_key):
                color_str = self.config.get('COLORS', color_key)
                return self._parse_color(color_str)
            else:
                # Default colors if not specified
                default_colors = {
                    'position_type_long_color': (0, 204, 170),  # Teal
                    'position_type_short_color': (235, 87, 87),  # Red
                    'profit_color': (0, 204, 170),  # Teal
                    'loss_color': (235, 87, 87),  # Red
                    'text_primary': (255, 255, 255),  # White
                    'text_secondary': (180, 180, 180),  # Light gray
                }
                
                if color_key in default_colors:
                    return default_colors[color_key]
                else:
                    logger.warning(f"No color found for {color_key}, using white")
                    return (255, 255, 255)  # Default to white
        except Exception as e:
            logger.error(f"Error getting color {color_key}: {e}")
            return (255, 255, 255)  # Default to white

    def _select_background(self, pnl_percentage):
        """Select background image based on PnL percentage"""
        try:
            if not self.config.has_section('BACKGROUNDS'):
                logger.warning("No BACKGROUNDS section in config")
                return None
                
            # Get the background path
            bg_path = self.config.get('BACKGROUNDS', 'path')
            
            # Determine background based on PnL percentage
            if pnl_percentage >= 50:
                bg_file = self.config.get('BACKGROUNDS', 'high_profit')
            elif pnl_percentage >= 20:
                bg_file = self.config.get('BACKGROUNDS', 'moderate_profit')
            elif pnl_percentage >= 0:
                bg_file = self.config.get('BACKGROUNDS', 'low_profit')
            elif pnl_percentage >= -20:
                bg_file = self.config.get('BACKGROUNDS', 'moderate_loss')
            else:
                bg_file = self.config.get('BACKGROUNDS', 'severe_loss')
                
            # Return full path to background
            return os.path.join(bg_path, bg_file)
        except Exception as e:
            logger.error(f"Error selecting background: {e}")
            return None
    
    def generate_pnl_image(self, trading_pair, leverage, entry_price, last_price, 
                          referral_code, pnl_percentage, is_long=True, handle_username=None, shared_date=None, 
                          handle_username_at=None, referral_message=None, signup_text=None, exchange='binance'):
        """
        Generate a PnL visualization image.
        
        Args:
            trading_pair (str): The trading pair (e.g., BTCUSDT)
            leverage (int): The leverage multiplier
            entry_price (float): The entry price of the position
            last_price (float): The current/last price
            referral_code (str): The referral code to be included in the image
            pnl_percentage (float): The calculated PnL percentage
            is_long (bool): True for long positions, False for short positions
            handle_username (str, optional): Username for BitGet template
            
        Returns:
            str: Path to the generated image
        """
        try:
            # Get template path
            template_path = self._get_template_path()
            if not os.path.exists(template_path):
                logger.error(f"Template file not found: {template_path}")
                raise FileNotFoundError(f"Template file not found: {template_path}")
            
            # Create the base image
            img = Image.open(template_path)
            draw = ImageDraw.Draw(img)
            
            # Generate QR code for referral code
            qr_code_img = self._generate_qr_code(referral_code)
            
            # Get layout coordinates from config
            try:
                position_x = int(self.config.get('LAYOUT', 'position_type_x'))
                position_y = int(self.config.get('LAYOUT', 'position_type_y'))
                leverage_x = int(self.config.get('LAYOUT', 'leverage_x'))
                leverage_y = int(self.config.get('LAYOUT', 'leverage_y'))
                trading_pair_x = int(self.config.get('LAYOUT', 'trading_pair_x'))
                trading_pair_y = int(self.config.get('LAYOUT', 'trading_pair_y'))
                
                pnl_x = int(self.config.get('LAYOUT', 'pnl_percentage_x'))
                pnl_y = int(self.config.get('LAYOUT', 'pnl_percentage_y'))
                
                entry_value_x = int(self.config.get('LAYOUT', 'entry_price_value_x'))
                entry_value_y = int(self.config.get('LAYOUT', 'entry_price_value_y'))
                
                last_value_x = int(self.config.get('LAYOUT', 'last_price_value_x'))
                last_value_y = int(self.config.get('LAYOUT', 'last_price_value_y'))

                # Get shared date coordinates with fallback values
                shared_date_x = int(self.config.get('LAYOUT', 'shared_date_x', fallback=0))
                shared_date_y = int(self.config.get('LAYOUT', 'shared_date_y', fallback=0))
                
                # Get handle username coordinates if they exist in config
                handle_username_x = int(self.config.get('LAYOUT', 'handle_username_x', fallback=0))
                handle_username_y = int(self.config.get('LAYOUT', 'handle_username_y', fallback=0))
                handle_username_at_x = int(self.config.get('LAYOUT', 'handle_username_at_x', fallback=0))
                handle_username_at_y = int(self.config.get('LAYOUT', 'handle_username_at_y', fallback=0))
                
                qr_x = int(self.config.get('LAYOUT', 'qr_code_x'))
                qr_y = int(self.config.get('LAYOUT', 'qr_code_y'))
                qr_size = int(self.config.get('LAYOUT', 'qr_code_size', fallback='100'))
                
                ref_value_x = int(self.config.get('LAYOUT', 'referral_code_value_x'))
                ref_value_y = int(self.config.get('LAYOUT', 'referral_code_value_y'))
            except (ValueError, configparser.NoOptionError) as e:
                logger.error(f"Error getting layout coordinates: {e}")
                raise ValueError(f"Error in layout configuration: {e}")

            
            # Draw position type
            position_text = "Long" if is_long else "Short"
            position_color = self._get_color('position_type_long_color' if is_long else 'position_type_short_color')
            if 'position_type' in self.fonts:
                draw.text((position_x, position_y), position_text, fill=position_color, font=self.fonts['position_type'])
            
            # Draw leverage
            leverage_text = f"{leverage}x"  # Default format
            
            # Add separator variable based on exchange
            separator = ""
            if exchange=="mexc":
                separator = "/"
                leverage_text = f"{separator}{leverage}X"
            elif exchange=="bitget":
                separator = "|"
                leverage_text = f"{separator} {leverage}x"
            elif exchange=="binance":
                leverage_text = f"{leverage}x"

            if 'leverage' in self.fonts:
                draw.text((leverage_x, leverage_y), leverage_text, fill=self._get_color('leverage_color'), 
                         font=self.fonts['leverage'])
            
            # Draw trading pair
            if 'trading_pair' in self.fonts:
                draw.text((trading_pair_x, trading_pair_y), trading_pair, fill=self._get_color('trading_pair_color'), 
                         font=self.fonts['trading_pair'])
            
            # Draw PnL percentage
            is_profit = pnl_percentage >= 0
            pnl_text = f"{'+' if is_profit else ''}{pnl_percentage:.2f}%"
            pnl_color = self._get_color('pnl_percentage', is_profit=is_profit)
            if 'pnl_percentage' in self.fonts:
                draw.text((pnl_x, pnl_y), pnl_text, fill=pnl_color, font=self.fonts['pnl_percentage'])
            
            # Draw prices
            if 'entry_price_value' in self.fonts:
                draw.text((entry_value_x, entry_value_y), f"${entry_price:.3f}" if exchange == "mexc" else f"{entry_price:.3f}", 
                         fill=self._get_color('entry_price_value_color'), font=self.fonts['entry_price_value'])
            
            if 'last_price_value' in self.fonts:
                draw.text((last_value_x, last_value_y), f"${last_price:.3f}" if exchange == "mexc" else f"{last_price:.3f}", 
                         fill=self._get_color('last_price_value_color'), font=self.fonts['last_price_value'])
            
            # Paste QR code
            if qr_code_img:
                qr_code_img = qr_code_img.resize((qr_size, qr_size))
                img.paste(qr_code_img, (qr_x, qr_y))
            
            # Draw referral code
            if 'referral_code_value' in self.fonts:
                draw.text((ref_value_x, ref_value_y), referral_code, 
                         fill=self._get_color('referral_code_value_color'), font=self.fonts['referral_code_value'])
            # Draw shared date code if applicable
            if shared_date:
                logger.info(f"Shared date value: {shared_date}")
                logger.info(f"Shared date font in self.fonts: {'shared_date' in self.fonts}")
                if 'shared_date' in self.fonts:
                    logger.info(f"Drawing shared date: {shared_date} at ({shared_date_x}, {shared_date_y})")
                    draw.text((shared_date_x, shared_date_y), shared_date, 
                             fill=self._get_color('shared_date_color'), font=self.fonts['shared_date'])
                else:
                    logger.warning(f"'shared_date' font not found in self.fonts dictionary. Available fonts: {list(self.fonts.keys())}")
            else:
                logger.warning("Shared date not drawn. shared_date value is None or empty.")
            # Draw Handle Username code
            if handle_username and 'handle_username' in self.fonts:
                draw.text((handle_username_x, handle_username_y), handle_username, 
                         fill=self._get_color('handle_username_color'), font=self.fonts['handle_username'])
            
            # Draw Handle Username At code (the @ symbol plus username for BitGet)
            if handle_username_at and handle_username and 'handle_username_at' in self.fonts:
                # Get and draw the @ symbol with username
                at_username = '@' + handle_username
                draw.text((handle_username_at_x, handle_username_at_y), at_username, 
                         fill=self._get_color('handle_username_at_color'), font=self.fonts['handle_username_at'])

            # Get signup text coordinates if they exist in config
            try:
                signup_text_x = int(self.config.get('LAYOUT', 'signup_text_x', fallback=0))
                signup_text_y = int(self.config.get('LAYOUT', 'signup_text_y', fallback=0))
            except (ValueError, configparser.NoOptionError):
                signup_text_x = 0
                signup_text_y = 0

            # Draw Signup Text code
            if signup_text and 'signup_text' in self.fonts:
                draw.text((signup_text_x, signup_text_y), signup_text, 
                         fill=self._get_color('signup_text_color'), font=self.fonts['signup_text'])
            # Save the image
            output_path = self._get_output_path(trading_pair, is_long)
            img.save(output_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating PnL image: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _generate_qr_code(self, referral_code):
        """Generate QR code for referral code"""
        try:
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            
            # Add data
            qr.add_data(f"https://accounts.binance.com/register?ref={referral_code}")
            qr.make(fit=True)
            
            # Create an image from the QR Code instance
            qr_img = qr.make_image(fill_color="black", back_color="white")
            return qr_img
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None
    
    def _get_template_path(self):
        """Get path to template image based on configuration"""
        try:
            template_path = self.config.get('TEMPLATES', 'path', fallback='./assets/templates/')
            template_file = self.config.get('TEMPLATES', 'template_file', fallback='template.png')
            
            full_path = os.path.join(template_path, template_file)
            logger.info(f"Using template: {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"Error getting template path: {e}")
            raise
    
    def _get_output_path(self, trading_pair, is_long):
        """Generate an output file path based on trading pair and other info"""
        try:
            # Check for environment variable override for serverless environments
            output_dir = os.environ.get('OUTPUT_DIR', self.config.get('OUTPUT', 'dir', fallback='./output'))
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            position_type = "LONG" if is_long else "SHORT"
            output_format = self.config.get('OUTPUT', 'format', fallback='PNG')
            
            filename = f"{trading_pair.replace('/', '_')}_{position_type}_{timestamp}.{output_format.lower()}"
            return os.path.join(output_dir, filename)
        except Exception as e:
            logger.error(f"Error generating output path: {e}")
            # Fallback to a generic output file
            return os.path.join("./output", f"pnl_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    def load_font_safely(self, font_path, size, default_size=24):
        """
        Load a font with proper fallback options if the font isn't found
        
        Args:
            font_path: Path to the font file
            size: Font size
            default_size: Size to use for default font if all else fails
            
        Returns:
            A usable font object
        """
        try:
            # First try loading the specified font
            logger.debug(f"Attempting to load font: {font_path} at size {size}")
            
            # Make sure the font file exists
            if not os.path.exists(font_path):
                logger.warning(f"Font file not found: {font_path}")
                raise FileNotFoundError(f"Font file not found: {font_path}")
                
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError) as e:
            logger.warning(f"Could not load font {font_path}: {e}")
            
            # Try system fonts as fallbacks
            system_fonts = [
                # Common system fonts on different platforms
                "Arial.ttf", "Helvetica.ttf", "DejaVuSans.ttf", 
                "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf",
                # Original fonts from config
                "SF-Pro-Display-Medium.otf", "SF-Pro-Display-Bold.otf", "SF-Pro-Display-Regular.otf",
                "NeologyGrotesque-Medium.ttf", "NeologyGrotesque-Bold.ttf", "IBMPlexSans_Condensed-Regular.ttf",
                "DIN Black.ttf", "DIN Bold.ttf", "DIN Medium.ttf"
            ]
            
            # Try each fallback font
            font_dir = os.path.dirname(font_path)
            for fallback in system_fonts:
                try:
                    fallback_path = os.path.join(font_dir, fallback)
                    if os.path.exists(fallback_path):
                        logger.info(f"Using fallback font: {fallback}")
                        return ImageFont.truetype(fallback_path, size)
                except (OSError, IOError):
                    continue
                
            # Last resort: try to find ANY usable font in the directory
            try:
                if os.path.exists(font_dir):
                    for file in os.listdir(font_dir):
                        if file.lower().endswith(('.ttf', '.otf')):
                            try:
                                fallback_path = os.path.join(font_dir, file)
                                logger.info(f"Using emergency fallback font: {file}")
                                return ImageFont.truetype(fallback_path, size)
                            except:
                                continue
            except:
                pass
            
            # If all else fails, use default font
            logger.warning("All fallbacks failed, using Pillow default font")
            return ImageFont.load_default()