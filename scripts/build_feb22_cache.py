import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
from pathlib import Path
import yfinance as yf
import datetime

# Training tickers only — eval uses current-data cache
TICKERS = ['^GSPC', 'AAPL', 'JNJ', 'JPM', 'XOM', 'PG', 'CAT', 'NEE', 'AMT', 'WMT']

# Feb 22, 2026 was a Sunday; last trading day was Feb 20 (Friday).
# yfinance end is exclusive, so end=2026-02-21 gives data through Feb 20.
END_DATE = datetime.date(2026, 2, 21)
START_DATE = datetime.date(2006, 2, 21)  # 20 years back

OUT_DIR = Path(r'C:\Users\ylchen\workspace\research_group\data\us_feb22')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(ticker: str) -> str:
    return (ticker.replace('^', '_').replace('/', '_')
                  .replace('\\', '_').replace('.', '_'))


for ticker in TICKERS:
    print(f'Downloading {ticker} up to {END_DATE}...')
    df = yf.download(ticker, start=str(START_DATE), end=str(END_DATE),
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        print(f'  ERROR: no data for {ticker}', file=sys.stderr)
        continue
    arr = df['Close'].values.astype('float32').flatten()
    arr = arr[~np.isnan(arr) & (arr > 0)]
    out_path = OUT_DIR / f'{safe_name(ticker)}.npy'
    np.save(out_path, arr)
    print(f'  {len(arr)} points -> {out_path.name}')

print('\nDone. Cache written to:', OUT_DIR)
