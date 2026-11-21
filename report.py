import pandas as pd, plotly.graph_objects as go, plotly.io as pio

COL = {"BULLISH": "#1a9850", "BEARISH": "#d73027", "NEUTRAL": "#888"}
def make(summ, prices, metrics, path):
    html = ["<html><head><meta charset='utf-8'><title>Sentiment Report</title><style>body{font-family:sans-serif;max-width:1100px;margin:auto}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:6px;text-align:right}th{background:#f3f3f3}</style></head><body>",
            f"<h1>Social + News Sentiment Report</h1><p>Generated {pd.Timestamp.utcnow():%Y-%m-%d %H:%M} UTC</p>"]
    for ex, df in summ.groupby("exchange", sort=False):
        df = df.sort_values(["mentions", "sentiment"], ascending=False)
        html.append(f"<h2>{ex}</h2>")
        fig = go.Figure(go.Bar(x=df.ticker, y=df.mentions, marker=dict(color=df.sentiment, colorscale="RdYlGn", cmin=-1, cmax=1, showscale=True,
                        colorbar=dict(title="sentiment")), text=df.direction, hovertemplate="%{x}<br>mentions %{y}<extra></extra>"))
        fig.update_layout(title=f"{ex}: social mentions (colour = sentiment)", height=350)
        html.append(pio.to_html(fig, full_html=False, include_plotlyjs="cdn"))
        d = df.copy(); d["direction"] = d.direction.map(lambda x: f"<b style='color:{COL[x]}'>{x}</b>")
        cols = ["ticker", "name", "price", "mentions", "sentiment", "direction", "news_sent", "position", "support", "resistance", "pred_price", "pred_ret_%"]
        html.append(d[cols].to_html(escape=False, index=False, float_format=lambda x: f"{x:,.3f}"))
        for _, r in df.iterrows():
            px = prices[r.ticker].iloc[-40:]
            f = go.Figure(go.Scatter(x=px.index, y=px.Close, name="Close"))
            for s in r.support_list: f.add_hline(y=s, line_dash="dot", line_color="green", annotation_text=f"S {s}")
            for s in r.resistance_list: f.add_hline(y=s, line_dash="dot", line_color="red", annotation_text=f"R {s}")
            f.add_trace(go.Scatter(x=[px.index[-1] + pd.Timedelta(days=1)], y=[r.pred_price], mode="markers", marker=dict(size=12, symbol="star"), name="n+1 prediction"))
            f.update_layout(title=f"{r.ticker} {r['name']} – {r.direction}, position {r.position}", height=320, margin=dict(t=40, b=20))
            html.append(pio.to_html(f, full_html=False, include_plotlyjs=False))
    html.append("<h2>Out-of-sample validation (walk-forward)</h2>" + pd.DataFrame(metrics).T.to_html(float_format=lambda x: f"{x:.4f}"))
    html.append("<p><i>Caveat: only ~10 days of social history, so validation samples are small; treat as a pipeline demo, not trading advice.</i></p></body></html>")
    open(path, "w", encoding="utf-8").write("\n".join(html))
