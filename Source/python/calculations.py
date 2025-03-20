def calculate_pnl_percentage(entry_price, last_price, is_long=True):
    """
    Calculate the profit/loss percentage.
    
    Args:
        entry_price (float): The entry price of the position
        last_price (float): The current/last price
        is_long (bool): True for long positions, False for short positions
        
    Returns:
        float: The profit/loss percentage (positive for profit, negative for loss)
    """
    if is_long:
        pnl = ((last_price - entry_price) / entry_price) * 100
    else:
        pnl = ((entry_price - last_price) / entry_price) * 100
        
    return pnl

def calculate_leveraged_pnl_percentage(entry_price, last_price, leverage, is_long=True):
    """
    Calculate the profit/loss percentage with leverage.
    
    Args:
        entry_price (float): The entry price of the position
        last_price (float): The current/last price
        leverage (int): The leverage multiplier
        is_long (bool): True for long positions, False for short positions
        
    Returns:
        float: The leveraged profit/loss percentage
    """
    base_pnl = calculate_pnl_percentage(entry_price, last_price, is_long)
    leveraged_pnl = base_pnl * leverage
    
    return leveraged_pnl
