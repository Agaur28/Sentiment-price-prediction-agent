"""Social ingestion via Apify. Output schema: ticker, source, ts_utc, text, likes, reposts, views, followers, author."""
import re, os, random
import numpy as np, pandas as pd
import config
from sentiment import POS, NEG

URL = re.compile(r"https?://\S+")
_TG_CACHE = {}
EXTRA = {
    "0700.HK": ["騰訊", "腾讯", "tencent", "0700", "00700", "马化腾", "馬化騰"],
    "9988.HK": ["阿里巴巴", "阿里", "alibaba", "9988", "09988"],
    "0005.HK": ["滙豐", "汇丰", "匯豐", "hsbc", "0005", "00005"],
    "1810.HK": ["小米", "xiaomi", "1810", "01810", "雷軍", "雷军"],
    "3690.HK": ["美團", "美团", "meituan", "3690", "03690"],
    "005930.KS": ["삼성전자", "삼전", "samsung electronics", "005930"],
    "000660.KS": ["sk하이닉스", "하이닉스", "sk hynix", "000660"],
    "035420.KS": ["네이버", "035420"],
    "005380.KS": ["현대차", "현대자동차", "005380"],
    "035720.KS": ["카카오", "035720"],
}
def relevant(ticker, text):
    t = URL.sub(" ", text).lower()
    return any(k.lower() in t for k in EXTRA.get(ticker, []))

ALIASES = {
    "text": ["text", "content", "message", "title", "body", "full_text"],
    "ts": ["created_at", "createdAt", "timestamp", "date", "time", "postedAt", "publishedAt", "create_time", "writtenAt"],
    "likes": ["likes", "likeCount", "like_count", "favorite_count", "reactions", "upvotes", "recommendCount", "goodCount"],
    "reposts": ["reposts", "shares", "retweetCount", "retweet_count", "forwards"],
    "views": ["views", "viewCount", "view_count", "impressions", "readCount", "hitCount"],
    "followers": ["followers", "followersCount", "author_followers", "followerCount"],
    "author": ["author", "username", "user", "userName", "from"],
}
def pick(d, key, default=None):
    for k in ALIASES[key]:
        if k in d and d[k] not in (None, ""): return d[k]
    return default
def num(v):
    try: return int(float(v))
    except Exception: return int(re.sub(r"[^\d]", "", str(v)) or 0)
def to_utc(v, tz):
    if v is None or v == "": return pd.NaT
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        x = float(v); return pd.to_datetime(x, unit="ms" if x > 1e11 else "s", utc=True)
    t = pd.to_datetime(v, errors="coerce")
    if pd.isna(t): return pd.NaT
    if t.tzinfo is None: t = t.tz_localize(tz, nonexistent="shift_forward", ambiguous="NaT")
    return t.tz_convert("UTC") if not pd.isna(t) else pd.NaT

NAVER_PAGE_FN = """async function pageFunction(context){
  const {request, body, json, enqueueRequest} = context;
  const data = json || JSON.parse(body.toString());
  const res = data.result || data;
  const posts = res.posts || [];
  const cutoff = new Date(Date.now() - 10*86400000 + 9*3600000).toISOString().slice(0,19);
  const out = posts.map(p => {
    const o = {...p, ticker: request.userData.ticker, text: (p.title||'') + ' ' + (p.contentSwReplacedButImg||''), author: p.writer ? p.writer.nickname : ''};
    delete o.contentJsonSwReplaced; delete o.contentSwReplaced; delete o.writer;
    return o;
  });
  const oldest = posts.length ? posts[posts.length-1].writtenAt : null;
  if (posts.length && oldest > cutoff && res.lastOffset && res.lastOffset !== request.userData.prevOffset && request.userData.page < 30) {
    const u = new URL(request.url); u.searchParams.set('offset', res.lastOffset);
    await enqueueRequest({url: u.toString(), userData: {ticker: request.userData.ticker, page: request.userData.page + 1, prevOffset: res.lastOffset}});
  }
  return out; }"""

TG_PAGE_FN = """async function pageFunction(context){
  const {$, request} = context; const out = [];
  const n = s => { s = (s||'').trim().toUpperCase(); const m = parseFloat(s); if (isNaN(m)) return 0; return s.endsWith('K') ? m*1e3 : s.endsWith('M') ? m*1e6 : m; };
  $('.tgme_widget_message').each((i, el) => {
    const m = $(el);
    out.push({text: m.find('.tgme_widget_message_text').text().trim(), date: m.find('time').attr('datetime'),
      views: n(m.find('.tgme_widget_message_views').text()), author: request.userData.channel});
  });
  return out; }"""

