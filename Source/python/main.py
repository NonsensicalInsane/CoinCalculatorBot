import argparse
from app import BinancePnLApp

def main():
    parser = argparse.ArgumentParser(description='Binance Futures PnL Visualization Generator')
    
    parser.add_argument('--pair', type=str, required=True, help='Trading pair (e.g., BTCUSDT)')
    parser.add_argument('--leverage', type=int, required=True, help='Leverage multiplier (e.g., 20)')
    parser.add_argument('--entry', type=float, required=True, help='Entry price')
    parser.add_argument('--last', type=float, required=True, help='Last/current price')
    parser.add_argument('--referral', type=str, required=True, help='Referral code')
    parser.add_argument('--position', type=str, default='Long', choices=['Long', 'Short'], 
                      help='Position type (Long or Short)')
    parser.add_argument('--output', type=str, help='Output filename (optional)')
    parser.add_argument('--config', type=str, default='config.cfg', help='Path to config file')
    
    args = parser.parse_args()
    
    app = BinancePnLApp(config_path=args.config)
    
    try:
        output_path = app.generate_pnl_visualization(
            args.pair,
            args.leverage,
            args.entry,
            args.last,
            args.referral,
            args.position,
            args.output
        )
        print(f"PnL visualization generated successfully: {output_path}")
    except Exception as e:
        print(f"Error generating PnL visualization: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
