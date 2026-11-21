import numpy as np, pandas as pd

def get_prices(tickers, demo=False, period="4mo"):
    out = {}
    for t in tickers:
        if demo:
            rng = np.random.default_rng(abs(hash(t)) % 2**32)
            idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=80)
            c = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(idx))))
            out[t] = pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1e6}, index=idx)
        else:
            import yfinance as yf, time
            df = pd.DataFrame()
            for _ in range(3):
                df = yf.Ticker(t).history(period=period, interval="1d")
                if not df.empty: break
                time.sleep(3)
            if df.empty:
                print(f"[warn] no price data for {t}"); continue
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            out[t] = df.dropna()
    return out

def levels(df, n=20):
    """Support/resistance: classic pivot (S1/R1) + n-day swing low/high."""
    last, w = df.iloc[-1], df.iloc[-n:]
    p = (last.High + last.Low + last.Close) / 3
    s1, r1 = 2 * p - last.High, 2 * p - last.Low
    sup = sorted({round(float(x), 2) for x in (s1, w.Low.min()) if x < last.Close})
    res = sorted({round(float(x), 2) for x in (r1, w.High.max()) if x > last.Close})
    return sup or [round(float(w.Low.min()), 2)], res or [round(float(w.High.max()), 2)]
