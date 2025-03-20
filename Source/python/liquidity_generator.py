import os
import configparser
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode
from image_utils import PnLImageGenerator

class LiquidityImageGenerator(PnLImageGenerator):
    """
    Extended image generator that adds support for liquidity position details.
    """
    
    def generate_liquidity_image(self, trading_pair, position_type, pnl_percentage, 
                                 unrealized_pnl, roi, size, margin, margin_ratio,
                                 entry_price, mark_price, positions, open_orders,
                                 referral_code, output_filename=None):
        """
        Generate a liquidity position image with detailed metrics.
        
        Args:
            trading_pair (str): The trading pair (e.g., "BTCUSDT")
            position_type (str): "Long" or "Short"
            pnl_percentage (float): The calculated PnL percentage
            unrealized_pnl (float): Unrealized PnL in USDT
            roi (float): Return on Investment percentage
            size (float): Position size in USDT
            margin (float): Margin in USDT
            margin_ratio (float): Margin ratio percentage
            entry_price (float): The entry price
            mark_price (float): The mark price
            positions (int): Number of positions
            open_orders (int): Number of open orders
            referral_code (str): The referral code
            output_filename (str, optional): Custom filename for the output image
            
        Returns:
            PIL.Image: The generated image
        """
        # Base PnL Image setup
        is_long = position_type.lower() == "long"
        img = self._create_base_image(pnl_percentage)
        
        draw = ImageDraw.Draw(img)
        
        # Get layout coordinates from config
        position_x = int(self.config.get('LAYOUT', 'position_type_x'))
        position_y = int(self.config.get('LAYOUT', 'position_type_y'))
        trading_pair_x = int(self.config.get('LAYOUT', 'trading_pair_x'))
        trading_pair_y = int(self.config.get('LAYOUT', 'trading_pair_y'))
        
        pnl_x = int(self.config.get('LAYOUT', 'pnl_percentage_x'))
        pnl_y = int(self.config.get('LAYOUT', 'pnl_percentage_y'))
        
        # Draw position type and trading pair
        draw.text(
            (position_x, position_y),
            position_type,
            font=self.fonts.get('position_type', self.fonts['position']),
            fill=self._get_color('position_type', is_long=is_long)
        )
        
        draw.text(
            (trading_pair_x, trading_pair_y),
            f"{trading_pair} Perpetual",
            font=self.fonts.get('trading_pair', self.fonts['position']),
            fill=self._get_color('trading_pair')
        )
        
        # Draw PnL percentage
        sign = "+" if pnl_percentage >= 0 else ""
        draw.text(
            (pnl_x, pnl_y),
            f"{sign}{pnl_percentage:.2f}%",
            font=self.fonts.get('pnl_percentage', self.fonts['pnl']),
            fill=self._get_color('pnl_percentage', is_profit=pnl_percentage >= 0)
        )
        
        # Draw liquidity-specific fields - left column
        self._draw_labeled_value(draw, 
            "Unrealized PNL (USDT)", 
            f"${unrealized_pnl:.2f}",
            int(self.config.get('LAYOUT', 'unrealized_pnl_label_x')),
            int(self.config.get('LAYOUT', 'unrealized_pnl_label_y')),
            int(self.config.get('LAYOUT', 'unrealized_pnl_value_x')),
            int(self.config.get('LAYOUT', 'unrealized_pnl_value_y')),
            'unrealized_pnl_label', 'unrealized_pnl_value'
        )
        
        self._draw_labeled_value(draw, 
            "ROI", 
            f"{roi:.2f}%",
            int(self.config.get('LAYOUT', 'roi_label_x')),
            int(self.config.get('LAYOUT', 'roi_label_y')),
            int(self.config.get('LAYOUT', 'roi_value_x')),
            int(self.config.get('LAYOUT', 'roi_value_y')),
            'roi_label', 'roi_value'
        )
        
        self._draw_labeled_value(draw, 
            "Size (USDT)", 
            f"${size:.2f}",
            int(self.config.get('LAYOUT', 'size_label_x')),
            int(self.config.get('LAYOUT', 'size_label_y')),
            int(self.config.get('LAYOUT', 'size_value_x')),
            int(self.config.get('LAYOUT', 'size_value_y')),
            'size_label', 'size_value'
        )
        
        self._draw_labeled_value(draw, 
            "Margin (USDT)", 
            f"${margin:.2f}",
            int(self.config.get('LAYOUT', 'margin_label_x')),
            int(self.config.get('LAYOUT', 'margin_label_y')),
            int(self.config.get('LAYOUT', 'margin_value_x')),
            int(self.config.get('LAYOUT', 'margin_value_y')),
            'margin_label', 'margin_value'
        )
        
        # Draw liquidity-specific fields - right column
        self._draw_labeled_value(draw, 
            "Margin Ratio", 
            f"{margin_ratio:.2f}%",
            int(self.config.get('LAYOUT', 'margin_ratio_label_x')),
            int(self.config.get('LAYOUT', 'margin_ratio_label_y')),
            int(self.config.get('LAYOUT', 'margin_ratio_value_x')),
            int(self.config.get('LAYOUT', 'margin_ratio_value_y')),
            'margin_ratio_label', 'margin_ratio_value'
        )
        
        self._draw_labeled_value(draw, 
            "Mark Price (USDT)", 
            f"${mark_price:.2f}",
            int(self.config.get('LAYOUT', 'mark_price_label_x')),
            int(self.config.get('LAYOUT', 'mark_price_label_y')),
            int(self.config.get('LAYOUT', 'mark_price_value_x')),
            int(self.config.get('LAYOUT', 'mark_price_value_y')),
            'mark_price_label', 'mark_price_value'
        )
        
        self._draw_labeled_value(draw, 
            "Positions", 
            f"{positions}",
            int(self.config.get('LAYOUT', 'positions_label_x')),
            int(self.config.get('LAYOUT', 'positions_label_y')),
            int(self.config.get('LAYOUT', 'positions_value_x')),
            int(self.config.get('LAYOUT', 'positions_value_y')),
            'positions_label', 'positions_value'
        )
        
        self._draw_labeled_value(draw, 
            "Open Orders", 
            f"{open_orders}",
            int(self.config.get('LAYOUT', 'open_orders_label_x')),
            int(self.config.get('LAYOUT', 'open_orders_label_y')),
            int(self.config.get('LAYOUT', 'open_orders_value_x')),
            int(self.config.get('LAYOUT', 'open_orders_value_y')),
            'open_orders_label', 'open_orders_value'
        )
        
        # Add QR code
        qr_x = int(self.config.get('LAYOUT', 'qr_code_x'))
        qr_y = int(self.config.get('LAYOUT', 'qr_code_y'))
        qr_img = self._generate_qr_code(referral_code)
        img.paste(qr_img, (qr_x, qr_y))
        
        # Add referral code
        ref_value_x = int(self.config.get('LAYOUT', 'referral_code_value_x'))
        ref_value_y = int(self.config.get('LAYOUT', 'referral_code_value_y'))
        draw.text(
            (ref_value_x, ref_value_y),
            f"{referral_code}",
            font=self.fonts.get('referral_code_value', self.fonts['medium']),
            fill=self._get_color('referral_code_value')
        )
        
        # Add date
        self._add_date_to_image(draw)
        
        # Save the image if filename provided
        if output_filename:
            output_dir = self.config.get('OUTPUT', 'dir')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            output_path = os.path.join(output_dir, output_filename)
            img.save(output_path, format=self.config.get('OUTPUT', 'format', fallback='PNG'))
        
        return img
    
    def _draw_labeled_value(self, draw, label_text, value_text, 
                           label_x, label_y, value_x, value_y, 
                           label_font_key, value_font_key):
        """Helper method to draw a label and its value"""
        # Draw the label
        draw.text(
            (label_x, label_y),
            label_text,
            font=self.fonts.get(label_font_key, self.fonts['medium']),
            fill=self._get_color(f'{label_font_key}_color')
        )
        
        # Draw the value
        draw.text(
            (value_x, value_y),
            value_text,
            font=self.fonts.get(value_font_key, self.fonts['medium']),
            fill=self._get_color(f'{value_font_key}_color')
        )
    
    def _create_base_image(self, pnl_percentage):
        """Create the base image with background"""
        try:
            # First try to load background based on PnL
            bg_path = self._select_background(pnl_percentage)
            img = Image.open(bg_path)
        except Exception as e:
            print(f"Error loading background: {e}")
            # Try to use template instead
            if self.config.has_section('TEMPLATES') and self.config.has_option('TEMPLATES', 'path') and self.config.has_option('TEMPLATES', 'template_file'):
                template_path = os.path.join(
                    self.config.get('TEMPLATES', 'path'),
                    self.config.get('TEMPLATES', 'template_file')
                )
                if os.path.exists(template_path):
                    img = Image.open(template_path)
                else:
                    # Fall back to blank image
                    img = Image.new('RGB', (1920, 1080), color=(20, 20, 20))
            else:
                # Fall back to blank image
                img = Image.new('RGB', (1920, 1080), color=(20, 20, 20))
        
        return img
    
    def _add_date_to_image(self, draw):
        """Add date to the image based on template"""
        if (self.config.has_section('LAYOUT') and 
            self.config.has_option('LAYOUT', 'shared_date_x') and 
            self.config.has_option('LAYOUT', 'shared_date_y')):
            
            shared_date_x = int(self.config.get('LAYOUT', 'shared_date_x'))
            shared_date_y = int(self.config.get('LAYOUT', 'shared_date_y'))
            shared_date_size = int(self.config.get('LAYOUT', 'shared_date_size', fallback=28))
            
            # Get current datetime
            now = datetime.now()
            date_str = f"Shared on: {now.strftime('%d %b %Y')}"
            
            # Get font for date
            font_path = self.config.get('FONTS', 'path')
            font_key = self.config.get('LAYOUT', 'shared_date_font', fallback='regular_font')
            
            # Try to load the font
            if font_key == 'main_font':
                font_file = self.config.get('FONTS', 'main_font')
            elif font_key == 'bold_font':
                font_file = self.config.get('FONTS', 'bold_font')
            elif font_key == 'regular_font':
                font_file = self.config.get('FONTS', 'regular_font')
            else:
                font_file = self.config.get('FONTS', 'regular_font')
            
            try:
                custom_font = ImageFont.truetype(os.path.join(font_path, font_file), shared_date_size)
            except Exception as e:
                print(f"Error loading date font: {e}")
                custom_font = self.fonts.get('small', ImageFont.load_default())
            
            # Get color for date
            shared_date_color = self._get_color('text_secondary')
            if self.config.has_section('COLORS') and self.config.has_option('COLORS', 'shared_date_color'):
                shared_date_color = self._parse_color(self.config.get('COLORS', 'shared_date_color'))
            
            # Draw the date
            draw.text(
                (shared_date_x, shared_date_y),
                date_str,
                font=custom_font,
                fill=shared_date_color
            )