def _run(actor, run_input):
    from apify_client import ApifyClient
    c = ApifyClient(config.APIFY_TOKEN)
    run = c.actor(actor).call(run_input=run_input)
    ds = getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
    return list(c.dataset(ds).iterate_items())

def _fetch(source, ticker, name, local, cfg):
    code = ticker.split(".")[0]
    if not config.APIFY_TOKEN: raise RuntimeError("APIFY_TOKEN missing in .env")
    if source == "telegram":
        chans = [x.strip().replace("https://", "").replace("t.me/", "").replace("s/", "").lstrip("@/") for x in os.getenv(cfg["tg_env"], "").split(",") if x.strip()]
        if not chans: raise RuntimeError(f"Set {cfg['tg_env']}=channel1,channel2 in .env (public Telegram channels)")
        key = tuple(chans)
        if key not in _TG_CACHE:
            _TG_CACHE[key] = _run(config.ACTORS["telegram"], {"startUrls": [{"url": f"https://t.me/s/{c}", "userData": {"channel": c}} for c in chans],
                     "pageFunction": TG_PAGE_FN, "proxyConfiguration": {"useApifyProxy": True}})
        return _TG_CACHE[key]
    if source == "naver":
        url = (f"https://m.stock.naver.com/front-api/discussion/list?discussionType=domesticStock&itemCode={code}"
               "&pageSize=50&isHolderOnly=false&excludesItemNews=false&isItemNewsOnly=false")
        return _run(config.ACTORS["naver"], {"startUrls": [{"url": url, "userData": {"ticker": ticker, "page": 1}}],
                    "pageFunction": NAVER_PAGE_FN, "additionalMimeTypes": ["application/json"],
                    "proxyConfiguration": {"useApifyProxy": True}})
    actor = config.ACTORS.get(source)
    if not actor: raise RuntimeError(f"Set ACTOR_{source.upper()} in .env")
    q = local if source == "lihkg" else f"{local} OR {name} OR {code}"
    return _run(actor, config.actor_input(source, q))
def _normalize(items, ticker, source, tz):
    rows = []
    for d in items:
        rows.append(dict(ticker=ticker, source=source, ts_utc=to_utc(pick(d, "ts"), tz), text=URL.sub(" ", str(pick(d, "text", ""))).strip(),
                         likes=num(pick(d, "likes", 0)), reposts=num(pick(d, "reposts", 0)), views=num(pick(d, "views", 0)),
                         followers=num(pick(d, "followers", 0)), author=str(pick(d, "author", ""))))
    return rows

def _demo(ticker, source, tz, days):
    rng = random.Random(hash((ticker, source)) % 10**6); rows = []
    for _ in range(rng.randint(60, 200)):
        ts = pd.Timestamp.utcnow() - pd.Timedelta(minutes=rng.randint(0, days * 1440))
        w = rng.choice([POS, NEG, ["flat", "wait"]])
        rows.append(dict(ticker=ticker, source=source, ts_utc=ts, text=f"[DEMO] {rng.choice(w)} {rng.choice(w)} {ticker}",
                         likes=rng.randint(0, 50), reposts=rng.randint(0, 10), views=rng.randint(10, 5000),
                         followers=rng.randint(0, 20000), author="demo"))
    return rows

def collect(cfg, demo=False, days=config.DAYS):
    rows, cutoff = [], pd.Timestamp.utcnow() - pd.Timedelta(days=days)
    for src in cfg["sources"]:
        for t, (name, local) in cfg["tickers"].items():
            try:
                rows += _demo(t, src, cfg["tz"], days) if demo else _normalize(_fetch(src, t, name, local, cfg), t, src, cfg["tz"])
            except Exception as e:
                print(f"[warn] {src}/{t}: {e}")
    df = pd.DataFrame(rows, columns=["ticker", "source", "ts_utc", "text", "likes", "reposts", "views", "followers", "author"])
    df["ts_utc"] = pd.to_datetime(df.ts_utc, utc=True, errors="coerce")
    df = df.dropna(subset=["ts_utc"]).query("ts_utc >= @cutoff").drop_duplicates(["ticker", "source", "text", "ts_utc"])
    print("[info] rows before relevance filter:", df.groupby("source").size().to_dict())
    if len(df):
        df = df[df.apply(lambda r: r.source == "naver" or relevant(r.ticker, r.text), axis=1)]
    print("[info] rows after relevance filter:", df.groupby("source").size().to_dict())
    return df