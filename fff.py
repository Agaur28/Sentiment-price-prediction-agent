import pandas as pd
for ex in ["HKEX", "KRX"]:
    d = pd.read_csv(f"out/{ex}_posts.csv")
    print(ex); print(d.groupby(["ticker", "source"]).size())