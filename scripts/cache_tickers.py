"""
One-time script to download and cache all experiment tickers as .npy files.

After running this, training and evaluation can be done completely offline by
passing --cache-dir to finetune_timesfm.py and rolling_eval.py.

Usage:
    python scripts/cache_tickers.py --out-dir data/us --region us
    python scripts/cache_tickers.py --out-dir data --region all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance is required. pip install yfinance", file=sys.stderr)
    sys.exit(1)

import datetime

# All tickers needed per region (training + eval + diagnostic)
TICKERS = {
    "us": [
        # training
        "^GSPC", "AAPL", "JNJ", "JPM", "XOM", "PG", "CAT", "NEE", "AMT", "WMT",
        # eval (held-out)
        "NVDA", "UNH", "GS", "CVX", "KO", "BA",
        # diagnostic
        "MSFT", "AMZN", "GOOGL", "META",
    ],
    "japan": [
        "7203.T", "6758.T", "9984.T", "8306.T", "6861.T",
        "7974.T", "4502.T", "9432.T", "8035.T", "6501.T",
        "6902.T", "7267.T", "4063.T", "2914.T", "8031.T",
    ],
    "europe": [
        "MC.PA", "ASML.AS", "LVMH.PA", "SAP.DE", "SIE.DE",
        "NESN.SW", "NOVN.SW", "ROG.SW", "AZN.L", "SHEL.L",
        "BP.L", "HSBA.L", "ULVR.L", "RIO.L", "GSK.L",
    ],
    "china": [
        "600519.SS", "601318.SS", "000858.SZ", "600036.SS", "601166.SS",
        "002594.SZ", "600900.SS", "601988.SS", "000333.SZ", "600276.SS",
        "601398.SS", "600000.SS", "601857.SS", "601628.SS", "600104.SS",
    ],
}


def download_and_cache(ticker: str, out_dir: Path, years: int = 20) -> bool:
    safe = ticker.replace("^", "_").replace("/", "_").replace("\\", "_")
    dest = out_dir / f"{safe}.npy"
    if dest.exists():
        size = np.load(dest).shape[0]
        print(f"  [skip] {ticker}: already cached ({size} pts) → {dest.name}")
        return True

    end = datetime.datetime.now(datetime.timezone.utc).date()
    start = end - datetime.timedelta(days=365 * years)
    print(f"  {ticker}: downloading {start} → {end} ...", end=" ", flush=True)
    try:
        df = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty:
            print("FAILED (empty)")
            return False
        close = df["Close"].values.astype(np.float32).flatten()
        close = close[~np.isnan(close) & (close > 0)]
        np.save(dest, close)
        print(f"ok ({len(close)} pts)")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Cache ticker data as .npy files")
    parser.add_argument(
        "--out-dir",
        default=r"C:\Users\ylchen\workspace\research_group\data",
        help="Root output directory. Tickers are saved as <out-dir>/<region>/<ticker>.npy "
             "when --region is used, or directly into <out-dir> when --region is omitted.",
    )
    parser.add_argument(
        "--region",
        default="us",
        choices=["us", "japan", "europe", "china", "all"],
        help="Region to download. 'all' downloads all four regions.",
    )
    parser.add_argument("--years", type=int, default=20, help="Years of history to download.")
    args = parser.parse_args()

    regions = list(TICKERS.keys()) if args.region == "all" else [args.region]

    for region in regions:
        out_dir = Path(args.out_dir) / region
        out_dir.mkdir(parents=True, exist_ok=True)
        tickers = TICKERS[region]
        print(f"\n=== {region.upper()} ({len(tickers)} tickers) → {out_dir} ===")
        ok, fail = 0, 0
        for ticker in tickers:
            if download_and_cache(ticker, out_dir, args.years):
                ok += 1
            else:
                fail += 1
        print(f"  Done: {ok} cached, {fail} failed.")


if __name__ == "__main__":
    main()
