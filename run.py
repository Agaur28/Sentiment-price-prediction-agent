"""Usage: python run.py [--demo]      -> builds report + predictions
          python run.py evaluate     -> compares saved predictions with the actual next close"""
import sys, os, json
import sys, json, pandas as pd
import config, prices as P, scrapers, news as N, sentiment, model, report

def pipeline(demo):
    all_s, all_px, all_m, preds = [], {}, {}, []
    for ex, cfg in config.EXCHANGES.items():
        px = P.get_prices(cfg["tickers"], demo); all_px.update(px)
        cache = f"out/{ex}_posts.csv"
        if "--cached" in sys.argv and os.path.exists(cache):
            posts = pd.read_csv(cache); posts["ts_utc"] = pd.to_datetime(posts.ts_utc, utc=True)
        else:
            posts = sentiment.score_df(scrapers.collect(cfg, demo))
        nws = N.collect(cfg, demo)
        posts.to_csv(f"out/{ex}_posts.csv", index=False)
        panel = model.build_panel(px, posts, nws, cfg["tz"], cfg["sources"], config.DAYS)
        last, m = model.run(panel); all_m[ex] = m["sentiment+price"]; all_m[ex + " price_only"] = m["price_only"]; all_m[ex + " naive"] = m["naive_zero_return"]
        for _, r in last.iterrows():
            t = r.ticker; p = posts[posts.ticker == t]; sup, res = P.levels(px[t])
            s = (p.sent * p.w).sum() / p.w.sum() if len(p) else 0.0
            direction = "BULLISH" if s > 0.1 else "BEARISH" if s < -0.1 else "NEUTRAL"
            pos = "LONG" if direction == "BULLISH" and r.pred_ret > 0 else "SHORT" if direction == "BEARISH" and r.pred_ret < 0 else "FLAT"
            note = {"LONG": f"stop {sup[0]}, target {res[0]}", "SHORT": f"stop {res[-1]}, target {sup[-1]}", "FLAT": "no trade"}[pos]
            all_s.append(dict(exchange=ex, ticker=t, name=cfg["tickers"][t][0], price=r.close, mentions=len(p), sentiment=s, direction=direction,
                              news_sent=nws[nws.ticker == t].sent.mean() if len(nws) else 0.0, position=f"{pos} ({note})",
                              support=", ".join(map(str, sup)), resistance=", ".join(map(str, res)), support_list=sup, resistance_list=res,
                              pred_price=r.pred_price, **{"pred_ret_%": r.pred_ret * 100}, base_date=r.date.date()))
    summ = pd.DataFrame(all_s); summ.drop(columns=["support_list", "resistance_list"]).to_csv("out/predictions.csv", index=False)
    json.dump(all_m, open("out/metrics.json", "w"), indent=2, default=float)
    report.make(summ, all_px, all_m, "out/report.html"); print("Done -> out/report.html, out/predictions.csv, out/metrics.json")

def evaluate():
    pr = pd.read_csv("out/predictions.csv", parse_dates=["base_date"]); rows = []
    px = P.get_prices(pr.ticker.tolist())
    for _, r in pr.iterrows():
        nxt = px[r.ticker][px[r.ticker].index > r.base_date]
        if nxt.empty: continue
        a = nxt.Close.iloc[0]; rows.append(dict(ticker=r.ticker, pred=r.pred_price, actual=a, err_pct=(r.pred_price / a - 1) * 100,
                                               direction_ok=(r.pred_price > r.price) == (a > r.price)))
    df = pd.DataFrame(rows); print(df.to_string(index=False)); df.to_csv("out/evaluation.csv", index=False)
    if len(df): print(f"\nMAPE {df.err_pct.abs().mean():.2f}% | directional accuracy {df.direction_ok.mean():.0%}")

if __name__ == "__main__":
    evaluate() if "evaluate" in sys.argv else pipeline("--demo" in sys.argv)
