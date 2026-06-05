
import torch  # <-- ADDED THIS LINE
import yfinance as yf
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def download_tickers_debug(tickers: list[str], years: int = 20):
    import datetime
    end = datetime.datetime.now(datetime.timezone.utc).date()
    start = end - datetime.timedelta(days=365 * years)
    print(f"Attempting to download {len(tickers)} tickers...")
    for ticker in tickers:
        print(f"Downloading {ticker} from {start} to {end}...")
        try:
            df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False, auto_adjust=True)
            if df is None or df.empty:
                print(f"  WARNING: Failed to download {ticker}, skipping.")
                continue
            print(f"  SUCCESS: Downloaded {len(df)} rows for {ticker}.")
        except Exception as e:
            print(f"  ERROR: Exception for ticker {ticker}: {e}")
    print("All tickers processed.")

if __name__ == "__main__":
    focused_tickers = "AAPL,JNJ,JPM,XOM,PG,CAT".split(',')
    print("--- Testing focused ticker list (6 tickers) with torch imported ---")
    download_tickers_debug(focused_tickers)
