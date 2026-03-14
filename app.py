from flask import Flask, render_template, jsonify, request
import anthropic
import feedparser
import os
import json
import time

app = Flask(__name__)

cache = {}
CACHE_DURATION = 1800

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
        prompt = f"""Pour chaque article, analyse en FRANÇAIS. Retourne UNIQUEMENT un JSON valide:
[{{"index":0,"historical":"2 phrases contexte historique","lesson":"1 phrase leçon","kids_explanation":"2 phrases fun pour enfant 10 ans sans rien d'effrayant","kids_fun_fact":"1 fait amusant"}}]
ARTICLES:\n{news_text}"""
    else:
        prompt = f"""For each article, return ONLY valid JSON:
[{{"index":0,"historical":"2 sentences historical context","lesson":"1 sentence lesson","kids_explanation":"2 fun sentences for 10 year old no scary details","kids_fun_fact":"1 fun fact"}}]
ARTICLES:\n{news_text}"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
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
    cache_key = f"{lang}_{region}"
    now = time.time()
    if cache_key in cache and now - cache[cache_key]['time'] < CACHE_DURATION:
        return jsonify(cache[cache_key]['data'])
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
    result = {"articles": articles, "region": region, "lang": lang}
    cache[cache_key] = {'data': result, 'time': now}
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
