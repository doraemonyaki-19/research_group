
import yfinance as yf
import numpy as np
import os
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def save_tickers_to_npy(tickers: list[str], save_dir: str, years: int = 20):
    import datetime
    p = Path(save_dir)
    p.mkdir(parents=True, exist_ok=True)
    
    end = datetime.datetime.now(datetime.timezone.utc).date()
    start = end - datetime.timedelta(days=365 * years)
    
    for ticker in tickers:
        # Sanitize ticker name for filesystem
        safe_ticker = ticker.replace('^', 'GSPC_')
        print(f"Downloading {ticker}...")
        df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False, auto_adjust=True)
        if df is None or df.empty:
            print(f"  WARNING: Failed to download {ticker}, skipping.")
            continue
        
        close = df["Close"].values.astype(np.float32).flatten()
        close = close[~np.isnan(close) & (close > 0)]
        
        output_path = p / f"{safe_ticker}.npy"
        np.save(output_path, close)
        print(f"  Saved {len(close)} data points for {ticker} to {output_path}")

if __name__ == "__main__":
    canonical_tickers = "^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT".split(',')
    output_directory = r"C:\Users\ylchen\workspace\research_group\artifacts\canonical_ticker_data"
    save_tickers_to_npy(canonical_tickers, output_directory)
    print("Data preparation complete.")
