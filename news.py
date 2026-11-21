import pandas as pd, config
from sentiment import score_text

def collect(cfg, demo=False, days=config.DAYS):
    rows = []
    if demo: return pd.DataFrame(columns=["ticker", "ts_utc", "title", "url", "sent"])
    if not config.EXA_API_KEY: raise SystemExit('EXA_API_KEY missing: create .env (Windows: copy .env.example .env) and add your key')
    from exa_py import Exa
    exa = Exa(config.EXA_API_KEY)
    start = (pd.Timestamp.utcnow() - pd.Timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000Z")
    for t, (name, local) in cfg["tickers"].items():
        try:
            r = exa.search_and_contents(f"{name} stock news", num_results=8, text={"max_characters": 1000},
                                        start_published_date=start, category="news")
            for x in r.results:
                rows.append(dict(ticker=t, ts_utc=pd.to_datetime(x.published_date, utc=True, errors="coerce"), title=x.title,
                                 url=x.url, sent=score_text((x.title or "") + " " + (x.text or ""))))
        except Exception as e:
            print(f"[warn] exa/{t}: {e}")
    return pd.DataFrame(rows, columns=["ticker", "ts_utc", "title", "url", "sent"])
