"""
Helper script to configure and control scraping behavior
"""

import os
import configparser
from dotenv import load_dotenv

def load_scraper_config():
    """Load scraper configuration from .env file and/or config files"""
    # Load environment variables
    load_dotenv()
    
    # Default configuration
    config = {
        "auto_update": False,
        "comprehensive_update": False,
        "on_demand": True,
        "selenium_timeout": 10,
        "headless": True,
        "max_threads": 3
    }
    
    # Override from environment variables if they exist
    if os.getenv("BINANCE_SCRAPER_AUTO_UPDATE") is not None:
        config["auto_update"] = os.getenv("BINANCE_SCRAPER_AUTO_UPDATE").lower() == "true"
    
    if os.getenv("BINANCE_SCRAPER_COMPREHENSIVE_UPDATE") is not None:
        config["comprehensive_update"] = os.getenv("BINANCE_SCRAPER_COMPREHENSIVE_UPDATE").lower() == "true"
    
    if os.getenv("BINANCE_SCRAPER_ON_DEMAND") is not None:
        config["on_demand"] = os.getenv("BINANCE_SCRAPER_ON_DEMAND").lower() == "true"
    
    # Try loading from config files
    for config_file in ["config.cfg", "config_binance.cfg", "config_mexc.cfg"]:
        if os.path.exists(config_file):
            cfg = configparser.ConfigParser()
            cfg.read(config_file)
            
            if cfg.has_section("BINANCE_SCRAPER"):
                scraper_config = cfg["BINANCE_SCRAPER"]
                
                if "auto_update" in scraper_config:
                    config["auto_update"] = scraper_config.getboolean("auto_update")
                
                if "comprehensive_update" in scraper_config:
                    config["comprehensive_update"] = scraper_config.getboolean("comprehensive_update")
                
                if "on_demand" in scraper_config:
                    config["on_demand"] = scraper_config.getboolean("on_demand")
                
                if "selenium_timeout" in scraper_config:
                    config["selenium_timeout"] = scraper_config.getint("selenium_timeout")
                
                if "headless" in scraper_config:
                    config["headless"] = scraper_config.getboolean("headless")
                
                if "max_threads" in scraper_config:
                    config["max_threads"] = scraper_config.getint("max_threads")
    
    return config

def get_scraper_instance(force_new=False, symbol=None):
    """
    Get a configured scraper instance
    
    Args:
        force_new: Force creation of a new instance even if one exists
        symbol: If provided, immediately fetch leverage data for this symbol
        
    Returns:
        Configured BinanceScraper instance
    """
    from binance_scraper import BinanceScraper
    
    # Get global instance or create a new one
    global _scraper_instance
    if not hasattr(get_scraper_instance, '_scraper_instance') or force_new:
        config = load_scraper_config()
        get_scraper_instance._scraper_instance = BinanceScraper(
            auto_update=config["auto_update"],
            comprehensive_update=config["comprehensive_update"],
            on_demand=config["on_demand"],
            selenium_timeout=config["selenium_timeout"],
            headless=config["headless"],
            max_threads=config["max_threads"]
        )
    
    # If symbol is provided, fetch its leverage data
    if symbol:
        scraper = get_scraper_instance._scraper_instance
        return scraper.get_leverage_for_symbol(symbol)
    
    return get_scraper_instance._scraper_instance

if __name__ == "__main__":
    """Test the configuration loading"""
    config = load_scraper_config()
    print("Scraper Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}") 