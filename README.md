# HKEX + KRX Social/News Sentiment -> n+1 Price Prediction Agent

Pipeline: Apify social scraping (2 sources/exchange) + Exa news -> sentiment scoring -> daily features aligned to price bars (UTC -> exchange tz)
-> Ridge model with walk-forward out-of-sample validation -> n+1 price, S/R levels, position -> visual HTML report.

| Exchange | Tickers                                | Social sources (Apify)        |
| -------- | -------------------------------------- | ----------------------------- |
| HKEX     | 0700, 9988, 0005, 1810, 3690           | LIHKG, Telegram               |
| KRX      | 005930, 000660, 035420, 005380, 035720 | Naver Finance board, Telegram |

## Setup

```
pip install -r requirements.txt
copy .env.example .env   (Windows) / cp .env.example .env     # fill APIFY_TOKEN, EXA_API_KEY and actor IDs
python run.py --demo     # synthetic data, tests the whole flow (no tokens needed)
python run.py            # live run -> out/report.html, out/predictions.csv, out/metrics.json
python run.py evaluate   # next trading day: compares predictions vs actual close
```

## Apify actors used

- Naver board: `apify/cheerio-scraper` (custom pageFunction in scrapers.py, 20 pages/ticker)
- Telegram: `apify/cheerio-scraper` on public channels (`TELEGRAM_CHANNELS_*` in `.env`, ticker/name keyword filter)
- LIHKG: actor ID in `.env` (`ACTOR_LIHKG`) with input JSON in `ACTOR_INPUT_*`.
  Field names are auto-normalised (text/timestamp/likes/reposts/views/followers aliases in scrapers.py).

## Method

- Features per ticker-day: mean & engagement-weighted sentiment, log post count, per-source sentiment, Exa news sentiment, 1d/5d return.
- Target: next-day return -> n+1 price = close * (1 + predicted return).
- Validation: expanding-window walk-forward (train only on days whose target is already known). Compared against price-only model and zero-return baseline.
- Support/resistance: classic pivot S1/R1 + 20-day swing low/high. Position: LONG/SHORT only when sentiment direction and model sign agree, else FLAT.
- Limitations: 10 days of history = tiny sample; lexicon sentiment (swap `sentiment.score_text` for an LLM/XLM-R model); posts after close map to next bar's date rule is simple.




## Results and limitations

- Sources: HKEX = LIHKG (Apify actor claude_code_reviewer/lihkg-scraper-en) + public Telegram channels;
  KRX = Naver Finance discussion JSON endpoint + Telegram. News via Exa. Naver and Telegram run on apify/cheerio-scraper.
- Naver posts are capped at 30 pages (1,500 posts) per ticker, so mention counts are capped and
  may cover less than 10 days for active tickers.
- LIHKG provides no views or follower counts; Telegram provides views only.
- Only a few Telegram posts per HK ticker; the first HK channel tried was ad spam.
- Sentiment is a multilingual keyword lexicon (EN/ZH/KO), a baseline only.
- Validation: expanding-window walk-forward on ~10 days x 5 tickers per exchange. Results show no
  reliable edge from sentiment (HKEX directional accuracy is inflated by a falling market; KRX model
  MAE is worse than the zero-return baseline). Treat as a pipeline demo, not trading advice.
- n+1 = next trading day after the last close; run `python run.py evaluate` after that close to compare.
