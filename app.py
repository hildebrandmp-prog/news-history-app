from flask import Flask, render_template, jsonify, request
import anthropic
import feedparser
import os
import json

app = Flask(__name__)

RSS_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Europe": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    "Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Asia": "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    "Americas": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "Africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
}

def get_image(entry):
    thumbs = entry.get('media_thumbnail', [])
    if thumbs:
        return thumbs[0].get('url', '')
    content = entry.get('media_content', [])
    if content:
        return content[0].get('url', '')
    return ''

def get_news(region="World"):
    url = RSS_FEEDS.get(region, RSS_FEEDS["World"])
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "image": get_image(entry)
        })
    return articles

def analyze_with_claude(articles):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "API key not set"
    client = anthropic.Anthropic(api_key=api_key)
    news_text = "\n\n".join([f"ARTICLE {i}:\nTITLE: {a['title']}\nSUMMARY: {a['summary']}" for i, a in enumerate(articles)])
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""For each news article, give a historical context analysis.
Return ONLY a valid JSON array with exactly {len(articles)} objects:
[
  {{
    "index": 0,
    "historical": "2-3 sentences connecting this to a historical event or context",
    "lesson": "1 sentence on what history teaches us about this"
  }}
]
NEWS ARTICLES:
{news_text}"""}]
    )
    try:
        text = message.content[0].text
        start = text.find('[')
        end = text.rfind(']') + 1
        analyses = json.loads(text[start:end])
        return analyses, None
    except:
        return None, "Failed to parse analysis"

@app.route("/")
def index():
    return render_template("index.html", regions=list(RSS_FEEDS.keys()))

@app.route("/api/news")
def api_news():
    region = request.args.get("region", "World")
    articles = get_news(region)
    analyses, error = analyze_with_claude(articles)
    if error:
        return jsonify({"error": error})
    for i, article in enumerate(articles):
        if analyses and i < len(analyses):
            article['historical'] = analyses[i].get('historical', '')
            article['lesson'] = analyses[i].get('lesson', '')
        else:
            article['historical'] = ''
            article['lesson'] = ''
    return jsonify({"articles": articles, "region": region})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
