import requests
import json
import time
import configparser
from typing import Dict, List, Tuple, Optional

# Import the scraper and set it as the primary data source
try:
    from binance_scraper import get_max_leverage as scraper_get_max_leverage
    from binance_scraper import get_available_symbols as scraper_get_available_symbols
    SCRAPER_AVAILABLE = True
    print("Binance scraper enabled and set as primary data source")
except ImportError:
    SCRAPER_AVAILABLE = False
    print("Warning: Binance scraper not available, some features may be limited")

class BinanceAPI:
    """Class to interact with Binance API for futures data"""
    
    def __init__(self, config_path='config.cfg'):
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Set API parameters from config or use defaults
        if self.config.has_section('BINANCE_API'):
            self.BASE_URL = self.config.get('BINANCE_API', 'base_url', 
                                          fallback='https://fapi.binance.com')
            # Force correct URL regardless of config
            if 'dapi.binance.com' in self.BASE_URL:
                print("Warning: Incorrect API URL in config. Fixing to fapi.binance.com")
                self.BASE_URL = 'https://fapi.binance.com'
                # Update config for future runs
                self.config.set('BINANCE_API', 'base_url', self.BASE_URL)
                with open(config_path, 'w') as f:
                    self.config.write(f)
            self.update_interval = self.config.getint('BINANCE_API', 'update_interval', 
                                                     fallback=60)
            self.price_update_interval = self.config.getint('BINANCE_API', 'price_update_interval', 
                                                           fallback=5)
            self.default_max_leverage = self.config.getint('BINANCE_API', 'default_max_leverage', 
                                                          fallback=125)
            self.timeout = self.config.getint('BINANCE_API', 'timeout', 
                                             fallback=10)
            self.enable_caching = self.config.getboolean('BINANCE_API', 'enable_caching', 
                                                       fallback=True)
            
            # Check if we should prefer scraper (new setting)
            self.use_scraper = self.config.getboolean('BINANCE_API', 'use_scraper', 
                                                     fallback=True)
            
            # If we have a use_scraper setting but it's not in the config, add it
            if not self.config.has_option('BINANCE_API', 'use_scraper'):
                self.config.set('BINANCE_API', 'use_scraper', 'true')
                with open(config_path, 'w') as f:
                    self.config.write(f)
            
            # Get preferred pairs if specified
            preferred_pairs_str = self.config.get('BINANCE_API', 'preferred_pairs', fallback='')
            self.preferred_pairs = [p.strip() for p in preferred_pairs_str.split(',') if p.strip()]
            
            # Set custom user agent if specified
            self.user_agent = self.config.get('BINANCE_API', 'user_agent', 
                                             fallback='BinancePnLCalculator/1.0')
        else:
            # Default values if section doesn't exist
            self.BASE_URL = 'https://fapi.binance.com'
            self.update_interval = 60
            self.price_update_interval = 5
            self.default_max_leverage = 125
            self.timeout = 10
            self.enable_caching = True
            self.use_scraper = True
            self.preferred_pairs = []
            self.user_agent = 'BinancePnLCalculator/1.0'
        
        # Set up session
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Initialize data structures
        self.exchange_info = None
        self.ticker_prices = {}
        self.last_update = 0
        self.last_price_update = 0
        self.symbols_data = {}
        
        # Print scraper status
        if self.use_scraper and SCRAPER_AVAILABLE:
            print("Using web scraper for Binance data")
        elif self.use_scraper and not SCRAPER_AVAILABLE:
            print("Warning: Scraper preferred but not available, falling back to API")
        elif not self.use_scraper:
            print("Using Binance API for data (not recommended without authentication)")
    
    def _update_exchange_info(self) -> None:
        """Update exchange information if needed"""
        # If scraper is preferred and available, don't bother with API
        if self.use_scraper and SCRAPER_AVAILABLE:
            # Only update if our data is empty or stale
            current_time = time.time()
            if not self.symbols_data or (current_time - self.last_update) > self.update_interval:
                try:
                    print("Using scraper to get available symbols")
                    symbols = scraper_get_available_symbols()
                    
                    # Process symbols into our format
                    self.symbols_data = {}
                    for symbol in symbols:
                        # Get max leverage for this symbol
                        max_leverage = scraper_get_max_leverage(symbol)
                        
                        # Create symbol entry
                        self.symbols_data[symbol] = {
                            'baseAsset': symbol[:-4] if symbol.endswith('USDT') else symbol[:-3],
                            'quoteAsset': 'USDT' if symbol.endswith('USDT') else 'BUSD',
                            'maxLeverage': max_leverage,
                            'pricePrecision': 2,
                            'quantityPrecision': 2
                        }
                    
                    self.last_update = current_time
                    print(f"Updated {len(self.symbols_data)} symbols using scraper")
                except Exception as e:
                    print(f"Error updating symbol data with scraper: {e}")
                    # If we have no data at all, fall back to API
                    if not self.symbols_data and not self.use_scraper:
                        self._update_with_api()
            return
            
        # Fall back to API if scraper not used or not available
        self._update_with_api()
    
    def _update_with_api(self) -> None:
        """Update using the API (only as fallback)"""
        # Skip API calls if we're told to use scraper only
        if self.use_scraper:
            return
            
        current_time = time.time()
        
        # Skip update if caching is enabled and data is fresh
        if self.enable_caching and self.exchange_info and (current_time - self.last_update) <= self.update_interval:
            return
            
        try:
            print("Attempting to use Binance API (may require authentication)")
            response = self.session.get(f"{self.BASE_URL}/fapi/v1/exchangeInfo", timeout=self.timeout)
            response.raise_for_status()
            self.exchange_info = response.json()
            self.last_update = current_time
            self._process_exchange_info()
            
            # After processing the exchange info, fetch and update leverage brackets
            self._fetch_leverage_brackets()
            
            print(f"Updated exchange info with {len(self.symbols_data)} symbols")
        except Exception as e:
            print(f"Error updating exchange info via API: {e}")
            # If we have no data at all, try scraper one more time
            if not self.symbols_data and SCRAPER_AVAILABLE:
                print("Falling back to scraper after API failure")
                try:
                    symbols = scraper_get_available_symbols()
                    self.symbols_data = {}
                    for symbol in symbols:
                        max_leverage = scraper_get_max_leverage(symbol)
                        self.symbols_data[symbol] = {
                            'baseAsset': symbol[:-4] if symbol.endswith('USDT') else symbol[:-3],
                            'quoteAsset': 'USDT' if symbol.endswith('USDT') else 'BUSD',
                            'maxLeverage': max_leverage,
                            'pricePrecision': 2,
                            'quantityPrecision': 2
                        }
                    self.last_update = current_time
                    print(f"Updated {len(self.symbols_data)} symbols using scraper after API failure")
                except Exception as scraper_e:
                    print(f"Scraper also failed: {scraper_e}")
                    # If all else fails and we have no data, use hardcoded defaults
                    if not self.symbols_data:
                        self._use_hardcoded_defaults()
    
    def _use_hardcoded_defaults(self):
        """Use hardcoded defaults when all other methods fail"""
        print("Using hardcoded default symbols")
        default_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT"]
        default_leverages = {
            "BTCUSDT": 125, "ETHUSDT": 100, "BNBUSDT": 75, 
            "SOLUSDT": 50, "ADAUSDT": 75, "XRPUSDT": 75, 
            "DOGEUSDT": 75, "LINKUSDT": 75
        }
        
        self.symbols_data = {}
        for symbol in default_symbols:
            self.symbols_data[symbol] = {
                'baseAsset': symbol[:-4],
                'quoteAsset': 'USDT',
                'maxLeverage': default_leverages.get(symbol, 20),
                'pricePrecision': 2,
                'quantityPrecision': 2
            }
        self.last_update = time.time()
    
    def _process_exchange_info(self) -> None:
        """Process exchange info to extract symbol data"""
        self.symbols_data = {}
        
        if not self.exchange_info or 'symbols' not in self.exchange_info:
            return
            
        for symbol_data in self.exchange_info['symbols']:
            if symbol_data['status'] == 'TRADING':
                symbol = symbol_data['symbol']
                # Get leverage brackets
                max_leverage = self.default_max_leverage
                
                for filter_data in symbol_data.get('filters', []):
                    if filter_data.get('filterType') == 'LEVERAGE_BRACKET':
                        if 'brackets' in filter_data and filter_data['brackets']:
                            # Get the maximum leverage from the first bracket
                            max_leverage = filter_data['brackets'][0].get('initialLeverage', max_leverage)
                
                # Store symbol data
                self.symbols_data[symbol] = {
                    'baseAsset': symbol_data.get('baseAsset', ''),
                    'quoteAsset': symbol_data.get('quoteAsset', ''),
                    'maxLeverage': max_leverage,
                    'pricePrecision': symbol_data.get('pricePrecision', 2),
                    'quantityPrecision': symbol_data.get('quantityPrecision', 2)
                }
    
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get the current price for a symbol"""
        # Update prices if needed
        current_time = time.time()
        if not self.ticker_prices or (current_time - self.last_price_update) > self.price_update_interval:
            try:
                response = self.session.get(f"{self.BASE_URL}/fapi/v1/ticker/price", timeout=self.timeout)
                response.raise_for_status()
                
                # Update ticker prices
                self.ticker_prices = {}
                for ticker in response.json():
                    self.ticker_prices[ticker['symbol']] = float(ticker['price'])
                
                self.last_price_update = current_time
            except Exception as e:
                print(f"Error updating prices: {e}")
                # If we have no price data and failed to get it, return None
                if symbol not in self.ticker_prices:
                    return None
        
        return self.ticker_prices.get(symbol)
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols"""
        # If scraper is preferred and available, use it directly
        if self.use_scraper and SCRAPER_AVAILABLE:
            try:
                symbols = scraper_get_available_symbols()
                if symbols:
                    if self.preferred_pairs:
                        # Start with preferred pairs that exist
                        result = [p for p in self.preferred_pairs if p in symbols]
                        # Add remaining symbols
                        result.extend([s for s in sorted(symbols) if s not in result])
                        return result
                    return sorted(symbols)
            except Exception as e:
                print(f"Error getting symbols from scraper: {e}")
                # Fall through to API method if scraper fails
        
        # Original method using API or cached data
        try:
            # First try the original method
            self._update_exchange_info()
            
            # If we have data from the API and preferred pairs are set, use them
            if self.symbols_data and self.preferred_pairs:
                # Start with preferred pairs that exist in our data
                result = [p for p in self.preferred_pairs if p in self.symbols_data]
                # Add all other pairs
                result.extend([s for s in sorted(self.symbols_data.keys()) if s not in result])
                
                if result:  # If we got results from API, return them
                    print(f"Using {len(result)} symbols from API")
                    return result
            
            # If no data from API or preferred pairs not set, check if symbols_data has entries
            if self.symbols_data:
                result = sorted(list(self.symbols_data.keys()))
                if result:  # If we got results from symbols_data, return them
                    print(f"Using {len(result)} symbols from symbols_data")
                    return result
            
            # If we get here, API methods failed, try the scraper
            if SCRAPER_AVAILABLE:
                try:
                    scraped_symbols = scraper_get_available_symbols()
                    if scraped_symbols:
                        print(f"Using {len(scraped_symbols)} symbols from scraper")
                        return scraped_symbols
                except Exception as scraper_e:
                    print(f"Scraper symbols fallback failed: {scraper_e}")
            
            # Last resort: return a default list
            default_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT"]
            print(f"All methods failed, returning {len(default_symbols)} default symbols")
            return default_symbols
            
        except Exception as e:
            print(f"Error in get_available_symbols: {e}")
            
            # Try scraper as a fallback
            if SCRAPER_AVAILABLE:
                try:
                    scraped_symbols = scraper_get_available_symbols()
                    if scraped_symbols:
                        print(f"Using {len(scraped_symbols)} symbols from scraper after exception")
                        return scraped_symbols
                except Exception as scraper_e:
                    print(f"Scraper symbols fallback failed after exception: {scraper_e}")
            
            # Return minimal default list
            return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get information for a specific symbol"""
        self._update_exchange_info()
        return self.symbols_data.get(symbol)
    
    def get_max_leverage(self, symbol: str) -> int:
        """Get maximum leverage for a symbol with debugging"""
        # If scraper is preferred and available, use it directly
        if self.use_scraper and SCRAPER_AVAILABLE:
            try:
                scraped_max_lev = scraper_get_max_leverage(symbol)
                print(f"Using scraper: max leverage for {symbol}: {scraped_max_lev}")
                return scraped_max_lev
            except Exception as e:
                print(f"Scraper failed for max leverage: {e}")
                # Fall through to original method
        
        try:
            # First try the original method
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                max_lev = symbol_info.get('maxLeverage', self.default_max_leverage)
                print(f"Symbol {symbol} has max leverage: {max_lev}")
                
                # Hard-coded overrides for known symbols with restricted leverage
                if symbol == "ADAUSDT" and max_lev > 75:
                    print(f"Overriding {symbol} max leverage from {max_lev} to 75")
                    return 75
                elif symbol == "DOGEUSDT" and max_lev > 75:
                    print(f"Overriding {symbol} max leverage from {max_lev} to 75")
                    return 75
                elif symbol == "XRPUSDT" and max_lev > 75:
                    print(f"Overriding {symbol} max leverage from {max_lev} to 75")
                    return 75
                
                return max_lev
            
            # If we get here, we don't have valid symbol info from the API
            print(f"No symbol info for {symbol}, trying scraper fallback")
            
            # Try the scraper as a fallback if available
            if SCRAPER_AVAILABLE:
                try:
                    scraped_max_lev = scraper_get_max_leverage(symbol)
                    print(f"Scraped max leverage for {symbol}: {scraped_max_lev}")
                    return scraped_max_lev
                except Exception as scraper_e:
                    print(f"Scraper fallback failed: {scraper_e}")
            
            # Last resort: return default
            print(f"All methods failed, returning default max leverage: {self.default_max_leverage}")
            return self.default_max_leverage
            
        except Exception as e:
            print(f"Error in get_max_leverage: {e}")
            
            # Try scraper as a fallback
            if SCRAPER_AVAILABLE:
                try:
                    scraped_max_lev = scraper_get_max_leverage(symbol)
                    print(f"Scraped max leverage for {symbol}: {scraped_max_lev}")
                    return scraped_max_lev
                except Exception as scraper_e:
                    print(f"Scraper fallback failed: {scraper_e}")
            
            return self.default_max_leverage
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        return self.get_ticker_price(symbol)

    def _fetch_leverage_brackets(self):
        """Fetch leverage brackets for all symbols"""
        try:
            # This API endpoint sometimes requires authentication, but we can get the data from exchange info
            print("Fetching leverage brackets directly...")
            
            # First try the direct endpoint - may not work without auth
            try:
                response = self.session.get(f"{self.BASE_URL}/fapi/v1/leverageBracket", timeout=self.timeout)
                response.raise_for_status()
                brackets = response.json()
                
                # Update our symbols_data with the correct max leverage
                for symbol_info in brackets:
                    symbol = symbol_info.get('symbol')
                    if symbol and 'brackets' in symbol_info and symbol_info['brackets']:
                        # Get the maximum leverage from the first bracket
                        max_leverage = symbol_info['brackets'][0].get('initialLeverage', self.default_max_leverage)
                        
                        # Update our symbols_data if we have this symbol
                        if symbol in self.symbols_data:
                            self.symbols_data[symbol]['maxLeverage'] = max_leverage
                            print(f"Updated {symbol} max leverage to {max_leverage}x")
                            
                print(f"Updated leverage information for {len(brackets)} symbols")
            except Exception as e:
                print(f"Direct leverage bracket API failed: {e}")
                print("Falling back to symbol information...")
                
                # As a fallback, check each symbol's leverage limit directly
                for symbol in list(self.symbols_data.keys()):
                    try:
                        symbol_url = f"{self.BASE_URL}/fapi/v1/leverageBracket?symbol={symbol}"
                        symbol_response = self.session.get(symbol_url, timeout=self.timeout)
                        symbol_response.raise_for_status()
                        
                        symbol_data = symbol_response.json()
                        if symbol_data and 'brackets' in symbol_data[0] and symbol_data[0]['brackets']:
                            max_leverage = symbol_data[0]['brackets'][0].get('initialLeverage', self.default_max_leverage)
                            
                            self.symbols_data[symbol]['maxLeverage'] = max_leverage
                            print(f"Updated {symbol} max leverage to {max_leverage}x")
                    except Exception as symbol_e:
                        print(f"Could not get leverage for {symbol}: {symbol_e}")
                        
                        # One more fallback - use hard-coded values for common symbols
                        if symbol == "ADAUSDT":
                            self.symbols_data[symbol]['maxLeverage'] = 75
                            print(f"Hard-coded {symbol} max leverage to 75x")
                        elif symbol == "XRPUSDT":
                            self.symbols_data[symbol]['maxLeverage'] = 75
                            print(f"Hard-coded {symbol} max leverage to 75x")
                        elif symbol == "DOGEUSDT":
                            self.symbols_data[symbol]['maxLeverage'] = 75
                            print(f"Hard-coded {symbol} max leverage to 75x")
        except Exception as e:
            print(f"Error fetching leverage brackets: {e}")

# Create a singleton instance
binance_api = BinanceAPI()

def get_available_symbols() -> List[str]:
    """Get list of available trading symbols"""
    return binance_api.get_available_symbols()

def get_symbol_info(symbol: str) -> Optional[Dict]:
    """Get information about a symbol"""
    return binance_api.get_symbol_info(symbol)

def get_current_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol"""
    return binance_api.get_current_price(symbol)

def get_max_leverage(symbol: str) -> int:
    """Get maximum leverage for a symbol"""
    return binance_api.get_max_leverage(symbol)

# Test function
if __name__ == "__main__":
    print("Testing Binance API...")
    api = BinanceAPI()
    
    # Get available symbols
    symbols = api.get_available_symbols()
    print(f"Available symbols: {len(symbols)}")
    print(f"First 5 symbols: {symbols[:5]}")
    
    # Get info for BTCUSDT
    btc_info = api.get_symbol_info("BTCUSDT")
    print(f"\nBTCUSDT info:")
    if btc_info:
        for key, value in btc_info.items():
            print(f"  {key}: {value}")
    
    # Get max leverage for different symbols
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]
    print("\nMaximum leverage:")
    for symbol in test_symbols:
        max_lev = api.get_max_leverage(symbol)
        print(f"  {symbol}: {max_lev}x")
    
    # Get current prices
    print("\nCurrent prices:")
    for symbol in test_symbols:
        price = api.get_current_price(symbol)
        print(f"  {symbol}: ${price}") 