from flask import Flask, render_template, jsonify, request
import anthropic
import feedparser
import os

app = Flask(__name__)

RSS_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Europe": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    "Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Asia": "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    "Americas": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "Africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
}

def get_news(region="World"):
    url = RSS_FEEDS.get(region, RSS_FEEDS["World"])
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", "")
        })
    return articles

def analyze_with_claude(articles):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "API key not set"
    client = anthropic.Anthropic(api_key=api_key)
    news_text = "\n\n".join([f"TITLE: {a['title']}\nSUMMARY: {a['summary']}" for a in articles])
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are a brilliant history teacher and news analyst.
Analyze these current international news articles and for each one:
1. Give a SHORT clear summary (2-3 sentences) in simple language
2. Connect it to a HISTORICAL EVENT or context
3. Explain WHY this matters today
Use emojis to make it readable.
NEWS ARTICLES:
{news_text}"""}]
    )
    return message.content[0].text, None

@app.route("/")
def index():
    return render_template("index.html", regions=list(RSS_FEEDS.keys()))

@app.route("/api/news")
def api_news():
    region = request.args.get("region", "World")
    articles = get_news(region)
    analysis, error = analyze_with_claude(articles)
    if error:
        return jsonify({"error": error})
    return jsonify({"articles": articles, "analysis": analysis, "region": region})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
