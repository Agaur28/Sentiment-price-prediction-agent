import numpy as np, pandas as pd
# Multilingual (EN / Cantonese-Chinese / Korean) finance lexicon. Swap score_text for an LLM or xlm-roberta model to upgrade.
POS = ["bullish", "buy rating", "surge", "rally", "beat", "upgrade", "breakout", "record high", "outperform",
       "利好", "看好", "大升", "急升", "上升", "上漲", "上涨", "新高", "突破", "增長", "增长", "盈喜", "回購", "回购", "獲批", "获批", "反彈", "反弹", "強勢", "强势", "買入", "买入", "超預期", "超预期", "升",
       "상승", "급등", "강세", "호재", "매수", "목표가", "신고가", "개선", "증가", "확대", "호조", "흑자", "수혜", "돌파", "반등", "상향", "낙관", "최대"]
NEG = ["bearish", "plunge", "crash", "miss", "downgrade", "dump", "sell-off", "record low", "underperform", "lawsuit",
       "利空", "看淡", "大跌", "急跌", "下跌", "暴跌", "新低", "跌穿", "破位", "盈警", "虧損", "亏损", "制裁", "被捕", "調查", "调查", "下滑", "疲弱", "拋售", "抛售", "止蝕", "止损", "減持", "减持", "風險", "风险", "下調", "下调", "跌",
       "하락", "급락", "약세", "악재", "매도", "손절", "부진", "감소", "우려", "적자", "둔화", "악화", "하향", "거품", "폭락", "리스크", "위기", "제재", "쇼크"]

def score_text(t):
    t = str(t).lower(); p = sum(w in t for w in POS); n = sum(w in t for w in NEG)
    return (p - n) / max(1, p + n)

def score_df(df):
    df = df.copy()
    df["sent"] = df.text.map(score_text) if len(df) else []
    if "views" in df:  # engagement weight, log-scaled to damp whales
        df["w"] = 1 + np.log1p(df.likes + df.reposts + 0.1 * df.views) + 0.2 * np.log1p(df.followers)
    return df
