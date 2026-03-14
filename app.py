import os
import json
import anthropic
from flask import Flask, render_template, Response, stream_with_context, request

app = Flask(__name__)

SYSTEM_PROMPT = """You are an expert international news analyst and historian. Your role is to:

1. Find and summarize the TOP 5 most important international news stories happening RIGHT NOW using web search.
2. For each story, provide:
   - A clear, concise summary (3-4 sentences) written in plain language
   - The key countries/players involved
   - A "Historical Link" section connecting this event to relevant historical precedents, patterns, or past events (2-3 sentences)
   - A "Why It Matters" section explaining the global significance (1-2 sentences)
   - A "Quick Fact" — one surprising or little-known historical fact related to the topic

Format your response EXACTLY as a JSON array like this:
[
  {
    "title": "Story headline here",
    "region": "Region/Country",
    "category": "Politics|Economy|Conflict|Diplomacy|Climate|Technology",
    "summary": "Clear summary of what's happening...",
    "historical_link": "This connects to history because...",
    "why_it_matters": "This is globally significant because...",
    "quick_fact": "Did you know that..."
  }
]

IMPORTANT:
- Search for CURRENT news from today or the past 48 hours
- Focus on international stories (not just US domestic news)
- Be factual and neutral
- Make historical connections genuinely insightful and educational
- Output ONLY the JSON array, no other text
"""

def generate_news_stream():
    """Stream news summaries from Claude with web search."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'error': 'ANTHROPIC_API_KEY not set. Please set it as an environment variable.'})}\n\n"
        return

    client = anthropic.Anthropic(api_key=api_key)

    yield f"data: {json.dumps({'status': 'searching', 'message': 'Searching for latest international news...'})}\n\n"

    try:
        full_text = ""
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=[
                {"type": "web_search_20260209", "name": "web_search"},
                {"type": "web_fetch_20260209", "name": "web_fetch"},
            ],
            messages=[{
                "role": "user",
                "content": "Search for and summarize the top 5 most important international news stories from the last 48 hours. Include historical context for each story. Return the result as a JSON array."
            }]
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if hasattr(event, 'content_block') and event.content_block.type == "text":
                        yield f"data: {json.dumps({'status': 'analyzing', 'message': 'Analyzing news and building historical context...'})}\n\n"
                elif event.type == "content_block_delta":
                    if hasattr(event, 'delta') and event.delta.type == "text_delta":
                        full_text += event.delta.text

        # Parse and send the final JSON
        full_text = full_text.strip()
        # Extract JSON if wrapped in markdown code blocks
        if "```json" in full_text:
            full_text = full_text.split("```json")[1].split("```")[0].strip()
        elif "```" in full_text:
            full_text = full_text.split("```")[1].split("```")[0].strip()

        stories = json.loads(full_text)
        yield f"data: {json.dumps({'status': 'done', 'stories': stories})}\n\n"

    except json.JSONDecodeError as e:
        yield f"data: {json.dumps({'error': f'Failed to parse news data: {str(e)}'})}\n\n"
    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'error': 'Invalid API key. Please check your ANTHROPIC_API_KEY.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stream-news")
def stream_news():
    return Response(
        stream_with_context(generate_news_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  International News + History App")
    print("=" * 60)
    print()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  WARNING: ANTHROPIC_API_KEY not set!")
        print("  Set it with: set ANTHROPIC_API_KEY=your-key-here")
        print()
    print("  Open your browser at: http://localhost:5000")
    print()
    app.run(debug=False, port=5000)
