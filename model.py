import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SENT = ["sent_mean", "sent_w", "log_n", "sent_s1", "sent_s2", "news_sent"]
PRICE = ["ret1", "ret5"]

def _align(dates, trading):  # map a timestamp to the next trading bar on/after it
    i = np.searchsorted(trading.values, dates.values, side="left")
    return pd.Series([trading[j] if j < len(trading) else pd.NaT for j in i], index=dates.index)

def build_panel(prices, posts, news, tz, sources, days):
    frames = []
    for t, px in prices.items():
        f = pd.DataFrame(index=px.index)
        f["close"] = px.Close; f["ret1"] = px.Close.pct_change(); f["ret5"] = px.Close.pct_change(5)
        f["target"] = px.Close.shift(-1) / px.Close - 1  # n+1 return
        p = posts[posts.ticker == t].copy()
        if len(p):
            p["date"] = _align(p.ts_utc.dt.tz_convert(tz).dt.tz_localize(None).dt.normalize(), px.index)
            p = p.dropna(subset=["date"])
            p["sw"] = p.sent * p.w
            g = p.groupby("date")
            f["n"] = g.size(); f["sent_mean"] = g.sent.mean(); f["sent_w"] = g.sw.sum() / g.w.sum()
            for k, s in enumerate(sources[:2], 1):
                f[f"sent_s{k}"] = p[p.source == s].groupby("date").sent.mean()
        n = news[news.ticker == t].copy() if len(news) else news
        if len(n):
            n["date"] = _align(n.ts_utc.dt.tz_convert(tz).dt.tz_localize(None).dt.normalize(), px.index)
            f["news_sent"] = n.dropna(subset=["date"]).groupby("date").sent.mean()
        for c in ["n", "sent_mean", "sent_w", "sent_s1", "sent_s2", "news_sent"]:
            if c not in f: f[c] = 0.0
        f["log_n"] = np.log1p(f.n.fillna(0))
        f = f.fillna({c: 0.0 for c in SENT}); f["ticker"] = t
        frames.append(f.iloc[-(days + 1):].reset_index(names="date"))
    return pd.concat(frames, ignore_index=True).dropna(subset=["ret1", "ret5"])

def _fit(X, y): return make_pipeline(StandardScaler(), Ridge(alpha=10.0)).fit(X, y)

def walk_forward(panel, feats, min_train=3):
    """Expanding-window, out-of-sample: predict day d using only rows whose target was known before d."""
    lab = panel.dropna(subset=["target"]); dates = sorted(lab.date.unique()); out = []
    for i, d in enumerate(dates):
        tr, te = lab[lab.date < d], lab[lab.date == d]
        if tr.date.nunique() < min_train: continue
        out.append(te.assign(pred=_fit(tr[feats], tr.target).predict(te[feats])))
    return pd.concat(out) if out else pd.DataFrame()

def metrics(df):
    if df.empty: return {"n": 0}
    return {"n": len(df), "MAE": float((df.pred - df.target).abs().mean()), "directional_acc": float((np.sign(df.pred) == np.sign(df.target)).mean())}

def run(panel):
    res = {}
    for name, feats in {"sentiment+price": SENT + PRICE, "price_only": PRICE}.items():
        res[name] = metrics(walk_forward(panel, feats))
    lab = panel.dropna(subset=["target"])
    res["naive_zero_return"] = {"n": len(lab), "MAE": float(lab.target.abs().mean()), "directional_acc": float((lab.target > 0).mean())}
    feats = SENT + PRICE
    m = _fit(lab[feats], lab.target)
    last = panel.sort_values("date").groupby("ticker").tail(1).copy()
    last["pred_ret"] = m.predict(last[feats]); last["pred_price"] = last.close * (1 + last.pred_ret)
    return last, res
