import os, collections, config, scrapers
chans = [c.strip() for c in os.getenv("TELEGRAM_CHANNELS_HKEX", "").split(",") if c.strip()]
items = scrapers._run("apify/cheerio-scraper", {
    "startUrls": [{"url": f"https://t.me/s/{c}", "userData": {"channel": c}} for c in chans],
    "pageFunction": scrapers.TG_PAGE_FN, "proxyConfiguration": {"useApifyProxy": True}})
print("total posts:", len(items))
print(collections.Counter(i.get("author") for i in items))
for i in items[:10]:
    print(i.get("author"), "|", (i.get("text") or "")[:120].replace("\n", " "))