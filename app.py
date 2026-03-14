from flask import Flask, render_template, jsonify, request
import anthropic
import feedparser
import os
import json

app = Flask(__name__)

RSS_FEEDS = {
    "en": {
        "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "Europe": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "Asia": "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "Americas": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "Africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    },
    "fr": {
        "Monde": "https://www.france24.com/fr/monde/rss",
        "Europe": "https://www.france24.com/fr/europe/rss",
        "Moyen-Orient": "https://www.france24.com/fr/moyen-orient/rss",
        "Asie": "https://www.france24.com/fr/asie-pacifique/rss",
        "Amériques": "https://www.france24.com/fr/ameriques/rss",
        "Afrique": "https://www.france24.com/fr/afrique/rss",
    }
}

def get_image(entry):
    thumbs = entry.get('media_thumbnail', [])
    if thumbs:
        return thumbs[0].get('url', '')
    content = entry.get('media_content', [])
    if content:
        return content[0].get('url', '')
    return ''

def get_news(region, lang):
    feeds = RSS_FEEDS.get(lang, RSS_FEEDS["en"])
    default = list(feeds.keys())[0]
    url = feeds.get(region, feeds[default])
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:3]:
        articles.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "image": get_image(entry)
        })
    return articles

def analyze_with_claude(articles, lang):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "API key not set"
    client = anthropic.Anthropic(api_key=api_key)
    news_text = "\n\n".join([f"ARTICLE {i}:\nTITLE: {a['title']}\nSUMMARY: {a['summary']}" for i, a in enumerate(articles)])

    if lang == "fr":
        prompt = f"""Pour chaque article, fournis une analyse en FRANÇAIS.
Retourne UNIQUEMENT un tableau JSON valide avec exactement {len(articles)} objets:
[
  {{
    "index": 0,
    "historical": "2-3 phrases reliant cet événement à un fait historique",
    "lesson": "1 phrase sur ce que l'histoire nous apprend",
    "kids_explanation": "Explique cette actualité en 2-3 phrases simples et fun pour un enfant de 10 ans. Ton amical, mots simples, un emoji sympa, RIEN de violent ou effrayant.",
    "kids_fun_fact": "1 fait amusant qu'un enfant trouverait cool"
  }}
]
ARTICLES:
{news_text}"""
    else:
        prompt = f"""For each news article, provide analysis in ENGLISH.
Return ONLY a valid JSON array with exactly {len(articles)} objects:
[
  {{
    "index": 0,
    "historical": "2-3 sentences connecting this to a historical event",
    "lesson": "1 sentence on what history teaches us",
    "kids_explanation": "Explain in 2-3 fun simple sentences for a 10 year old. Friendly tone, simple words, fun emoji, NO scary details.",
    "kids_fun_fact": "1 fun fact a kid would find cool"
  }}
]
NEWS ARTICLES:
{news_text}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
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
    return render_template("index.html")

@app.route("/api/news")
def api_news():
    region = request.args.get("region", "World")
    lang = request.args.get("lang", "en")
    articles = get_news(region, lang)
    analyses, error = analyze_with_claude(articles, lang)
    if error:
        return jsonify({"error": error})
    for i, article in enumerate(articles):
        if analyses and i < len(analyses):
            article['historical'] = analyses[i].get('historical', '')
            article['lesson'] = analyses[i].get('lesson', '')
            article['kids_explanation'] = analyses[i].get('kids_explanation', '')
            article['kids_fun_fact'] = analyses[i].get('kids_fun_fact', '')
        else:
            article['historical'] = ''
            article['lesson'] = ''
            article['kids_explanation'] = ''
            article['kids_fun_fact'] = ''
    return jsonify({"articles": articles, "region": region, "lang": lang})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
