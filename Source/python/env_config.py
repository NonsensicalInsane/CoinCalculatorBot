"""
Environment variable configuration handler
Securely loads sensitive information from environment variables
"""

import os
import configparser
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file if it exists"""
    # First try to load from .env file
    load_dotenv()
    return os.environ

def update_config_with_env(config_path='config.cfg'):
    """
    Update configuration file with environment variables
    
    This keeps configuration structure but replaces sensitive values
    with those from environment variables
    """
    # Load environment variables
    env = load_environment()
    
    # Load existing config
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    
    # Update Telegram section
    if 'TELEGRAM_BOT_TOKEN' in env:
        if not config.has_section('TELEGRAM'):
            config.add_section('TELEGRAM')
        config.set('TELEGRAM', 'bot_token', env['TELEGRAM_BOT_TOKEN'])
    
    if 'TELEGRAM_CHAT_ID' in env:
        if not config.has_section('TELEGRAM'):
            config.add_section('TELEGRAM')
        config.set('TELEGRAM', 'chat_id', env['TELEGRAM_CHAT_ID'])
    
    if 'TELEGRAM_REFERRAL_CODE' in env:
        if not config.has_section('TELEGRAM'):
            config.add_section('TELEGRAM')
        config.set('TELEGRAM', 'referral_code', env['TELEGRAM_REFERRAL_CODE'])
    
    # Update Telegram API section
    if any(key in env for key in ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH']):
        if not config.has_section('TELEGRAM_API'):
            config.add_section('TELEGRAM_API')
        
        if 'TELEGRAM_API_ID' in env:
            config.set('TELEGRAM_API', 'api_id', env['TELEGRAM_API_ID'])
        
        if 'TELEGRAM_API_HASH' in env:
            config.set('TELEGRAM_API', 'api_hash', env['TELEGRAM_API_HASH'])
        
        if 'TELEGRAM_PHONE_NUMBER' in env:
            config.set('TELEGRAM_API', 'phone_number', env['TELEGRAM_PHONE_NUMBER'])
        
        if 'TELEGRAM_USERNAME' in env:
            config.set('TELEGRAM_API', 'username', env['TELEGRAM_USERNAME'])
    
    # Update Binance API section
    if any(key in env for key in ['BINANCE_API_KEY', 'BINANCE_API_SECRET']):
        if not config.has_section('BINANCE_API'):
            config.add_section('BINANCE_API')
        
        if 'BINANCE_API_KEY' in env:
            config.set('BINANCE_API', 'api_key', env['BINANCE_API_KEY'])
        
        if 'BINANCE_API_SECRET' in env:
            config.set('BINANCE_API', 'api_secret', env['BINANCE_API_SECRET'])
    
    # Update Exchange Templates section
    if 'DEFAULT_EXCHANGE' in env or 'AVAILABLE_EXCHANGES' in env:
        if not config.has_section('EXCHANGE_TEMPLATES'):
            config.add_section('EXCHANGE_TEMPLATES')
        
        if 'DEFAULT_EXCHANGE' in env:
            config.set('EXCHANGE_TEMPLATES', 'default', env['DEFAULT_EXCHANGE'])
        
        if 'AVAILABLE_EXCHANGES' in env:
            config.set('EXCHANGE_TEMPLATES', 'templates', env['AVAILABLE_EXCHANGES'])
    
    # Don't write to the file in production (especially on Vercel)
    # This is just for local development
    if not os.environ.get('VERCEL_ENV'):
        with open(config_path, 'w') as f:
            config.write(f)
    
    return config

def get_config_from_env():
    """
    Create a configparser object populated from environment variables
    without reading or writing any files (for serverless environments)
    """
    env = load_environment()
    config = configparser.ConfigParser()
    
    # Create sections and populate from environment
    sections = {
        'TELEGRAM': ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_REFERRAL_CODE'],
        'TELEGRAM_API': ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_PHONE_NUMBER', 'TELEGRAM_USERNAME'],
        'BINANCE_API': ['BINANCE_API_KEY', 'BINANCE_API_SECRET'],
        'EXCHANGE_TEMPLATES': ['DEFAULT_EXCHANGE', 'AVAILABLE_EXCHANGES']
    }
    
    section_key_mapping = {
        'TELEGRAM': {'TELEGRAM_BOT_TOKEN': 'bot_token', 'TELEGRAM_CHAT_ID': 'chat_id', 'TELEGRAM_REFERRAL_CODE': 'referral_code'},
        'TELEGRAM_API': {'TELEGRAM_API_ID': 'api_id', 'TELEGRAM_API_HASH': 'api_hash', 
                         'TELEGRAM_PHONE_NUMBER': 'phone_number', 'TELEGRAM_USERNAME': 'username'},
        'BINANCE_API': {'BINANCE_API_KEY': 'api_key', 'BINANCE_API_SECRET': 'api_secret'},
        'EXCHANGE_TEMPLATES': {'DEFAULT_EXCHANGE': 'default', 'AVAILABLE_EXCHANGES': 'templates'}
    }
    
    for section, keys in sections.items():
        if any(key in env for key in keys):
            config.add_section(section)
            for env_key in keys:
                if env_key in env:
                    config_key = section_key_mapping[section][env_key]
                    config.set(section, config_key, env[env_key])
    
    return config

# For use in serverless environments like Vercel
def get_environment_variable(section, key, default=None):
    """
    Get a configuration value from environment variables
    This provides a direct way to access config without files
    """
    env = load_environment()
    
    # Define mappings from config sections/keys to environment variable names
    mappings = {
        'TELEGRAM': {
            'bot_token': 'TELEGRAM_BOT_TOKEN',
            'chat_id': 'TELEGRAM_CHAT_ID',
            'referral_code': 'TELEGRAM_REFERRAL_CODE'
        },
        'TELEGRAM_API': {
            'api_id': 'TELEGRAM_API_ID',
            'api_hash': 'TELEGRAM_API_HASH',
            'phone_number': 'TELEGRAM_PHONE_NUMBER',
            'username': 'TELEGRAM_USERNAME'
        },
        'BINANCE_API': {
            'api_key': 'BINANCE_API_KEY',
            'api_secret': 'BINANCE_API_SECRET'
        },
        'EXCHANGE_TEMPLATES': {
            'default': 'DEFAULT_EXCHANGE',
            'templates': 'AVAILABLE_EXCHANGES'
        }
    }
    
    # Look up the environment variable name
    if section in mappings and key in mappings[section]:
        env_var = mappings[section][key]
        return env.get(env_var, default)

def load_env():
    """Load environment variables from .env file"""
    # Try to load from .env or .env.local
    load_dotenv()
    
    # Also try .env.local if it exists
    if os.path.exists('.env.local'):
        load_dotenv('.env.local')

def get_env(key, default=None, convert_type=None):
    """
    Get environment variable with optional type conversion
    
    Args:
        key: Environment variable name
        default: Default value if not found
        convert_type: Optional function to convert value type (int, float, bool, etc.)
        
    Returns:
        The environment variable value with appropriate type conversion
    """
    value = os.getenv(key, default)
    
    if value is not None and convert_type is not None:
        if convert_type == bool:
            # Special handling for boolean values
            return value.lower() in ('true', 'yes', '1', 'y')
        else:
            # Use the provided conversion function
            return convert_type(value)
    
    return value

def get_config(section, key, default=None, config_file='config.cfg', convert_type=None):
    """
    Get configuration value from a specific file and section
    
    Args:
        section: Configuration section name
        key: Configuration key
        default: Default value if not found
        config_file: Path to the configuration file
        convert_type: Optional function to convert value type
        
    Returns:
        The configuration value with appropriate type conversion
    """
    if not os.path.exists(config_file):
        return default
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    if not config.has_section(section) or not config.has_option(section, key):
        return default
    
    value = config.get(section, key)
    
    if convert_type is not None:
        if convert_type == bool:
            return config.getboolean(section, key)
        elif convert_type == int:
            return config.getint(section, key)
        elif convert_type == float:
            return config.getfloat(section, key)
        else:
            return convert_type(value)
    
    return value

def get_any(key, default=None, config_file='config.cfg', section=None, convert_type=None):
    """
    Try to get a value from environment variables first, then from config file
    
    Args:
        key: Variable name (will be used for both env var and config key)
        default: Default value if not found
        config_file: Path to configuration file
        section: Configuration section (if None, derived from key prefix)
        convert_type: Optional function to convert value type
        
    Returns:
        The value from environment or config with appropriate type conversion
    """
    # Try environment variables first
    env_value = get_env(key, None, convert_type)
    if env_value is not None:
        return env_value
    
    # If no section provided, try to derive it from key
    if section is None:
        parts = key.split('_', 1)
        if len(parts) > 1:
            section = parts[0]
        else:
            section = 'DEFAULT'
    
    # Try config file
    return get_config(section, key.lower(), default, config_file, convert_type)

# Load environment variables when the module is imported
load_env() 