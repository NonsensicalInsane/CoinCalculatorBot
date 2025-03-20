"""
Optimized Binance web scraper for retrieving leverage and other data
with significantly improved performance
"""

import os
import json
import time
import logging
import requests
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create cache directory if it doesn't exist
os.makedirs("./Source/python/cache", exist_ok=True)

# Try importing selenium - mark as optional dependency
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, 
        WebDriverException, ElementNotInteractableException
    )
    
    # Check for webdriver_manager (makes selenium setup easier)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.firefox import GeckoDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
    
    SELENIUM_AVAILABLE = True
    logger.info("Selenium is available for web scraping")
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    logger.warning("Selenium not available. Web scraping capabilities will be limited.")

# Default configuration with optimized values
DEFAULT_CONFIG = {
    "update_interval": 60,  # minutes
    "cache_timeout": 300,   # seconds
    "max_threads": 5,       # increased for parallel processing
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "selenium_timeout": 10,  # timeout for selenium operations
    "headless": True,
    "leverage_file": "./Source/python/cache/binance_leverage_data.json",  # Updated path
    "leverage_cache_hours": 168,   # 7 days for cache validity
    "auto_update": False,
    "comprehensive_update": False,
    "on_demand": True,
    "api_first": False,     # Changed to False: don't try API first
    "use_calculator": True  # New flag to use calculator page instead of contract details
}

# Binance API endpoints and URLs
BINANCE_API_BASE = "https://fapi.binance.com"
BINANCE_FUTURES_URL = "https://www.binance.com/en/futures"
BINANCE_CALCULATOR_URL = "https://www.binance.com/en/futures/{symbol}/calculator"

# Common leverage values for popular coins - used as fallback
COMMON_LEVERAGES = {
    "BTCUSDT": 125, "ETHUSDT": 100, "BNBUSDT": 75, 
    "ADAUSDT": 75, "SOLUSDT": 50, "XRPUSDT": 75, 
    "DOGEUSDT": 75, "LINKUSDT": 75, "ZETAUSDT": 75,
    "DOTUSD": 75, "MATICUSDT": 50, "AVAXUSDT": 50,
    "SHIBUSDT": 20, "NEARUSDT": 50, "LTCUSDT": 75,
    "ATOMUSDT": 50, "ALGOUSDT": 20, "EOSUSDT": 50,
    "ETCUSDT": 75, "FILUSDT": 50, "UNIUSDT": 50
}

