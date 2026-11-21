import os, json
from dotenv import load_dotenv
load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
EXA_API_KEY = os.getenv("EXA_API_KEY")
DAYS = 10  # social lookback window

# ticker -> (English name, local-language keyword)
EXCHANGES = {
    "HKEX": {
        "tz": "Asia/Hong_Kong",
        "sources": ["lihkg", "telegram"], "tg_env": "TELEGRAM_CHANNELS_HKEX",
        "tickers": {
            "0700.HK": ("Tencent", "騰訊"), "9988.HK": ("Alibaba", "阿里巴巴"),
            "0005.HK": ("HSBC", "滙豐"), "1810.HK": ("Xiaomi", "小米"),
            "3690.HK": ("Meituan", "美團"),
        },
    },
    "KRX": {
        "tz": "Asia/Seoul",
        "sources": ["naver", "telegram"], "tg_env": "TELEGRAM_CHANNELS_KRX",
        "tickers": {
            "005930.KS": ("Samsung Electronics", "삼성전자"), "000660.KS": ("SK Hynix", "SK하이닉스"),
            "035420.KS": ("Naver", "네이버"), "005380.KS": ("Hyundai Motor", "현대차"),
            "035720.KS": ("Kakao", "카카오"),
        },
    },
}
ACTORS = {  # naver uses Apify's official Cheerio scraper with a custom pageFunction
    "naver": "apify/cheerio-scraper",
    "telegram": "apify/cheerio-scraper",
    "lihkg": os.getenv("ACTOR_LIHKG"), "futu": os.getenv("ACTOR_FUTU"),
}
def actor_input(source, query):
    raw = os.getenv(f"ACTOR_INPUT_{source.upper()}", '{"search":"{query}","maxItems":200}')
    return json.loads(raw.replace("{query}", query))