class BinanceScraper:
    """Optimized scraper for Binance Futures data"""
    
    def __init__(self, config_path='config.cfg'):
        """Initialize the Binance scraper with configuration"""
        self.config = DEFAULT_CONFIG.copy()
        self.load_config(config_path)
        
        # Initialize data structures
        self.leverage_map = {}
        self.last_update = datetime.now() - timedelta(hours=self.config["leverage_cache_hours"] + 1)  # Force initial load
        self.driver = None
        self.symbols = []
        self.symbols_last_update = None
        
        # Load any previously saved data
        self._load_leverage_data()
        
        # Executor for parallel scraping
        self.executor = None
        
        logger.info(f"Binance Scraper initialized with cache file: {self.config['leverage_file']}")
    
    def load_config(self, config_path):
        """Load configuration from file"""
        try:
            import configparser
            config = configparser.ConfigParser()
            
            if os.path.exists(config_path):
                config.read(config_path)
                
                if config.has_section("BINANCE_SCRAPER"):
                    scraper_config = config["BINANCE_SCRAPER"]
                    
                    # Update config with values from file
                    for key in self.config:
                        if key in scraper_config:
                            # Type conversion based on default types
                            default_type = type(self.config[key])
                            if default_type == bool:
                                self.config[key] = scraper_config.getboolean(key)
                            elif default_type == int:
                                self.config[key] = scraper_config.getint(key)
                            else:
                                self.config[key] = scraper_config.get(key)
        except Exception as e:
            logger.warning(f"Error loading scraper config: {e}, using defaults")
    
    def _load_leverage_data(self):
        """Load previously saved leverage data if available"""
        leverage_file = self.config["leverage_file"]
        
        try:
            if os.path.exists(leverage_file):
                with open(leverage_file, 'r') as f:
                    data = json.load(f)
                    
                    # Check if data format is correct
                    if isinstance(data, dict) and "leverage_map" in data and "last_update" in data:
                        self.leverage_map = data["leverage_map"]
                        self.last_update = datetime.fromisoformat(data["last_update"])
                        
                        # Check if data is still valid based on cache duration
                        cache_hours = self.config["leverage_cache_hours"]
                        if (datetime.now() - self.last_update) > timedelta(hours=cache_hours):
                            logger.info(f"Leverage data is older than {cache_hours} hours, will update when needed")
                        else:
                            logger.info(f"Loaded leverage data for {len(self.leverage_map)} symbols")
                            return True
                    else:
                        logger.warning("Leverage data file has invalid format, initializing new data")
        except Exception as e:
            logger.warning(f"Error loading leverage data: {e}")
        
        # Initialize empty data if loading failed
        self.leverage_map = {}
        self.last_update = datetime.now()
        return False
    
    def _save_leverage_map(self):
        """Save current leverage data to file"""
        try:
            leverage_file = self.config["leverage_file"]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(leverage_file), exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "leverage_map": self.leverage_map,
                "last_update": self.last_update.isoformat()
            }
            
            with open(leverage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved leverage data for {len(self.leverage_map)} symbols")
            return True
        except Exception as e:
            logger.error(f"Error saving leverage data: {e}")
            return False
    
    def _initialize_selenium(self):
        """Initialize Selenium WebDriver with optimized settings"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not available. Please install selenium: pip install selenium")
        
        try:
            options = Options()
            
            # Set headless mode based on config
            if self.config["headless"]:
                options.add_argument("--headless=new")  # Use newer headless mode
            
            # Add optimized browser options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1280,720")
            options.add_argument(f"user-agent={self.config['user_agent']}")
            
            # Performance optimization flags
            options.add_argument("--js-flags=--expose-gc")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-translate")
            options.add_argument("--disk-cache-size=50000000")  # 50MB disk cache
            
            # Initialize appropriate WebDriver with optimized approach
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                    logger.info("Initialized Chrome WebDriver with webdriver_manager")
                except Exception as chrome_error:
                    logger.warning(f"Chrome initialization failed, trying Firefox: {chrome_error}")
                    try:
                        # Fall back to Firefox
                        firefox_options = webdriver.FirefoxOptions()
                        if self.config["headless"]:
                            firefox_options.add_argument("--headless")
                        service = Service(GeckoDriverManager().install())
                        self.driver = webdriver.Firefox(service=service, options=firefox_options)
                        logger.info("Initialized Firefox WebDriver with webdriver_manager")
                    except Exception as firefox_error:
                        logger.error(f"Firefox initialization also failed: {firefox_error}")
                        raise firefox_error
            else:
                # Try to initialize with system-installed drivers
                try:
                    self.driver = webdriver.Chrome(options=options)
                    logger.info("Initialized Chrome WebDriver")
                except Exception as chrome_error:
                    logger.warning(f"Chrome initialization failed, trying Firefox: {chrome_error}")
                    try:
                        # Fall back to Firefox
                        firefox_options = webdriver.FirefoxOptions()
                        if self.config["headless"]:
                            firefox_options.add_argument("--headless")
                        self.driver = webdriver.Firefox(options=firefox_options)
                        logger.info("Initialized Firefox WebDriver")
                    except Exception as firefox_error:
                        logger.error(f"Firefox initialization also failed: {firefox_error}")
                        raise firefox_error
            
            # Set page load timeout
            self.driver.set_page_load_timeout(self.config["selenium_timeout"])
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            self.driver = None
            raise e
    
    def _close_selenium(self):
        """Close Selenium WebDriver if it's open"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Closed WebDriver")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def get_max_leverage(self, symbol: str) -> int:
        """
        Get the maximum leverage available for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            int: Maximum leverage value
        """
        # Normalize symbol to uppercase
        symbol = symbol.upper()
        
        # Check if we have a value in cache and it's not expired
        cache_valid = (datetime.now() - self.last_update) <= timedelta(hours=self.config["leverage_cache_hours"])
        if symbol in self.leverage_map and cache_valid:
            leverage = self.leverage_map[symbol]
            logger.info(f"Using cached leverage for {symbol}: {leverage}x")
            return leverage
            
        # If on-demand updates are enabled, get the leverage
        if self.config["on_demand"]:
            try:
                logger.info(f"Updating leverage data for {symbol}")
                success = self.update_symbol_leverage(symbol)
                if success and symbol in self.leverage_map:
                    return self.leverage_map[symbol]
            except Exception as e:
                logger.warning(f"Error updating leverage for {symbol}: {e}")
                # Continue to check common values
        
        # Check if it's a common symbol with known leverage
        if symbol in COMMON_LEVERAGES:
            logger.info(f"Using known common leverage for {symbol}: {COMMON_LEVERAGES[symbol]}x")
            self.leverage_map[symbol] = COMMON_LEVERAGES[symbol]
            self._save_leverage_map()
            return COMMON_LEVERAGES[symbol]
        
        # Default value if nothing else is available
        default_leverage = 20
        logger.info(f"No leverage data for {symbol}, using default: {default_leverage}x")
        return default_leverage
    
    def _get_leverage_from_api(self, symbol: str) -> Optional[int]:
        """
        Try to get leverage from Binance API
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Optional[int]: Maximum leverage if available, None otherwise
        """
        # We're not using the API approach now, as requested
        logger.info(f"API-first approach is disabled for {symbol}, using web scraping instead")
        return None
    
    def _get_leverage_from_calculator(self, symbol: str) -> Optional[int]:
        """
        Get maximum leverage by scraping the Binance Futures Calculator page
        
        Args:
            symbol: Trading pair symbol (e.g. BTCUSDT)
            
        Returns:
            Optional[int]: Maximum leverage value if found, None otherwise
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available for web scraping")
            return None
        
        start_time = time.time()
        
        # Initialize the driver if not already done
        if not self.driver:
            try:
                self._initialize_selenium()
            except Exception as e:
                logger.error(f"Could not initialize Selenium: {e}")
                return None
        
        try:
            # Use calculator page URL
            calculator_url = BINANCE_CALCULATOR_URL.format(symbol=symbol.lower())
            logger.info(f"Loading calculator page: {calculator_url}")
            self.driver.get(calculator_url)
            
            # Wait for page to load
            time.sleep(2)  # Brief wait for JavaScript to load
            
            # Method 1 (Primary): Target the exact slider input element shown in the example
            try:
                # Look for the input element with type="range" inside bn-slider-wrapper
                slider_input = WebDriverWait(self.driver, self.config["selenium_timeout"]).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "div.bn-slider-wrapper input[type='range']"))
                )
                
                # Extract the max attribute directly
                max_value = slider_input.get_attribute("max")
                if max_value and max_value.isdigit():
                    leverage = int(max_value)
                    logger.info(f"Found max leverage from slider input: {leverage}x (took {time.time() - start_time:.2f}s)")
                    return leverage
            except Exception as e:
                logger.warning(f"Error extracting leverage from slider input: {e}")
            
            # Alternative selectors to find the slider
            try:
                # Look for any input element with type="range" and a max attribute
                range_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='range']")
                for input_elem in range_inputs:
                    max_attr = input_elem.get_attribute("max")
                    if max_attr and max_attr.isdigit():
                        leverage = int(max_attr)
                        logger.info(f"Found max leverage from range input: {leverage}x (took {time.time() - start_time:.2f}s)")
                        return leverage
            except Exception as e:
                logger.warning(f"Error extracting leverage from alternative input elements: {e}")
            
            # Method 2: Look for the last step mark which should contain the max leverage
            try:
                # Find the last step mark in the slider track (the rightmost one)
                last_step = self.driver.find_element(By.CSS_SELECTOR, 
                    "div.bn-slider-track div.bn-slider-track-step:last-child div.bn-slider-track-step-mark")
                
                if last_step:
                    step_text = last_step.text.strip()
                    # Extract numeric part from "125x"
                    import re
                    match = re.search(r'(\d+)x', step_text)
                    if match:
                        leverage = int(match.group(1))
                        logger.info(f"Found max leverage from last step mark: {leverage}x (took {time.time() - start_time:.2f}s)")
                        return leverage
            except Exception as e:
                logger.warning(f"Error extracting leverage from step marks: {e}")
            
            # If the specific methods failed, continue with other fallback methods...
            
            # Method 3: Look for leverage input field and its label
            try:
                leverage_input = self.driver.find_element(By.CSS_SELECTOR, 
                    "input[data-testid='futures-calculator-leverage-input']")
                
                # Try to get max value from input field
                max_attr = leverage_input.get_attribute("max")
                if max_attr and max_attr.isdigit():
                    leverage = int(max_attr)
                    logger.info(f"Found max leverage from input max attribute: {leverage}x (took {time.time() - start_time:.2f}s)")
                    return leverage
                
                # Try to find max leverage from label text
                label_element = self.driver.find_element(By.XPATH, 
                    "//span[contains(text(), 'Max') and contains(text(), 'x')]")
                label_text = label_element.text
                
                import re
                match = re.search(r'Max[:\s]*(\d+)x', label_text)
                if match:
                    leverage = int(match.group(1))
                    logger.info(f"Found max leverage from label text: {leverage}x (took {time.time() - start_time:.2f}s)")
                    return leverage
                
            except Exception as e:
                logger.warning(f"Error looking for leverage input: {e}")
            
            # Method 4: Check for Calculator header information
            try:
                # Look for text that mentions max leverage
                max_leverage_text = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Max Leverage') or contains(text(), 'Maximum Leverage')]")
                
                for element in max_leverage_text:
                    text = element.text
                    import re
                    match = re.search(r'(\d+)x', text)
                    if match:
                        leverage = int(match.group(1))
                        logger.info(f"Found max leverage from page text: {leverage}x (took {time.time() - start_time:.2f}s)")
                        return leverage
                
            except Exception as e:
                logger.warning(f"Error looking for leverage text: {e}")
            
            # Method 5: Try entering a very large leverage value and see what it caps at
            try:
                leverage_input = self.driver.find_element(By.CSS_SELECTOR, 
                    "input[data-testid='futures-calculator-leverage-input']")
                
                # Clear the field and try to input a very large value
                leverage_input.clear()
                test_value = "999"
                leverage_input.send_keys(test_value)
                
                # Wait for possible value change
                time.sleep(0.5)
                
                # Get actual value (it might cap at max)
                actual_value = leverage_input.get_attribute("value")
                if actual_value.isdigit() and actual_value != test_value:
                    leverage = int(actual_value)
                    logger.info(f"Found max leverage by input testing: {leverage}x (took {time.time() - start_time:.2f}s)")
                    return leverage
                
            except Exception as e:
                logger.warning(f"Error testing leverage input: {e}")
            
            # Method 6: Look at page source for clues
            try:
                page_source = self.driver.page_source
                import re
                
                # Look for max leverage in various formats in page source
                patterns = [
                    r'"maxLeverage":(\d+)',
                    r'"max_leverage":(\d+)',
                    r'"maximumLeverage":(\d+)',
                    r'"leverage":[^}]*"max":(\d+)',
                    r'max[Ll]everage["\s:=]+(\d+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, page_source)
                    if match:
                        leverage = int(match.group(1))
                        logger.info(f"Found max leverage in page source: {leverage}x (took {time.time() - start_time:.2f}s)")
                        return leverage
                
            except Exception as e:
                logger.warning(f"Error analyzing page source: {e}")
            
            logger.warning(f"Could not find leverage on calculator page (took {time.time() - start_time:.2f}s)")
            return None
            
        except Exception as e:
            logger.error(f"Error during web scraping for {symbol}: {e}")
            return None
        finally:
            # Take a screenshot for debugging if needed
            if os.environ.get("DEBUG_SCREENSHOTS") == "1":
                try:
                    os.makedirs("./Source/python/cache/screenshots", exist_ok=True)
                    self.driver.save_screenshot(f"./Source/python/cache/screenshots/{symbol.lower()}_calculator.png")
                except Exception as e:
                    logger.warning(f"Failed to save debug screenshot: {e}")
    
    def update_symbol_leverage(self, symbol: str) -> bool:
        """
        Update leverage data for a specific symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            bool: True if update successful, False otherwise
        """
        symbol = symbol.upper()  # Normalize to uppercase
        
        # Try API first only if configured (now disabled by default)
        if self.config["api_first"]:
            api_leverage = self._get_leverage_from_api(symbol)
            if api_leverage:
                self.leverage_map[symbol] = api_leverage
                self.last_update = datetime.now()
                self._save_leverage_map()
                return True
        
        # Use calculator page for web scraping
        if SELENIUM_AVAILABLE and self.config["use_calculator"]:
            calculator_leverage = self._get_leverage_from_calculator(symbol)
            if calculator_leverage:
                self.leverage_map[symbol] = calculator_leverage
                self.last_update = datetime.now()
                self._save_leverage_map()
                return True
        
        # If all scraping attempts failed, check if we already have a value
        if symbol in self.leverage_map:
            logger.info(f"Keeping existing leverage value for {symbol}: {self.leverage_map[symbol]}x")
            return True
        
        # Use common values as fallback
        if symbol in COMMON_LEVERAGES:
            logger.info(f"Using known leverage for common symbol {symbol}: {COMMON_LEVERAGES[symbol]}x")
            self.leverage_map[symbol] = COMMON_LEVERAGES[symbol]
            self._save_leverage_map()
            return True
        
        # If all else fails, use a default value
        logger.warning(f"Could not determine leverage for {symbol}, using default 20x")
        self.leverage_map[symbol] = 20
        self._save_leverage_map()
        return False
    
    def get_available_symbols(self) -> List[str]:
        """
        Get list of available trading pairs
        
        Returns:
            List[str]: List of symbol strings
        """
        # Return cached symbols if fresh (less than 1 hour old)
        if self.symbols and self.symbols_last_update and (datetime.now() - self.symbols_last_update < timedelta(hours=1)):
            return self.symbols
        
        try:
            # Try to get from public API first (most reliable and extremely fast)
            url = f"{BINANCE_API_BASE}/fapi/v1/exchangeInfo"
            response = requests.get(url, timeout=5)  # Short timeout for API
            
            if response.status_code == 200:
                data = response.json()
                if "symbols" in data:
                    symbols = []
                    for item in data["symbols"]:
                        if item.get("status") == "TRADING" and item.get("contractType") == "PERPETUAL":
                            symbols.append(item.get("symbol"))
                    
                    self.symbols = symbols
                    self.symbols_last_update = datetime.now()
                    logger.info(f"Retrieved {len(symbols)} symbols from API")
                    return symbols
        except Exception as e:
            logger.warning(f"Error getting symbols from API: {e}")
        
        # Fallback to common symbols if all else fails
        common_symbols = list(COMMON_LEVERAGES.keys())
        
        logger.warning(f"Using fallback list of {len(common_symbols)} common symbols")
        self.symbols = common_symbols
        self.symbols_last_update = datetime.now()
        return common_symbols
    
    def perform_batch_update(self, symbols=None, max_symbols=20):
        """
        Perform a batch update of leverage data for multiple symbols
        
        Args:
            symbols: List of symbols to update (if None, uses most popular)
            max_symbols: Maximum number of symbols to update
            
        Returns:
            int: Number of successfully updated symbols
        """
        if symbols is None:
            # Use most popular symbols
            symbols = list(COMMON_LEVERAGES.keys())
        
        # Limit the number of symbols to update
        symbols = symbols[:max_symbols]
        
        logger.info(f"Starting batch update for {len(symbols)} symbols")
        
        # For calculator scraping, we need to do it sequentially in a single browser
        if self.config["use_calculator"] and SELENIUM_AVAILABLE:
            updated_count = 0
            
            # Initialize selenium once for all symbols
            try:
                if not self.driver:
                    self._initialize_selenium()
                
                for symbol in symbols:
                    if symbol not in self.leverage_map or (datetime.now() - self.last_update) > timedelta(hours=self.config["leverage_cache_hours"]):
                        try:
                            logger.info(f"Scraping leverage for {symbol}...")
                            leverage = self._get_leverage_from_calculator(symbol)
                            if leverage:
                                self.leverage_map[symbol] = leverage
                                updated_count += 1
                        except Exception as e:
                            logger.error(f"Error updating {symbol}: {e}")
                
                # Save updated data
                if updated_count > 0:
                    self.last_update = datetime.now()
                    self._save_leverage_map()
                
                logger.info(f"Batch update completed. Updated {updated_count}/{len(symbols)} symbols")
                return updated_count
            
            finally:
                # Always close the browser when done with batch
                self._close_selenium()
        
        # Otherwise use parallel processing for API or other methods
        else:
            # Initialize executor if needed
            if self.executor is None:
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config["max_threads"])
            
            # Submit tasks
            futures = {}
            for symbol in symbols:
                if symbol not in self.leverage_map or (datetime.now() - self.last_update) > timedelta(hours=self.config["leverage_cache_hours"]):
                    future = self.executor.submit(self._get_leverage_from_api, symbol)
                    futures[future] = symbol
            
            # Process results
            updated_count = 0
            for future in concurrent.futures.as_completed(futures, timeout=30):
                symbol = futures[future]
                try:
                    leverage = future.result()
                    if leverage:
                        self.leverage_map[symbol] = leverage
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating {symbol}: {e}")
            
            # Save updated data
            if updated_count > 0:
                self.last_update = datetime.now()
                self._save_leverage_map()
            
            logger.info(f"Batch update completed. Updated {updated_count}/{len(symbols)} symbols")
            return updated_count
    
    def perform_comprehensive_update(self):
        """
        Perform a comprehensive update of leverage data for all symbols
        
        Returns:
            int: Number of successfully updated symbols
        """
        symbols = self.get_available_symbols()
        
        # Use batch update with all symbols
        return self.perform_batch_update(symbols=symbols, max_symbols=len(symbols))
    
    def __del__(self):
        """Clean up resources when object is deleted"""
        self._close_selenium()
        if self.executor:
            self.executor.shutdown(wait=False)


# Singleton instance
_INSTANCE = None

def get_instance():
    """Get or create the singleton scraper instance"""
    global _INSTANCE
    if not _INSTANCE:
        _INSTANCE = BinanceScraper()
    return _INSTANCE

# Helper functions for direct use

def get_max_leverage(symbol: str) -> int:
    """
    Get maximum leverage for a symbol
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        int: Maximum leverage value
    """
    return get_instance().get_max_leverage(symbol)

def get_available_symbols() -> List[str]:
    """
    Get list of available trading pairs
    
    Returns:
        List[str]: List of symbol strings
    """
    return get_instance().get_available_symbols()

def update_symbol_leverage(symbol: str) -> bool:
    """
    Update leverage data for a specific symbol
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        bool: True if update successful, False otherwise
    """
    return get_instance().update_symbol_leverage(symbol)

def update_all_leverage_data() -> int:
    """
    Update leverage data for all available symbols
    
    Returns:
        int: Number of successfully updated symbols
    """
    return get_instance().perform_comprehensive_update()

def update_batch_leverage_data(symbols=None, max_symbols=20) -> int:
    """
    Update leverage data for a batch of symbols
    
    Args:
        symbols: List of symbols to update (if None, uses most popular)
        max_symbols: Maximum number of symbols to update
        
    Returns:
        int: Number of successfully updated symbols
    """
    return get_instance().perform_batch_update(symbols, max_symbols)

# Command line interface
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Binance Futures Data Scraper")
    parser.add_argument("--symbol", type=str, help="Get max leverage for a specific symbol")
    parser.add_argument("--list", action="store_true", help="List all available symbols")
    parser.add_argument("--update", action="store_true", help="Update leverage data for all symbols")
    parser.add_argument("--batch", type=int, default=0, help="Update a batch of N most popular symbols")
    parser.add_argument("--config", type=str, default="config.cfg", help="Path to configuration file")
    parser.add_argument("--debug-screenshot", action="store_true", help="Save screenshots during scraping")
    
    args = parser.parse_args()
    
    scraper = BinanceScraper(config_path=args.config)
    
    # Set debug screenshots if requested
    if args.debug_screenshot:
        os.environ["DEBUG_SCREENSHOTS"] = "1"
    
    if args.symbol:
        symbol = args.symbol.upper()
        print(f"Updating leverage data for {symbol}...")
        start_time = time.time()
        scraper.update_symbol_leverage(symbol)
        leverage = scraper.get_max_leverage(symbol)
        elapsed = time.time() - start_time
        print(f"Maximum leverage for {symbol}: {leverage}x (retrieved in {elapsed:.2f} seconds)")
    
    if args.list:
        symbols = scraper.get_available_symbols()
        print(f"Available symbols ({len(symbols)}):")
        for symbol in symbols:
            print(f"  {symbol}")
    
    if args.update:
        print("Updating leverage data for all symbols (this may take a while)...")
        start_time = time.time()
        count = scraper.perform_comprehensive_update()
        elapsed = time.time() - start_time
        print(f"Updated {count} symbols in {elapsed:.2f} seconds")
    
    if args.batch > 0:
        print(f"Updating leverage data for {args.batch} popular symbols...")
        start_time = time.time()
        count = scraper.perform_batch_update(max_symbols=args.batch)
        elapsed = time.time() - start_time
        print(f"Updated {count} symbols in {elapsed:.2f} seconds")
    
    # If no arguments provided, print help
    if not (args.symbol or args.list or args.update or args.batch > 0):
        parser.print_help() 